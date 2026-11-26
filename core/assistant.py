"""Orkestrator: menggabungkan guard, router, tool, otak lokal dan cloud."""
from __future__ import annotations

import json
from pathlib import Path

from .cloud_brain import CloudBrain, CloudUnavailable
from .local_brain import LocalBrain, LocalUnavailable
from .router import Router, extract_path, match_tool
from .tool_descriptions import TOOL_DESCRIPTIONS
from .spec_guard import SpecGuard
from brain.cloud_bridge import CloudBridge
from brain.local_llm import LocalLLM
from brain.router import BrainRouter
from hud_state import set_state as set_hud_state
from skills.registry import select_skill
from pipeline.metadata import MetadataPipeline
from tools.files import FileTools
from tools.system import SystemTools

CONFIRM_WORDS = {"ya", "y", "konfirmasi", "konfirm", "oke", "lanjut", "jalankan", "setuju"}


class Assistant:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.cfg = json.loads((self.root / "config.json").read_text(encoding="utf-8"))
        persona = (self.root / "PERSONA.md").read_text(encoding="utf-8")

        self.system = SystemTools(self.cfg)
        spec_result = self.system.get_specs()
        self.specs = spec_result["data"]
        self.files = FileTools(self.cfg, self.root)

        self.guard = SpecGuard(self.specs)
        self.local = LocalLLM(self.cfg.get("local", {}), persona)
        self.cloud = CloudBridge(self.cfg.get("cloud", {}), persona, self.specs)
        self.metadata = MetadataPipeline(self.cfg, self.cloud, self.files)
        self.router = Router(self.local, self.cloud)
        self.brain_router = BrainRouter(self.local, self.cloud)

        self.mode = "auto"  # auto | local | cloud
        self.active_skill = "core"
        self.pending: tuple[str, dict] | None = None
        self.last_route = "idle"  # untuk UI: idle|tool|cloud|local_llm|reject|offline|confirm

        self.tools = {
            "get_specs": lambda **kw: self.system.get_specs(),
            "disk_usage": lambda **kw: self.system.disk_usage(kw.get("path", "C:\\")),
            "processes": lambda **kw: self.system.processes(kw.get("limit")),
            "internet_check": lambda **kw: self.system.internet_check(),
            "run_command": lambda **kw: self.system.run_command(
                kw.get("argv", []), confirm=kw.get("confirm", False)
            ),
            "list_dir": lambda **kw: self.files.list_dir(
                kw.get("path", "workspace"), kw.get("pattern", "*")
            ),
            "file_info": lambda **kw: self.files.file_info(kw.get("path", "workspace")),
            "read_text": lambda **kw: self.files.read_text(kw.get("path", "")),
            "hash_file": lambda **kw: self.files.hash_file(
                kw.get("path", "workspace"), kw.get("algo", "sha256")
            ),
            "find_duplicates": lambda **kw: self.files.find_duplicates(
                kw.get("path", "workspace")
            ),
            "write_csv": lambda **kw: self.files.write_csv(
                kw.get("path", "workspace/output.csv"),
                kw.get("rows", []),
                kw.get("header"),
                overwrite=kw.get("overwrite", False),
            ),
            "rename_batch": lambda **kw: self.files.rename_batch(
                kw.get("path", "workspace"), kw.get("mapping", {}),
                confirm=kw.get("confirm", False), dry_run=kw.get("dry_run"),
            ),
            "move_file": lambda **kw: self.files.move_file(
                kw.get("src", ""), kw.get("dst", ""),
                confirm=kw.get("confirm", False), dry_run=kw.get("dry_run"),
            ),
            "generate_metadata": lambda **kw: self.metadata.process_folder(
                kw.get("path", "workspace"),
                kw.get("out", "workspace/adobe_stock.csv"),
                kw.get("limit"),
                kw.get("dry_run", True),
                kw.get("style_hint", ""),
            ),
        }

    # ---------- aksi ----------
    def _execute(self, tool_name: str, args: dict) -> str:
        func = self.tools.get(tool_name)
        if func is None:
            return f"Tool '{tool_name}' tidak dikenal."
        try:
            result = func(**args)
        except TypeError as exc:
            return f"Argumen tool tidak lengkap: {exc}"
        except Exception as exc:
            return f"Tool gagal: {exc}"
        if isinstance(result, dict):
            if result.get("need_confirmation"):
                self.pending = (tool_name, dict(args))
            return result.get("message", str(result))
        return str(result)

    def _complete_args(self, tool: str, args: dict) -> dict:
        args = dict(args)
        if tool in {
            "list_dir", "hash_file", "read_text", "find_duplicates",
            "rename_batch", "file_info", "generate_metadata",
        } and not args.get("path"):
            args["path"] = "workspace"
        return args

    def _fallback_answer(self, text: str, decision: dict) -> str:
        """Coba otak lokal, lalu cloud, dengan pesan error yang jujur."""
        if decision.get("route") == "cloud":
            try:
                return self.cloud.answer(text, fresh=decision.get("fresh", False))
            except CloudUnavailable as cloud_error:
                if self.local.available():
                    try:
                        return "(Cloud gagal, pakai otak lokal)\n" + self.local.answer(text)
                    except LocalUnavailable:
                        pass
                return str(cloud_error)

        if decision.get("route") == "local_llm":
            if self.local.available():
                try:
                    plan = self.local.plan(text, TOOL_DESCRIPTIONS)
                    if plan and plan.get("tool"):
                        self.last_route = "tool"
                        return self._execute(str(plan["tool"]), plan.get("args") or {})
                    if plan and plan.get("answer"):
                        return str(plan["answer"])
                    return self.local.answer(text)
                except LocalUnavailable as local_error:
                    if self.cloud.available():
                        try:
                            return "(Otak lokal gagal, pakai cloud)\n" + self.cloud.answer(text)
                        except CloudUnavailable as cloud_error:
                            return f"{local_error}\n{cloud_error}"
                    return str(local_error)
            if self.cloud.available():
                try:
                    return "(Otak lokal belum aktif, pakai cloud)\n" + self.cloud.answer(text)
                except CloudUnavailable as cloud_error:
                    return str(cloud_error)
            return (
                "Otak lokal belum aktif dan API key Gemini belum diset. "
                "Buka README.md untuk cara mengaktifkan."
            )
        return decision.get("message", "Tidak ada jalur yang tersedia.")

    # ---------- API publik ----------
    def handle(self, text: str) -> str:
        """Bungkus _handle dengan sinyal state untuk avatar HUD."""
        if not text.strip():
            set_hud_state("idle", "idle")
            return ""
        self.active_skill = select_skill(text)
        set_hud_state("thinking", "pending")
        try:
            return self._handle(text)
        finally:
            final = {"reject": "alerting", "offline": "failed"}.get(
                self.last_route, "working"
            )
            set_hud_state(final, self.last_route)

    def _handle(self, text: str) -> str:
        text = text.strip()
        if not text:
            return ""

        if self.pending and text.lower() in CONFIRM_WORDS:
            tool, args = self.pending
            self.pending = None
            args["confirm"] = True
            args["dry_run"] = False
            self.last_route = "confirm"
            return self._execute(tool, args)

        guard_result = self.guard.classify(text)
        if guard_result["route"] == "reject":
            self.last_route = "reject"
            return guard_result["message"]

        detected = match_tool(text)
        if detected and self.mode != "cloud":
            self.last_route = "tool"
            return self._execute(detected[0], self._complete_args(detected[0], detected[1]))

        if self.mode == "cloud" and self.cloud.available():
            self.last_route = "cloud"
            return self._fallback_answer(text, {"route": "cloud", "fresh": False})
        if self.mode == "local" and self.local.available():
            self.last_route = "local_llm"
            return self._fallback_answer(text, {"route": "local_llm"})

        brain = self.brain_router.decide(text)
        if brain["target"] == "cloud":
            decision = {"route": "cloud", "fresh": "penalaran" in brain["reason"]}
        elif brain["target"] == "local":
            decision = {"route": "local_llm"}
        else:
            decision = {
                "route": "offline",
                "message": "Otak lokal dan cloud tidak tersedia.",
            }
        self.last_route = decision["route"]
        if decision["route"] in {"cloud", "local_llm"}:
            return self._fallback_answer(text, decision)
        if decision["route"] == "tool":
            tool, args = detected or ("list_dir", {"path": "workspace"})
            return self._execute(tool, self._complete_args(tool, args))
        return decision["message"]

    def status(self) -> str:
        return (
            f"Mode: {self.mode}\n"
            f"Otak lokal: {'aktif' if self.local.available() else 'tidak aktif'} "
            f"({self.cfg['local'].get('base_url')})\n"
            f"Gemini API: {'aktif' if self.cloud.available() else 'belum diset / tidak aktif'}\n"
            f"Area kerja: {self.files.allowed}\n"
            f"Dry-run default: {self.cfg.get('dry_run_default')}"
        )

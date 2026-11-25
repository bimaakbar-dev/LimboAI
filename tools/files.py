"""Operasi file/folder dengan pembatas area kerja (sandbox)."""
from __future__ import annotations

import csv
import hashlib
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any


class SafetyError(Exception):
    """Dilempar ketika path berada di luar area yang diizinkan."""


class FileTools:
    def __init__(self, config: dict, project_root: Path):
        self.cfg = config
        self.root = Path(project_root).resolve()
        self.workspace = self.root / config.get("workspace", "workspace")
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.allowed: list[Path] = []
        for raw in config.get("allowed_roots", ["workspace"]):
            path = Path(raw).expanduser()
            if not path.is_absolute():
                path = self.root / path
            self.allowed.append(path.resolve())
        if self.workspace.resolve() not in self.allowed:
            self.allowed.append(self.workspace.resolve())

    # ---------- keamanan ----------
    def resolve(self, path: str | None) -> Path:
        raw = path or "workspace"
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = self.root / candidate
        candidate = candidate.resolve()
        for base in self.allowed:
            try:
                candidate.relative_to(base)
                return candidate
            except ValueError:
                continue
        raise SafetyError(
            f"Path '{candidate}' berada di luar area yang diizinkan. "
            "Tambahkan folder tersebut ke 'allowed_roots' di config.json."
        )

    @staticmethod
    def _ok(message: str, **data: Any) -> dict:
        return {"ok": True, "message": message, "data": data}

    @staticmethod
    def _fail(message: str) -> dict:
        return {"ok": False, "message": message}

    def _destructive_gate(self, args: dict, label: str) -> dict | None:
        """Mengembalikan respons 'butuh konfirmasi' bila belum ada konfirmasi."""
        if not self.cfg.get("confirm_destructive", True):
            return None
        if args.get("confirm") is not True:
            return {
                "ok": False,
                "need_confirmation": True,
                "message": f"Rencana: {label}\nBelum dijalankan. Ketik 'konfirmasi' untuk melanjutkan.",
            }
        if args.get("dry_run", self.cfg.get("dry_run_default", True)):
            return self._ok(f"DRY RUN — {label}\nTidak ada perubahan yang ditulis.")
        return None

    # ---------- tool ----------
    def list_dir(self, path: str = "workspace", pattern: str = "*") -> dict:
        try:
            target = self.resolve(path)
            if not target.is_dir():
                return self._fail(f"Bukan folder: {target}")
            limit = int(self.cfg.get("limits", {}).get("max_list_items", 200))
            items = sorted(target.glob(pattern))[:limit]
            lines = []
            for item in items:
                if item.is_dir():
                    lines.append(f"[DIR ] {item.name}")
                else:
                    lines.append(f"[FILE] {item.name}  ({item.stat().st_size:,} B)")
            tail = "" if len(items) < limit else f"\n... dibatasi {limit} item."
            return self._ok(f"Isi {target}:\n" + "\n".join(lines) + tail, path=str(target), count=len(items))
        except (SafetyError, OSError) as exc:
            return self._fail(str(exc))

    def file_info(self, path: str) -> dict:
        try:
            target = self.resolve(path)
            if not target.exists():
                return self._fail(f"Tidak ditemukan: {target}")
            stat = target.stat()
            return self._ok(
                f"{target}\nUkuran: {stat.st_size:,} byte\nTipe: {'folder' if target.is_dir() else 'file'}",
                path=str(target), size=stat.st_size, is_dir=target.is_dir(),
            )
        except (SafetyError, OSError) as exc:
            return self._fail(str(exc))

    def read_text(self, path: str) -> dict:
        try:
            target = self.resolve(path)
            limit = int(self.cfg.get("limits", {}).get("max_file_read_bytes", 200000))
            size = target.stat().st_size
            if size > limit:
                return self._fail(f"File terlalu besar ({size:,} B). Batas {limit:,} B.")
            text = target.read_text(encoding="utf-8", errors="replace")
            return self._ok(f"Isi {target}:\n{text}", path=str(target), text=text)
        except (SafetyError, OSError) as exc:
            return self._fail(str(exc))

    def hash_file(self, path: str, algo: str = "sha256") -> dict:
        try:
            target = self.resolve(path)
            if not target.is_file():
                return self._fail(f"Bukan file: {target}")
            digest = hashlib.new(algo)
            with target.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            value = digest.hexdigest()
            return self._ok(f"{algo}: {value}", path=str(target), hash=value)
        except (SafetyError, OSError, ValueError) as exc:
            return self._fail(str(exc))

    def find_duplicates(self, path: str = "workspace") -> dict:
        try:
            target = self.resolve(path)
            if not target.is_dir():
                return self._fail(f"Bukan folder: {target}")
            by_size: dict[int, list[Path]] = defaultdict(list)
            for file in target.rglob("*"):
                if file.is_file():
                    by_size[file.stat().st_size].append(file)
            groups: list[list[str]] = []
            for same_size in by_size.values():
                if len(same_size) < 2:
                    continue
                by_hash: dict[str, list[Path]] = defaultdict(list)
                for file in same_size:
                    digest = hashlib.sha256(file.read_bytes()).hexdigest()
                    by_hash[digest].append(file)
                for files in by_hash.values():
                    if len(files) > 1:
                        groups.append([str(p) for p in files])
            if not groups:
                return self._ok("Tidak ditemukan file duplikat (berdasarkan SHA-256).", groups=[])
            text = "File duplikat:\n" + "\n\n".join(
                "\n".join(f"  - {p}" for p in group) for group in groups
            )
            return self._ok(text, groups=groups)
        except (SafetyError, OSError) as exc:
            return self._fail(str(exc))

    def write_csv(self, path: str, rows: list[list[Any]], header: list[str] | None = None,
                  overwrite: bool = False) -> dict:
        try:
            target = self.resolve(path)
            if target.exists() and not overwrite:
                return self._fail(
                    f"File sudah ada: {target}. Tambahkan overwrite=true untuk menimpa."
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                if header:
                    writer.writerow(header)
                writer.writerows(rows)
            return self._ok(f"CSV ditulis: {target} ({len(rows)} baris)", path=str(target))
        except (SafetyError, OSError, csv.Error) as exc:
            return self._fail(str(exc))

    def rename_batch(self, path: str, mapping: dict[str, str], confirm: bool = False,
                     dry_run: bool | None = None) -> dict:
        folder = self.resolve(path)
        label = f"rename {len(mapping)} file di {folder}"
        args = {"confirm": confirm, "dry_run": self.cfg.get("dry_run_default", True) if dry_run is None else dry_run}
        gate = self._destructive_gate(args, label)
        if gate:
            return gate
        done, errors = [], []
        for old, new in mapping.items():
            src, dst = folder / old, folder / new
            try:
                src.rename(dst)
                done.append(f"{old} -> {new}")
            except OSError as exc:
                errors.append(f"{old}: {exc}")
        message = f"Renamed {len(done)} file." + ("\nGagal:\n" + "\n".join(errors) if errors else "")
        return self._ok(message, done=done, errors=errors)

    def move_file(self, src: str, dst: str, confirm: bool = False,
                  dry_run: bool | None = None) -> dict:
        source, destination = self.resolve(src), self.resolve(dst)
        args = {"confirm": confirm, "dry_run": self.cfg.get("dry_run_default", True) if dry_run is None else dry_run}
        gate = self._destructive_gate(args, f"memindahkan {source} -> {destination}")
        if gate:
            return gate
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            return self._ok(f"Dipindahkan: {source} -> {destination}")
        except OSError as exc:
            return self._fail(str(exc))

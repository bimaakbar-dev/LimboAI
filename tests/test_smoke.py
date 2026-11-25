"""Tes ringan tanpa llama-server / API key."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.assistant import Assistant  # noqa: E402
from core.cloud_brain import CloudBrain, CloudUnavailable  # noqa: E402
from core.local_brain import build_plan_system  # noqa: E402
from core.router import match_tool  # noqa: E402
from core.tool_descriptions import TOOL_DESCRIPTIONS  # noqa: E402
from pipeline.metadata import normalize_row, parse_json_response  # noqa: E402
from core.spec_guard import SpecGuard  # noqa: E402
from tools.files import FileTools, SafetyError  # noqa: E402


class SmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.files = FileTools(self.config, self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_sandbox_menolak_path_luar(self) -> None:
        with self.assertRaises(SafetyError):
            self.files.resolve("C:/Windows/System32")

    def test_hash_file(self) -> None:
        target = self.files.workspace / "contoh.txt"
        target.write_text("halo", encoding="utf-8")
        result = self.files.hash_file("workspace/contoh.txt")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["data"]["hash"]), 64)

    def test_write_csv(self) -> None:
        result = self.files.write_csv(
            "workspace/hasil.csv",
            [["a.jpg", "Judul", "keyword"]],
            header=["Filename", "Title", "Keywords"],
        )
        self.assertTrue(result["ok"])
        self.assertTrue((self.files.workspace / "hasil.csv").exists())
        again = self.files.write_csv("workspace/hasil.csv", [["b.jpg"]])
        self.assertFalse(again["ok"])

    def test_guard_menolak_training(self) -> None:
        guard = SpecGuard({"cpu": "i5-3570", "ram_gb": 16, "gpu": "GT 710", "gpu_vram_gb": 2})
        result = guard.classify("tolong latih model AI di PC ini")
        self.assertEqual(result["route"], "reject")
        self.assertIn("Kaggle", result["message"])

    def test_guard_info_training_di_cloud_diperbolehkan(self) -> None:
        guard = SpecGuard({"cpu": "i5-3570", "ram_gb": 16, "gpu": "GT 710", "gpu_vram_gb": 2})
        result = guard.classify("bagaimana cara latih di colab gratis?")
        self.assertNotEqual(result["route"], "reject")

    def test_router_tool(self) -> None:
        self.assertEqual(match_tool("cek spec pc")[0], "get_specs")
        self.assertEqual(match_tool("lihat isi folder workspace")[0], "list_dir")
        self.assertEqual(match_tool("cari duplikat di folder workspace")[0], "find_duplicates")
        self.assertEqual(match_tool("rename file a.txt jadi b.txt")[0], "rename_batch")
        self.assertEqual(match_tool("buat metadata stock dari folder gambar")[0], "generate_metadata")

    def test_parse_json_respons(self) -> None:
        data = parse_json_response('```json\n{"title": "Halo", "keywords": ["a"]}\n```')
        self.assertEqual(data["title"], "Halo")
        self.assertIsNone(parse_json_response("bukan json"))

    def test_normalisasi_metadata(self) -> None:
        row = normalize_row(
            {
                "title": "x" * 100,
                "keywords": ["BATU", "batu", "pemandangan", ""],
                "category": "Kategori Aneh",
                "description": "  sebuah   deskripsi  ",
            },
            "foto_01.jpg",
        )
        self.assertEqual(len(row["Title"]), 70)
        self.assertEqual(row["Keywords"], "batu, pemandangan")
        self.assertEqual(row["Category"], "Other")
        self.assertEqual(row["Description"], "sebuah deskripsi")

    def test_plan_otak_lokal_dijalankan(self) -> None:
        shutil.copy(ROOT / "config.json", self.root / "config.json")
        shutil.copy(ROOT / "PERSONA.md", self.root / "PERSONA.md")
        assistant = Assistant(self.root)
        plan = {"tool": "get_specs", "args": {}, "answer": "ok"}

        with patch.object(assistant.local, "available", return_value=True), \
             patch.object(assistant.local, "plan", return_value=plan):
            reply = assistant.handle("halo")

        self.assertIn("CPU", reply)
        self.assertEqual(assistant.last_route, "tool")

    def test_dataset_system_prompt_sama_dengan_runtime(self) -> None:
        dataset = ROOT / "training" / "dataset.jsonl"
        if not dataset.exists():
            self.skipTest("dataset.jsonl belum dibuat")
        first = json.loads(dataset.read_text(encoding="utf-8").splitlines()[0])
        persona = (ROOT / "PERSONA.md").read_text(encoding="utf-8")
        self.assertEqual(
            first["messages"][0]["content"],
            build_plan_system(persona, TOOL_DESCRIPTIONS),
        )

    def test_dataset_mengandung_guard(self) -> None:
        dataset = ROOT / "training" / "dataset.jsonl"
        if not dataset.exists():
            self.skipTest("dataset.jsonl belum dibuat")
        text = dataset.read_text(encoding="utf-8")
        self.assertIn("Kaggle", text)
        self.assertIn("get_specs", text)

    def test_upload_gambar_default_nonaktif(self) -> None:
        cloud = CloudBrain(
            {"enabled": True, "api_key_env": "GEMINI_API_KEY", "allow_image_upload": False},
            "", {},
        )
        with self.assertRaises(CloudUnavailable):
            cloud.vision(b"bytes", "image/jpeg", "deskripsikan")

    def test_alur_konfirmasi(self) -> None:
        shutil.copy(ROOT / "config.json", self.root / "config.json")
        shutil.copy(ROOT / "PERSONA.md", self.root / "PERSONA.md")
        (self.files.workspace / "a.txt").write_text("isi", encoding="utf-8")

        assistant = Assistant(self.root)
        first = assistant.handle("rename file a.txt jadi b.txt di folder workspace")
        self.assertIn("konfirmasi", first.lower())
        self.assertFalse((self.files.workspace / "b.txt").exists())

        second = assistant.handle("konfirmasi")
        self.assertTrue((self.files.workspace / "b.txt").exists())
        self.assertIn("rename", second.lower())


if __name__ == "__main__":
    unittest.main()

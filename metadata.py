"""CLI pipeline metadata stock asset -> CSV Adobe Stock.

Contoh:
    python metadata.py workspace/gambar --limit 5 --dry-run
    python metadata.py workspace/gambar --out workspace/adobe_stock.csv --no-dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.cloud_brain import CloudBrain
from pipeline.metadata import MetadataPipeline
from tools.files import FileTools
from tools.system import SystemTools

ROOT = Path(__file__).resolve().parent


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(description="Buat metadata Adobe Stock dari folder gambar.")
    parser.add_argument("folder", nargs="?", default="workspace", help="Folder berisi gambar")
    parser.add_argument("--out", default="workspace/adobe_stock.csv", help="Path CSV output")
    parser.add_argument("--limit", type=int, default=None, help="Batasi jumlah gambar")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Hanya preview (default)")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="Tulis CSV sebenarnya")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--style", default="", help="Gaya keyword yang diinginkan")
    parser.add_argument(
        "--allow-upload", action="store_true",
        help="Izinkan kirim gambar ke API gratis untuk percobaan ini saja",
    )
    parser.add_argument("--model", default=None, help="Override model Gemini untuk percobaan ini")
    args = parser.parse_args()

    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    if args.allow_upload:
        config["cloud"]["allow_image_upload"] = True
    if args.model:
        config["cloud"]["model"] = args.model
        config["cloud"]["grounding_model"] = args.model
    persona = (ROOT / "PERSONA.md").read_text(encoding="utf-8")
    specs = SystemTools(config).get_specs()["data"]
    cloud = CloudBrain(config.get("cloud", {}), persona, specs)
    files = FileTools(config, ROOT)
    pipeline = MetadataPipeline(config, cloud, files)

    print(pipeline.process_folder(
        path=args.folder,
        out=args.out,
        limit=args.limit,
        dry_run=args.dry_run,
        style_hint=args.style,
    ))


if __name__ == "__main__":
    main()

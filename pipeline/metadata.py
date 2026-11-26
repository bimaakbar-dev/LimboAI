"""Gambar -> metadata Adobe Stock (judul, keyword, kategori, deskripsi) -> CSV."""
from __future__ import annotations

import json
import mimetypes
import re
from pathlib import Path
from typing import Any

from brain.cloud_bridge import CloudBridge, CloudUnavailable
from tools.files import FileTools

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
CSV_HEADER = ["Filename", "Title", "Description", "Keywords", "Category", "Releases"]

CATEGORIES = [
    "Animals", "Architecture", "Backgrounds", "Beauty", "Business", "Careers",
    "Concepts", "Education", "Environment", "Fashion", "Food", "Healthcare",
    "Hobbies", "Holidays", "Household", "Industry", "Landscapes", "Music",
    "Nature", "Objects", "People", "Places", "Science", "Sports", "Technology",
    "Textures", "Travel", "Vehicles", "Weather", "Wildlife", "Other",
]

PROMPT_TEMPLATE = """Kamu adalah editor metadata aset stock foto.

Lihat gambar ini dan balas HANYA dengan JSON valid, tanpa teks lain:
{{"title": "...", "keywords": ["..."], "category": "...", "description": "..."}}

Aturan:
- "title": maksimal 70 karakter, deskriptif, singkat dan natural, bukan daftar keyword.
- "keywords": 30 sampai 50 kata/frasa pendek, huruf kecil, relevan dengan isi gambar, tanpa duplikat.
- "category": pilih tepat satu dari daftar ini: {categories}
- "description": 1-2 kalimat ringkas tentang isi gambar.
{custom_hint}
Jangan mengarang elemen yang tidak terlihat. Jangan menambahkan penjelasan di luar JSON."""


def parse_json_response(raw: str) -> dict[str, Any] | None:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        value = json.loads(cleaned[start:end + 1])
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        return None


def normalize_row(data: dict[str, Any], filename: str) -> dict[str, str]:
    title = re.sub(r"\s+", " ", str(data.get("title", "")).strip())[:70]
    if not title:
        title = Path(filename).stem.replace("_", " ")[:70]

    raw_keywords = data.get("keywords", [])
    if isinstance(raw_keywords, str):
        raw_keywords = [part for part in re.split(r"[,\n]", raw_keywords)]

    keywords: list[str] = []
    for item in raw_keywords:
        keyword = re.sub(r"\s+", " ", str(item).strip().lower())
        if keyword and keyword not in keywords:
            keywords.append(keyword)
    keywords = keywords[:50]

    category = str(data.get("category", "Other")).strip()
    if category not in CATEGORIES:
        category = "Other"

    description = re.sub(r"\s+", " ", str(data.get("description", "")).strip())
    return {
        "Filename": filename,
        "Title": title,
        "Description": description,
        "Keywords": ", ".join(keywords),
        "Category": category,
        "Releases": "",
    }


class MetadataPipeline:
    def __init__(self, config: dict, cloud: CloudBridge, files: FileTools):
        self.cloud = cloud
        self.files = files
        self.max_bytes = int(config.get("limits", {}).get("max_image_bytes", 10485760))

    def collect_images(self, path: str = "workspace") -> list[Path]:
        target = self.files.resolve(path)
        if not target.is_dir():
            return []
        return sorted(
            file for file in target.rglob("*")
            if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS
        )

    def process_folder(
        self,
        path: str = "workspace",
        out: str = "workspace/adobe_stock.csv",
        limit: int | None = None,
        dry_run: bool = True,
        style_hint: str = "",
    ) -> str:
        if not self.cloud.available():
            return (
                "Gemini API belum tersedia. Set GEMINI_API_KEY terlebih dahulu. "
                "Pipeline metadata membutuhkan model vision di cloud."
            )
        if not self.cloud.allow_images:
            return (
                "Upload gambar sedang NONAKTIF demi privasi. Jika gambar kamu boleh dikirim "
                "ke API gratis, ubah 'allow_image_upload' menjadi true di config.json."
            )

        images = self.collect_images(path)
        if not images:
            return f"Tidak ada gambar (.jpg/.jpeg/.png/.webp) di folder '{path}'."

        if limit is not None:
            try:
                images = images[:max(1, int(limit))]
            except (TypeError, ValueError):
                pass

        prompt = PROMPT_TEMPLATE.format(
            categories=", ".join(CATEGORIES),
            custom_hint=(f"Gaya keyword yang diinginkan: {style_hint}." if style_hint else ""),
        )

        rows: list[dict[str, str]] = []
        errors: list[str] = []
        for image in images:
            if image.stat().st_size > self.max_bytes:
                errors.append(f"{image.name}: terlalu besar (> {self.max_bytes} byte)")
                continue
            mime = mimetypes.guess_type(image.name)[0] or "image/jpeg"
            try:
                raw = self.cloud.vision(image.read_bytes(), mime, prompt)
            except CloudUnavailable as exc:
                return f"{exc}\n(Sudah diproses {len(rows)} gambar sebelum error.)"
            except OSError as exc:
                errors.append(f"{image.name}: gagal dibaca ({exc})")
                continue
            data = parse_json_response(raw)
            if data is None:
                errors.append(f"{image.name}: Gemini tidak mengembalikan JSON valid")
                continue
            rows.append(normalize_row(data, image.name))

        if not rows:
            return "Tidak ada metadata yang berhasil dibuat." + (
                "\nError:\n" + "\n".join(errors) if errors else ""
            )

        if dry_run:
            preview = []
            for row in rows[:3]:
                preview.append(
                    f"{row['Filename']} | {row['Title']} | {row['Category']} | "
                    f"{len(row['Keywords'].split(', '))} keyword"
                )
            return (
                f"DRY RUN — {len(rows)} gambar berhasil dianalisis. "
                "Belum ada CSV yang ditulis.\n" + "\n".join(preview)
                + ("\n... dan lain-lain" if len(rows) > 3 else "")
                + ("\n\nError:\n" + "\n".join(errors) if errors else "")
                + "\nUlangi dengan dry_run=false untuk menulis CSV."
            )

        result = self.files.write_csv(
            out,
            [[row[column] for column in CSV_HEADER] for row in rows],
            header=CSV_HEADER,
            overwrite=True,
        )
        return result["message"] + (
            "\nError:\n" + "\n".join(errors) if errors else ""
        )

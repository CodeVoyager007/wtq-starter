"""Image loading: fix phone rotation (EXIF), keep detail, keep the request small."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageOps

from .llm import Image

MAX_SIDE = 2400
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")


def load(path: Path) -> Image:
    with PILImage.open(path) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        if max(img.size) > MAX_SIDE:
            img.thumbnail((MAX_SIDE, MAX_SIDE), PILImage.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
    return Image(data=buffer.getvalue(), mime_type="image/png")


def find_bill(bills_dir: Path, bill_id: str) -> Path | None:
    for suffix in IMAGE_SUFFIXES:
        for candidate in (bills_dir / f"{bill_id}{suffix}", bills_dir / f"{bill_id}{suffix.upper()}"):
            if candidate.exists():
                return candidate
    return None

"""Image loading: fix phone rotation (EXIF), upscale small photos, cap very large ones."""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image as PILImage
from PIL import ImageFilter, ImageOps

from .llm import Image

MAX_SIDE = 2400
MIN_SIDE = 2000  # small photos are upscaled so each digit gets more pixels
MAX_UPSCALE = 3.0
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")


def load(path: Path) -> Image:
    return load_bytes(Path(path).read_bytes())


def load_bytes(data: bytes) -> Image:
    with PILImage.open(io.BytesIO(data)) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        long_side = max(img.size)
        if long_side > MAX_SIDE:
            img.thumbnail((MAX_SIDE, MAX_SIDE), PILImage.LANCZOS)
        elif long_side < MIN_SIDE:
            scale = min(MIN_SIDE / long_side, MAX_UPSCALE)
            img = img.resize((round(img.width * scale), round(img.height * scale)), PILImage.LANCZOS)
            img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=60, threshold=2))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
    return Image(data=buffer.getvalue(), mime_type="image/png")


def find_bill(bills_dir: Path, bill_id: str) -> Path | None:
    for suffix in IMAGE_SUFFIXES:
        for candidate in (bills_dir / f"{bill_id}{suffix}", bills_dir / f"{bill_id}{suffix.upper()}"):
            if candidate.exists():
                return candidate
    return None

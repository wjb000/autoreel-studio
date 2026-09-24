"""Generate a simple thumbnail PNG/JPG from title text."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def make_thumbnail(title: str, out_path: Path, size: tuple[int, int] = (1280, 720)) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", size, (15, 23, 42))
    draw = ImageDraw.Draw(img)
    # Accent bar
    draw.rectangle([0, size[1] - 120, size[0], size[1]], fill=(99, 102, 241))
    draw.rectangle([0, 0, 16, size[1]], fill=(129, 140, 248))

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
        small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
        small = font

    # Word-wrap title
    words = title.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > size[0] - 80 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    lines = lines[:4]

    y = size[1] // 2 - len(lines) * 36
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (size[0] - (bbox[2] - bbox[0])) // 2
        draw.text((x + 2, y + 2), line, fill=(0, 0, 0), font=font)
        draw.text((x, y), line, fill=(248, 250, 252), font=font)
        y += 70

    badge = "AutoReel Studio"
    draw.text((40, size[1] - 80), badge, fill=(255, 255, 255), font=small)

    if out_path.suffix.lower() in (".jpg", ".jpeg"):
        img.save(out_path, quality=92)
    else:
        img.save(out_path)
    return out_path

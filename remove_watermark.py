# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy", "pillow"]
# ///
"""
Usage:
    uv run remove_watermark.py --input "Sample Input" --output "Output"
    uv run remove_watermark.py --input page.jpg --output Output --light 185
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def clean_image(
    img: Image.Image,
    light: int,
    red: int,
    pink_min: int,
) -> tuple[Image.Image, float]:
    """Return (cleaned image, % of pixels whitened)."""
    arr = np.asarray(img.convert("RGB")).astype(np.int16)
    R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]

    min_ch = arr.min(axis=2)                     # "whiteness" — high = light
    redness = R - np.maximum(G, B)               # salmon watermark leans red

    light_mask = min_ch >= light                 # (a) too light to be content
    pink_mask = (redness >= red) & (min_ch >= pink_min)  # (b) tinted + light

    whiten = light_mask | pink_mask

    out = arr.copy()
    out[whiten] = 255
    pct = 100.0 * float(whiten.mean())
    return Image.fromarray(out.astype(np.uint8), "RGB"), pct


def iter_images(input_path: Path):
    if input_path.is_file():
        yield input_path
    else:
        for p in sorted(input_path.iterdir()):
            if p.suffix.lower() in EXTS:
                yield p


def main() -> int:
    ap = argparse.ArgumentParser(description="Remove light tinted watermarks from document scans.")
    ap.add_argument("--input", required=True, help="Image file or folder of images")
    ap.add_argument("--output", required=True, help="Output folder for cleaned images")
    ap.add_argument("--light", type=int, default=188,
                    help="Whiten any pixel whose min channel >= this (default 188)")
    ap.add_argument("--red", type=int, default=10,
                    help="Redness (R - max(G,B)) at/above which a light pixel is treated as watermark (default 10)")
    ap.add_argument("--pink-min", type=int, default=158,
                    help="A tinted pixel must also have min channel >= this to be whitened (default 158)")
    ap.add_argument("--suffix", default="_clean",
                    help="Filename suffix for outputs (default '_clean'); use '' to keep original names")
    args = ap.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.output)
    if not input_path.exists():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)

    images = list(iter_images(input_path))
    if not images:
        print(f"error: no images found in {input_path}", file=sys.stderr)
        return 1

    for p in images:
        with Image.open(p) as im:
            cleaned, pct = clean_image(im, args.light, args.red, args.pink_min)
        out_name = f"{p.stem}{args.suffix}.png"
        out_path = out_dir / out_name
        cleaned.save(out_path)
        print(f"{p.name:45s} -> {out_path.name:45s}  ({pct:4.1f}% whitened)")

    print(f"\nDone. {len(images)} image(s) written to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

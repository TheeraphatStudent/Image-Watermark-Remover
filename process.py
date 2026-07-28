# /// script
# requires-python = ">=3.9"
# dependencies = ["numpy", "pillow", "lxml", "cairosvg", "vtracer"]
# ///
"""
Document watermark toolkit — SVG + raster, with text-quality upscaling.

Handles two kinds of input, auto-detected per file:

  1. SVG reports (e.g. the OCM "controller.thaioil UAT" exports)
     The watermark is a small PNG tile embedded MANY times (tiled across the
     page) via <image> elements, while the real content is genuine vector
     <text>/<rect>. We remove the watermark LOSSLESSLY by deleting the repeated
     tiles and keeping everything else (including one-off images such as a
     signature). Output text stays perfectly crisp because it is never
     rasterised. Optionally we also render a high-DPI PNG.

  2. Raster scans (.jpg/.png)
     The watermark is a light, salmon-tinted overlay while the content is dark.
     We whiten only light+tinted pixels (content preserved), then optionally
     upscale 2x/4x with sharpening for better text clarity, and export SVG
     (true vector trace via vtracer, and/or the raster embedded in a scalable
     SVG container).

Usage:
    # clean everything in a folder (SVGs cleaned losslessly, rasters whitened)
    uv run process.py --input "Sample Input" --output "Output"

    # also upscale rasters 2x and emit both SVG styles; render cleaned SVGs to PNG
    uv run process.py --input "Sample Input" --output "Output" \
        --scale 2 --svg both --rasterize-svg

    # single file
    uv run process.py --input page.jpg --output Output --scale 4
"""

from __future__ import annotations

import argparse
import base64
import io
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

RASTER_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
SVG_NS = "{http://www.w3.org/2000/svg}"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


# --------------------------------------------------------------------------- #
# SVG watermark removal (lossless)
# --------------------------------------------------------------------------- #
def _img_href(el) -> str | None:
    return el.get("href") or el.get(XLINK_HREF)


def strip_svg_watermark(svg_path: Path, tile_min_repeat: int = 3):
    """Delete repeated watermark <image> tiles; keep unique images + all vectors.

    The watermark is tiled, so its (identical) href appears many times. Genuine
    embedded images (logo, signature) appear once. Anything whose href repeats
    at least `tile_min_repeat` times is treated as watermark.

    Returns (cleaned_xml_bytes, n_removed, n_kept).
    """
    from lxml import etree

    tree = etree.parse(str(svg_path))
    root = tree.getroot()
    images = root.findall(".//" + SVG_NS + "image")
    counts = Counter(_img_href(e) for e in images)

    removed = kept = 0
    for el in images:
        href = _img_href(el)
        if href is not None and counts[href] >= tile_min_repeat:
            el.getparent().remove(el)
            removed += 1
        else:
            kept += 1

    xml = etree.tostring(tree, xml_declaration=True, encoding="utf-8")
    return xml, removed, kept


def rasterize_svg(svg_source, out_png: Path, scale: float = 1.0, dpi: int | None = None):
    """Render an SVG (path or bytes) to PNG. scale multiplies the native size.

    Note: text is rendered with the fonts installed on THIS machine. Thai text
    (TH SarabunPSK) needs that font present to render correctly.
    """
    import cairosvg

    kwargs = {"write_to": str(out_png)}
    if dpi:
        kwargs["dpi"] = dpi
    if scale and scale != 1.0:
        kwargs["scale"] = scale
    if isinstance(svg_source, (bytes, bytearray)):
        cairosvg.svg2png(bytestring=bytes(svg_source), **kwargs)
    else:
        cairosvg.svg2png(url=str(svg_source), **kwargs)


# --------------------------------------------------------------------------- #
# Raster watermark removal (light + tinted -> white)
# --------------------------------------------------------------------------- #
def whiten_watermark(img: Image.Image, light: int = 188, red: int = 10, pink_min: int = 158):
    """Whiten light/tinted watermark pixels; preserve dark ink. Returns (img, pct)."""
    arr = np.asarray(img.convert("RGB")).astype(np.int16)
    R, G, B = arr[..., 0], arr[..., 1], arr[..., 2]
    min_ch = arr.min(axis=2)
    redness = R - np.maximum(G, B)

    whiten = (min_ch >= light) | ((redness >= red) & (min_ch >= pink_min))
    out = arr.copy()
    out[whiten] = 255
    return Image.fromarray(out.astype(np.uint8), "RGB"), 100.0 * float(whiten.mean())


# --------------------------------------------------------------------------- #
# Text-quality enhancement (upscale + sharpen)
# --------------------------------------------------------------------------- #
def enhance(img: Image.Image, scale: int = 1, sharpen: bool = True) -> Image.Image:
    """High-quality upscale (Lanczos) plus an unsharp pass to crisp up text."""
    out = img
    if scale and scale > 1:
        out = out.resize((out.width * scale, out.height * scale), Image.LANCZOS)
    if sharpen:
        # radius/percent tuned for document text: sharpen edges without halos
        out = out.filter(ImageFilter.UnsharpMask(radius=1.2, percent=110, threshold=2))
    return out


# --------------------------------------------------------------------------- #
# SVG export from raster
# --------------------------------------------------------------------------- #
def raster_to_vector_svg(img: Image.Image, out_svg: Path, trace_scale: int = 3, binary: bool = True):
    """True vector trace via vtracer — resolution-independent output.

    Tracing tiny text straight from a low-res scan yields mushy blobs, so we
    first upscale (default 3x) to give the tracer enough edge detail; the result
    is legible and fully scalable. Binary mode (the default) traces black-on-white
    only: it is fast, memory-light, and crispest for these near-black government
    forms — colour (e.g. a blue signature) is dropped here but is preserved in the
    upscaled PNG and the raster-embedded SVG. Colour mode keeps coloured ink but is
    much heavier and can exhaust memory on dense, full-page documents.
    """
    import os
    import tempfile

    import vtracer

    up = img.convert("RGB")
    if trace_scale and trace_scale > 1:
        up = up.resize((up.width * trace_scale, up.height * trace_scale), Image.LANCZOS)

    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    up.save(tmp)
    try:
        vtracer.convert_image_to_svg_py(
            tmp,
            str(out_svg),
            colormode="binary" if binary else "color",
            mode="spline",       # smooth curves (good for text)
            filter_speckle=2,
            color_precision=6,
            corner_threshold=60,
            path_precision=8,
        )
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def raster_embed_svg(img: Image.Image, out_svg: Path):
    """Embed the raster (PNG) inside a scalable SVG container sized to the image."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    w, h = img.size
    svg = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
        f'  <image width="{w}" height="{h}" '
        f'xlink:href="data:image/png;base64,{b64}"/>\n'
        f'</svg>\n'
    )
    out_svg.write_text(svg, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Per-file drivers
# --------------------------------------------------------------------------- #
def process_svg(path: Path, out_dir: Path, args) -> None:
    xml, removed, kept = strip_svg_watermark(path, args.tile_min_repeat)
    clean_path = out_dir / f"{path.stem}_clean.svg"
    clean_path.write_bytes(xml)
    print(f"[SVG]  {path.name:22s} watermark tiles removed={removed:2d} kept={kept}  -> {clean_path.name}")

    if args.rasterize_svg:
        scale = args.scale if args.scale and args.scale > 1 else 2
        png_path = out_dir / f"{path.stem}_clean_x{scale}.png"
        try:
            rasterize_svg(xml, png_path, scale=scale, dpi=args.dpi)
            print(f"       rendered PNG x{scale}{f' @ {args.dpi}dpi' if args.dpi else ''} -> {png_path.name}")
        except Exception as e:  # noqa: BLE001
            print(f"       (skipped PNG render: {e})", file=sys.stderr)


def process_raster(path: Path, out_dir: Path, args) -> None:
    with Image.open(path) as im:
        cleaned, pct = whiten_watermark(im, args.light, args.red, args.pink_min)

    # keep a base (un-upscaled) cleaned image for tracing
    base_clean = cleaned
    final = enhance(cleaned, args.scale, sharpen=not args.no_sharpen)

    suffix = f"_clean_x{args.scale}" if args.scale and args.scale > 1 else "_clean"
    png_path = out_dir / f"{path.stem}{suffix}.png"
    final.save(png_path)
    print(f"[IMG]  {path.name:22s} {pct:4.1f}% whitened  x{max(args.scale,1)}  -> {png_path.name}")

    if args.svg in ("vector", "both"):
        vec_path = out_dir / f"{path.stem}_vector.svg"
        try:
            raster_to_vector_svg(base_clean, vec_path, trace_scale=args.trace_scale, binary=not args.trace_color)
            mode = "colour" if args.trace_color else "binary"
            print(f"       vector-traced SVG (x{args.trace_scale} {mode}) -> {vec_path.name}")
        except Exception as e:  # noqa: BLE001
            print(f"       (skipped vector SVG: {e})", file=sys.stderr)

    if args.svg in ("raster", "both"):
        emb_path = out_dir / f"{path.stem}_raster.svg"
        raster_embed_svg(final, emb_path)
        print(f"       raster-embedded SVG -> {emb_path.name}")


def iter_inputs(p: Path):
    if p.is_file():
        yield p
    else:
        for f in sorted(p.iterdir()):
            if f.suffix.lower() == ".svg" or f.suffix.lower() in RASTER_EXTS:
                yield f


def main() -> int:
    ap = argparse.ArgumentParser(description="Remove watermarks from SVG reports and raster scans; enhance text quality.")
    ap.add_argument("--input", required=True, help="File or folder")
    ap.add_argument("--output", required=True, help="Output folder")
    # raster whitening
    ap.add_argument("--light", type=int, default=188, help="Whiten pixels with min-channel >= this (raster)")
    ap.add_argument("--red", type=int, default=10, help="Redness threshold for tinted watermark (raster)")
    ap.add_argument("--pink-min", type=int, default=158, help="Min-channel floor for tinted pixels (raster)")
    # enhancement
    ap.add_argument("--scale", type=int, default=1, choices=[1, 2, 4], help="Upscale factor for rasters / SVG render")
    ap.add_argument("--no-sharpen", action="store_true", help="Disable unsharp masking")
    # svg export from raster
    ap.add_argument("--svg", choices=["none", "vector", "raster", "both"], default="none",
                    help="For raster inputs: also export SVG (vector trace / raster-embed / both)")
    ap.add_argument("--trace-scale", type=int, default=3,
                    help="Upscale factor before vector tracing (more = crisper vector text; default 3)")
    ap.add_argument("--trace-color", action="store_true",
                    help="Trace in colour (keeps coloured ink but heavier / can exhaust memory on dense pages). Default is fast binary black-on-white.")
    # svg input handling
    ap.add_argument("--tile-min-repeat", type=int, default=3,
                    help="An <image> whose href repeats >= this many times is treated as a watermark tile")
    ap.add_argument("--rasterize-svg", action="store_true", help="Also render cleaned SVGs to PNG")
    ap.add_argument("--dpi", type=int, default=None, help="DPI for SVG rasterization (optional)")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.output)
    if not in_path.exists():
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)

    files = list(iter_inputs(in_path))
    if not files:
        print(f"error: no images/SVGs found in {in_path}", file=sys.stderr)
        return 1

    for f in files:
        if f.suffix.lower() == ".svg":
            process_svg(f, out_dir, args)
        else:
            process_raster(f, out_dir, args)

    print(f"\nDone. {len(files)} file(s) -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Repaints the text baked into the 3D model textures (monitor/PC/keyboard
labels and the credits sheet) using the values in tools/textures.json.

Usage:
    pip install pillow numpy
    python3 tools/customize-textures.py

It always starts from the untouched copies in tools/original-textures/, so you
can edit tools/textures.json and re-run as often as you like.
"""
import json
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ORIG = ROOT / "tools" / "original-textures"
OUT_COMPUTER = ROOT / "static" / "models" / "Computer" / "baked_computer.jpg"
OUT_DECOR = ROOT / "static" / "models" / "Decor" / "baked_decor_modified.jpg"
CFG = json.loads((ROOT / "tools" / "textures.json").read_text())

FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu/",
    "/usr/share/fonts/truetype/liberation/",
    "/Library/Fonts/",
    "/System/Library/Fonts/Supplemental/",
    "C:/Windows/Fonts/",
]


def font(names, size):
    for d in FONT_DIRS:
        for n in names:
            p = Path(d) / n
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size=size)


BRAND_FONT = ["DejaVuSans-BoldOblique.ttf", "LiberationSans-BoldItalic.ttf", "Arial Bold Italic.ttf", "arialbi.ttf"]
SMALL_FONT = ["LiberationSans-Italic.ttf", "DejaVuSans-Oblique.ttf", "Arial Italic.ttf", "ariali.ttf"]
MONO_BOLD = ["LiberationMono-Bold.ttf", "DejaVuSansMono-Bold.ttf", "Courier New Bold.ttf", "courbd.ttf"]


def inpaint(arr, mask, iters=250):
    """Fill masked pixels by repeatedly averaging their neighbours."""
    out = arr.copy()
    out[mask] = np.median(arr[~mask].reshape(-1, 3), axis=0) if (~mask).any() else 128
    for _ in range(iters):
        p = np.pad(out, ((1, 1), (1, 1), (0, 0)), mode="edge")
        avg = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 4.0
        out[mask] = avg[mask]
    return out


def clear_text(img, box, thresh=18, grow=2):
    """Erase everything in `box` that differs from the local background."""
    x0, y0, x1, y1 = [int(v) for v in box]
    arr = np.asarray(img.crop((x0, y0, x1, y1))).astype(np.float32)
    lum = arr.mean(axis=2)
    bg = np.median(lum)
    mask_img = Image.fromarray((np.abs(lum - bg) > thresh).astype(np.uint8) * 255)
    if grow:
        mask_img = mask_img.filter(ImageFilter.MaxFilter(grow * 2 + 1))
    mask = np.asarray(mask_img) > 0
    filled = inpaint(arr, mask)
    img.paste(Image.fromarray(np.clip(filled, 0, 255).astype(np.uint8)), (x0, y0))


def draw_lines(img, box, lines, align="left", valign="top", gap=0.25, scale=4):
    """
    Draw lines of text inside `box`, shrinking until everything fits.
    lines = [(text, font_names, relative_size, gray_value), ...]
    """
    x0, y0, x1, y1 = [int(v) for v in box]
    bw, bh = (x1 - x0) * scale, (y1 - y0) * scale
    size = bh
    while size > 3:
        fonts = [font(f, max(2, int(size * rel))) for _, f, rel, _ in lines]
        widths = [fo.getlength(t) for (t, _, _, _), fo in zip(lines, fonts)]
        heights = [fo.getbbox("Hgy")[3] for fo in fonts]
        total = sum(heights) + gap * size * (len(lines) - 1)
        if max(widths) <= bw and total <= bh:
            break
        size -= 1
    layer = Image.new("L", (bw, bh), 0)
    d = ImageDraw.Draw(layer)
    y = 0 if valign == "top" else (bh - total) / 2
    shade = Image.new("L", (bw, bh), 0)
    for (t, _, _, gray), fo, w, h in zip(lines, fonts, widths, heights):
        x = 0 if align == "left" else (bw - w) / 2 if align == "center" else bw - w
        ld = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(ld).text((x, y), t, font=fo, fill=255)
        shade = Image.composite(Image.new("L", (bw, bh), gray), shade, ld)
        d.text((x, y), t, font=fo, fill=255)
        y += h + gap * size
    alpha = layer.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    color = shade.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    region = img.crop((x0, y0, x1, y1))
    colored = Image.merge("RGB", (color, color, color))
    img.paste(Image.composite(colored, region, alpha), (x0, y0))


def on_rotated(img, box, angle, fn):
    """Rotate the area under `box`, run fn(upright_image), rotate back, paste."""
    x0, y0, x1, y1 = box
    crop = img.crop(box).rotate(angle, expand=True)
    fn(crop)
    img.paste(crop.rotate(-angle, expand=True), (x0, y0))


def rel(box, w, h):
    return (box[0] * w, box[1] * h, box[2] * w, box[3] * h)


def plaque(p):
    """The dark information plate. `p` is an upright PIL image."""
    w, h = p.size
    c = CFG
    for b in [(0.05, 0.07, 0.85, 0.27), (0.05, 0.31, 0.93, 0.52), (0.05, 0.58, 0.43, 0.80), (0.05, 0.86, 0.42, 0.95), (0.56, 0.52, 0.94, 0.74)]:
        clear_text(p, rel(b, w, h), thresh=14, grow=2)
    draw_lines(p, rel((0.06, 0.08, 0.84, 0.26), w, h), [(c["product"], BRAND_FONT, 1.0, 235), (c["company"], BRAND_FONT, 0.55, 205)])
    wrapped = textwrap.wrap(c["description"], 46)[:4]
    draw_lines(p, rel((0.06, 0.32, 0.92, 0.51), w, h), [(t, SMALL_FONT, 1.0, 175) for t in wrapped], gap=0.2)
    draw_lines(p, rel((0.06, 0.59, 0.42, 0.79), w, h), [("Model No.  " + c["model"], SMALL_FONT, 1.0, 160), ("AC Input  " + c["power"], SMALL_FONT, 1.0, 160), (c["power_note"], SMALL_FONT, 0.7, 140)], gap=0.3)
    draw_lines(p, rel((0.06, 0.87, 0.41, 0.94), w, h), [(c["assembled"], SMALL_FONT, 1.0, 130)])
    draw_lines(p, rel((0.57, 0.54, 0.93, 0.73), w, h), [(c["brand"], BRAND_FONT, 1.0, 200), (c["company"], BRAND_FONT, 0.55, 180)], gap=0.1)


def logo(img, box, angle=0, thresh=18):
    c = CFG

    def fn(u):
        w, h = u.size
        clear_text(u, (0, 0, w, h), thresh=thresh, grow=2)
        draw_lines(u, (0, 0, w, h), [(c["brand"], BRAND_FONT, 1.0, 55), (c["company"], BRAND_FONT, 0.5, 70)], gap=0.1)

    on_rotated(img, box, angle, fn)


def computer():
    img = Image.open(ORIG / "baked_computer.jpg").convert("RGB")
    # monitor back plate (rotated 90 degrees in the texture) and PC plate
    on_rotated(img, (1695, 534, 1835, 748), -90, plaque)
    plaque_c = img.crop((2774, 3294, 2993, 3439))
    plaque(plaque_c)
    img.paste(plaque_c, (2774, 3294))
    logo(img, (1335, 2650, 1570, 2735), angle=180)  # monitor bezel logo (upside down)
    logo(img, (2312, 1938, 2398, 1972), thresh=14)  # keyboard logo
    img.save(OUT_COMPUTER, quality=95, subsampling=0)


def credits():
    img = Image.open(ORIG / "baked_decor_modified.jpg").convert("RGB")
    c = CFG
    clear_text(img, (380, 260, 1640, 2700), thresh=8, grow=7)
    gray = 112
    left, right, width = 400, 1600, 1200
    f = lambda s: font(MONO_BOLD, s)
    # work out how tall everything is: squeeze the font if too long, spread gaps if short
    rows = sum(len(s["rows"]) for s in c["credits"])
    need = 2 * 58 + 140 + len(c["credits"]) * (85 + 150) + rows * 58 + 140 + len(c["credits_footer"]) * 58
    k = min(1.0, 2400 / need)
    spread = min(1.7, max(1.0, 2300 / need))
    line, head_gap, sec_gap = 58 * k, 85 * k, 150 * k * spread
    size = int(50 * k)
    d = ImageDraw.Draw(img)

    def centered(text, y):
        d.text(((left + right) / 2, y), text, font=f(size), fill=(gray,) * 3, anchor="mt")

    y = 290
    centered(c["credits_title"], y)
    y += line * 1.3
    centered(c["credits_subtitle"], y)
    y += 140 * k * spread
    for section in c["credits"]:
        centered(section["heading"], y)
        y += head_gap
        for l, r in section["rows"]:
            d.text((left, y), l, font=f(size), fill=(gray,) * 3, anchor="lt")
            d.text((right, y), r, font=f(size), fill=(gray,) * 3, anchor="rt")
            y += line
        y += sec_gap - head_gap + 20 * k
    y += 20 * spread
    for t in c["credits_footer"]:
        centered(t, y)
        y += line
    img.save(OUT_DECOR, quality=95, subsampling=0)


if __name__ == "__main__":
    computer()
    credits()
    print("Wrote", OUT_COMPUTER.relative_to(ROOT), "and", OUT_DECOR.relative_to(ROOT))

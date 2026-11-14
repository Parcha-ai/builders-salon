"""Precompute the glyph-field targets (pure code, no generative imagery).

Writes assets/field.js with:
  logos     coverage masks of the official Parcha SVG and Piloto 151 PNG (0/1 per cell)
  portraits mean luminance per cell of each real headshot (0-9), sized to the photo box

The film draws each cell as one code glyph, so the logos and portraits are rebuilt from
characters; the official artwork and the unaltered photos land on top of them."""

import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "assets/img"
DATA = json.loads((ROOT / "assets/data.js").read_text().split("=", 1)[1].rstrip().rstrip(";"))
BOX, CELL = 560, 8


def grid(arr, cols, rows):
    """area-average a float image onto cols x rows"""
    im = Image.fromarray((arr * 255).astype(np.uint8))
    return np.asarray(im.resize((cols, rows), Image.Resampling.BOX), dtype=np.float32) / 255


def parcha_raster():
    with tempfile.TemporaryDirectory() as d:
        page = Path(d) / "p.html"
        out = Path(d) / "p.png"
        page.write_text(f'<html><body style="margin:0;background:#fff"><img src="file://{IMG}/parcha-official-purple.svg" '
                        'style="width:1332px;height:300px;display:block"></body></html>')
        subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                        f"--screenshot={out}", "--window-size=1332,300", f"file://{page}"], check=True, capture_output=True, timeout=90)
        rgb = np.asarray(Image.open(out).convert("RGB"), dtype=np.float32) / 255
    # purple ink on white: the green channel drops from 1.0 to ~0.37 on the mark
    return np.clip((1 - rgb[..., 1]) / 0.6, 0, 1)


def mask(cov, cols, thr=0.38):
    """m: cells drawn as glyphs; a: every cell with any ink (the photo-tile resolve covers these)"""
    rows = max(1, round(cols * cov.shape[0] / cov.shape[1]))
    g = grid(cov, cols, rows)
    return {"cols": cols, "rows": rows,
            "m": "".join("1" if v > thr else "0" for v in g.ravel()),
            "a": "".join("1" if v > 0.015 else "0" for v in g.ravel())}


def main():
    # about 4 px cells at the size the film draws them (Parcha ~560 px wide, the Piloto PNG ~545 px wide)
    logos = {
        "parcha": mask(parcha_raster(), 140),
        "piloto": mask(np.asarray(Image.open(IMG / "piloto-151-official-white.png").convert("LA"), dtype=np.float32)[..., 1] / 255, 136, 0.3),
    }

    portraits = {}
    for s in DATA["speakers"]:
        iw, ih = s["headshot_dimensions"]["width"], s["headshot_dimensions"]["height"]
        sc = min(BOX / iw, BOX / ih)
        w, h = round(iw * sc), round(ih * sc)
        cols, rows = round(w / CELL), round(h / CELL)
        im = Image.open(ROOT / s["src"]).convert("L")
        big = im.resize((cols * 4, rows * 4), Image.Resampling.LANCZOS)
        # tone: half histogram-equalised (local detail), half percentile-stretched (keeps light grounds light)
        eq = np.asarray(ImageOps.equalize(big).filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255
        raw = np.asarray(big.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255
        lo, hi = np.percentile(raw, 2), np.percentile(raw, 98)
        tone = grid(0.5 * eq + 0.5 * np.clip((raw - lo) / max(1e-3, hi - lo), 0, 1), cols, rows)
        dark = (1 - tone) ** 1.25
        # contour cells (strong gradient on a softer copy) are drawn in vermilion
        soft = np.asarray(big.filter(ImageFilter.GaussianBlur(2.2)), dtype=np.float32) / 255
        gy, gx = np.gradient(soft)
        e = grid(np.clip(np.hypot(gx, gy) / max(1e-4, np.percentile(np.hypot(gx, gy), 99)), 0, 1), cols, rows)
        edge = e > np.percentile(e, 90)
        portraits[s["id"]] = {
            "cols": cols, "rows": rows, "w": w, "h": h,
            "v": "".join(str(min(9, int(v * 10))) for v in dark.ravel()),
            "e": "".join("1" if x else "0" for x in edge.ravel()),
        }

    out = ROOT / "assets/field.js"
    out.write_text("window.BS_FIELD = " + json.dumps({"logos": logos, "portraits": portraits}, separators=(",", ":")) + ";\n")
    print("wrote", out, {k: v["m"].count("1") for k, v in logos.items()}, {k: (v["cols"], v["rows"]) for k, v in portraits.items()})


if __name__ == "__main__":
    main()

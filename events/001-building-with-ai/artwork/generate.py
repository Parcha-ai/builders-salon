"""A parametric, occluded wireframe B. All geometry and exports are code-generated."""

import argparse
import ast
import json
import textwrap
from functools import cache
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, Polygon

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENT_ROOT = Path(__file__).resolve().parents[1]
FONT = REPO_ROOT / "brand/fonts/JetBrainsMono-Medium.ttf"
BOLD = REPO_ROOT / "brand/fonts/JetBrainsMono-SemiBold.ttf"
PAPER, INK, RED = "#F4F0E7", "#20221F", "#D74327"
F = TTFont(FONT)
FB = TTFont(BOLD)


class Art:
    def __init__(self, w, h, bg=None):
        self.w, self.h, self.parts = w, h, []
        self.im = Image.new("RGBA", (w * 3, h * 3), bg or (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.im)
        if bg:
            self.rect(0, 0, w, h, bg)

    def rect(self, x, y, w, h, color):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}"/>'
        )
        self.draw.rectangle(
            (
                round(x * 3),
                round(y * 3),
                round((x + w) * 3) - 1,
                round((y + h) * 3) - 1,
            ),
            fill=color,
        )

    def line(self, pts, color=RED, width=1.5):
        self.parts.append(
            f'<polyline points="{" ".join(f"{x:.3f},{y:.3f}" for x,y in pts)}" fill="none" stroke="{color}" stroke-width="{width:.3f}" stroke-linejoin="miter" stroke-linecap="square"/>'
        )
        self.draw.line(
            [(round(x * 3), round(y * 3)) for x, y in pts],
            fill=color,
            width=max(1, round(width * 3)),
        )

    def polygon(self, contours, color):
        d = " ".join(
            "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in pts) + "Z"
            for pts in contours
        )
        self.parts.append(f'<path d="{d}" fill="{color}" fill-rule="evenodd"/>')
        mask = Image.new("L", self.im.size)
        draw = ImageDraw.Draw(mask)
        for i, pts in enumerate(contours):
            draw.polygon(
                [(round(x * 3), round(y * 3)) for x, y in pts],
                fill=255 if i == 0 else 0,
            )
        self.im.paste(color, (0, 0), mask)

    def text(self, value, x, y, size, color=INK, bold=False):
        font = FB if bold else F
        glyphs = font.getGlyphSet()
        cmap = font.getBestCmap()
        chunks, cursor = [], 0
        for char in value:
            name = cmap[ord(char)]
            p = SVGPathPen(glyphs)
            glyphs[name].draw(p)
            chunks.append(
                f'<path transform="translate({cursor},0)" d="{p.getCommands()}"/>'
            )
            cursor += font["hmtx"].metrics[name][0]
        scale = size / font["head"].unitsPerEm
        self.parts.append(
            f'<g aria-label="{escape(value)}" fill="{color}" transform="translate({x},{y}) scale({scale},-{scale})">{"".join(chunks)}</g>'
        )
        self.draw.text(
            (round(x * 3), round(y * 3)),
            value,
            font=ImageFont.truetype(str(BOLD if bold else FONT), round(size * 3)),
            fill=color,
            anchor="ls",
        )
        return cursor * scale

    def save(self, name, title):
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img"><title>{escape(title)}</title>{"".join(self.parts)}</svg>'
        ET.fromstring(svg)
        name = Path(name)
        name.parent.mkdir(parents=True, exist_ok=True)
        name.with_suffix(".svg").write_text(svg, encoding="utf-8")
        self.im.resize((self.w * 2, self.h * 2), Image.Resampling.LANCZOS).save(
            name.with_suffix(".png")
        )


# A broad, hand-constructed B on a 200-unit cap height. The lower bowl is
# deliberately larger. Forty-five-degree chamfers share one consistent grid.
OUTER = [
    (0, 0),
    (108, 0),
    (138, 30),
    (138, 66),
    (116, 88),
    (146, 118),
    (146, 170),
    (116, 200),
    (0, 200),
]
UPPER = [(32, 30), (94, 30), (106, 42), (106, 66), (94, 78), (32, 78)]
LOWER = [(32, 106), (102, 106), (114, 118), (114, 156), (102, 168), (32, 168)]
CONTOURS = [OUTER, UPPER, LOWER]
DX, DY = 32, -32


@cache
def visible_edges(steps):
    """Ray-test every edge against the extruded letter; split at occlusions."""
    shape = Polygon(OUTER, [UPPER, LOWER])

    def project(p):
        u, v, t = p
        return u + DX * t, v + DY * t

    def visible(p):
        if p[2] < 1e-5:
            return True
        q = project(p)
        near = (p[0] + DX * 1e-5, p[1] + DY * 1e-5)
        return shape.intersection(LineString([q, near])).length < 0.001

    edges = []

    def clipped(p, q):
        n = max(
            4,
            int(((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 / 0.8),
            int(abs(p[2] - q[2]) * 70),
        )

        def interp(s):
            return tuple(a + (b - a) * s for a, b in zip(p, q))

        prev_s = 0
        prev = visible(p)
        run = [project(p)] if prev else []
        for i in range(1, n + 1):
            s = i / n
            point = interp(s)
            state = visible(point)
            if state != prev:
                lo, hi = prev_s, s
                for _ in range(12):
                    mid = (lo + hi) / 2
                    if visible(interp(mid)) == prev:
                        lo = mid
                    else:
                        hi = mid
                cross = project(interp((lo + hi) / 2))
                if prev:
                    run.append(cross)
                    if len(run) > 1:
                        edges.append(run)
                    run = []
                else:
                    run = [cross]
            if state:
                run.append(project(point))
            prev_s, prev = s, state
        if len(run) > 1:
            edges.append(run)

    for i in range(steps, 0, -1):
        t = i / steps
        for poly in CONTOURS:
            for p, q in zip(poly, poly[1:] + poly[:1]):
                clipped((*p, t), (*q, t))
    for poly in CONTOURS:
        for p in poly:
            clipped((*p, 0), (*p, 1))
    return [[pts[0], pts[-1]] for pts in edges]


def bmark(a, x, y, height, color=RED, detail=None):
    """Extrude cross sections and ray-test the edges for visibility."""
    k = height / (200 - DY)

    def project(poly, t=0):
        return [(x + (u + DX * t) * k, y + (v - DY + DY * t) * k) for u, v in poly]

    steps = detail if detail is not None else (9 if height >= 180 else 4)
    for pts in visible_edges(steps):
        a.line(
            [(x + u * k, y + (v - DY) * k) for u, v in pts], color, max(0.55, k * 0.65)
        )
    for pts in CONTOURS:
        a.line(project(pts + [pts[0]]), color, max(1.0, k * 1.6))


def build_brand(output_dir, byline):
    """Export the series identity, including transparent and reverse variants."""
    for name, background, foreground, accent in [
        ("builders-salon-logo", PAPER, INK, RED),
        ("builders-salon-transparent", None, INK, RED),
        ("builders-salon-reverse", INK, PAPER, RED),
        ("builders-salon-white", None, PAPER, PAPER),
    ]:
        a = Art(1440, 580, background)
        bmark(a, 100, 147, 220, accent)
        a.text("The Builders’", 340, 231, 112, foreground, bold=True)
        a.text("Salon", 340, 355, 112, foreground, bold=True)
        a.text(byline, 344, 430, 25, foreground)
        a.save(
            output_dir / name, f"The Builders’ Salon — refined wireframe B — {byline}"
        )

    for name, background, color in [
        ("b-mark", None, RED),
        ("b-mark-paper", PAPER, RED),
        ("b-mark-white", None, PAPER),
    ]:
        a = Art(680, 800, background)
        bmark(a, 92, 88, 620, color, detail=13)
        a.save(output_dir / name, "The Builders’ Salon — parametric wireframe B")


def build_flyer(output_dir, event, byline):
    """Build Event 001 with its approved, frozen source-code background."""
    a = Art(1200, 1200, PAPER)
    source = (Path(__file__).parent / "background-source.py.txt").read_text(
        encoding="utf-8"
    )
    formatted = ast.unparse(ast.parse(source))
    code_lines = []
    for line in formatted.splitlines():
        code_lines.extend(
            textwrap.wrap(
                line,
                width=73,
                subsequent_indent="        ",
                break_long_words=True,
                break_on_hyphens=False,
            )
            or [""]
        )
    rows = 76
    for i, line in enumerate(code_lines[: rows * 2]):
        column, row = divmod(i, rows)
        x, y = 12 + 600 * column, 10 + row * 16
        a.text(f"{i + 1:03}", x, y, 9, "#DEDAD1")
        if line.strip():
            a.text(line, x + 36, y, 12, "#D6D2C9")

    a.text("A CONVERSATION SERIES", 64, 57, 17)
    a.text(event["location"].upper(), 1000, 57, 17)
    a.line([(64, 81), (1136, 81)], INK, 1)
    bmark(a, 66, 126, 102)
    a.text("The Builders’", 176, 166, 49, bold=True)
    a.text("Salon", 176, 222, 49, bold=True)
    a.text("SESSION", 1014, 148, 17)
    a.text(f"{event['number']:03}", 1022, 214, 61, RED)
    a.text("Building", 56, 426, 156, bold=True)
    with_width = a.text("with", 63, 580, 156, bold=True)
    a.text("AI", 63 + with_width + 156 * 0.30, 580, 156, bold=True)

    profile = [
        (125, 972),
        (125, 773),
        (320, 773),
        (320, 863),
        (515, 863),
        (515, 684),
        (710, 684),
        (710, 972),
    ]
    for layer in range(19):
        a.line([(x + layer * 16, y - layer * 5) for x, y in profile])
    for x, y in profile:
        a.line([(x, y), (x + 18 * 16, y - 18 * 5)])
    a.line([(64, 1050), (1136, 1050)], INK, 1)
    a.text(byline, 64, 1118, 28)
    a.text(f"[ {event['number']:02} ]", 1028, 1118, 24, RED)
    a.save(output_dir / "flyer", f"{event['title']} — {event['series']} — {byline}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT,
        help="Output root; mirrors the repository layout (default: repository root).",
    )
    args = parser.parse_args()
    event = json.loads((EVENT_ROOT / "event.json").read_text(encoding="utf-8"))
    byline = "by " + " and ".join(event["hosts"])
    output = args.output_dir.resolve()
    build_brand(output / "brand/assets", byline)
    build_flyer(output / "events" / EVENT_ROOT.name / "assets", event, byline)
    print(f"Built 7 brand assets and the Event 001 flyer as SVG + PNG in {output}")


if __name__ == "__main__":
    main()

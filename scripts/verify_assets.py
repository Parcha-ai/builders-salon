"""Rebuild in isolation and validate the checked-in public artwork."""

import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EVENT = Path("events/001-building-with-ai")
SVG_NS = "{http://www.w3.org/2000/svg}"
ASSETS = {
    **{
        Path("brand/assets") / name: (1440, 580)
        for name in (
            "builders-salon-logo",
            "builders-salon-transparent",
            "builders-salon-reverse",
            "builders-salon-white",
        )
    },
    **{
        Path("brand/assets") / name: (680, 800)
        for name in ("b-mark", "b-mark-paper", "b-mark-white")
    },
    EVENT / "assets/flyer": (1200, 1200),
}
TRANSPARENT = {
    "builders-salon-transparent",
    "builders-salon-white",
    "b-mark",
    "b-mark-white",
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def validate_asset(base, stem, size):
    svg_path = (base / stem).with_suffix(".svg")
    png_path = (base / stem).with_suffix(".png")
    svg = ET.parse(svg_path).getroot()
    require(svg.tag == SVG_NS + "svg", f"Not SVG: {svg_path}")
    require(
        svg.get("viewBox") == f"0 0 {size[0]} {size[1]}", f"Wrong viewBox: {svg_path}"
    )
    require(svg.find(SVG_NS + "title") is not None, f"Missing title: {svg_path}")
    require(
        any(svg.find(".//" + SVG_NS + tag) is not None for tag in ("path", "polyline")),
        f"No vector geometry: {svg_path}",
    )
    for element in svg.iter():
        require(
            element.tag not in {SVG_NS + "text", SVG_NS + "image"},
            f"SVG must use portable paths: {svg_path}",
        )
        require(
            not any(key.endswith("href") for key in element.attrib),
            f"Linked resource in SVG: {svg_path}",
        )

    with Image.open(png_path) as image:
        image.load()
        require(image.format == "PNG", f"Not PNG: {png_path}")
        require(image.size == (size[0] * 2, size[1] * 2), f"Wrong PNG size: {png_path}")
        require(image.mode == "RGBA", f"Missing alpha channel: {png_path}")
        alpha = image.getchannel("A").getextrema()
        if stem.name in TRANSPARENT:
            require(alpha == (0, 255), f"Transparency is missing: {png_path}")
        else:
            require(alpha == (255, 255), f"Unexpected transparency: {png_path}")

    if stem.name == "flyer" or stem.name.startswith("builders-salon"):
        event = json.loads((ROOT / EVENT / "event.json").read_text(encoding="utf-8"))
        expected = "by " + " and ".join(event["hosts"])
        labels = {node.get("aria-label") for node in svg.iter()}
        require(expected in labels, f"Missing host attribution: {svg_path}")


def main():
    with TemporaryDirectory(prefix="builders-salon-") as directory:
        generated = Path(directory)
        subprocess.run(
            [
                sys.executable,
                str(ROOT / EVENT / "artwork/generate.py"),
                "--output-dir",
                str(generated),
            ],
            cwd=ROOT,
            check=True,
        )
        expected_paths = {
            stem.with_suffix(extension)
            for stem in ASSETS
            for extension in (".svg", ".png")
        }
        actual_paths = {
            p.relative_to(generated) for p in generated.rglob("*") if p.is_file()
        }
        require(actual_paths == expected_paths, "Build output manifest changed")
        for stem, size in ASSETS.items():
            validate_asset(ROOT, stem, size)
            validate_asset(generated, stem, size)
            svg_path = stem.with_suffix(".svg")
            # SVGs are deterministic across the supported Python environment.
            # PNG encoders / FreeType can differ between operating systems;
            # validate both raster copies without assuming byte-identical pixels.
            require(
                (ROOT / svg_path).read_bytes() == (generated / svg_path).read_bytes(),
                f"Stale checked-in SVG: {svg_path}. Run make build.",
            )
    print(
        "Verified 16 exports: reproducible SVGs, PNG dimensions, transparency, and attribution."
    )


if __name__ == "__main__":
    main()

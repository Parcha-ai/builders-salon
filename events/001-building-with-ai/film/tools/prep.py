"""Build assets/data.js from the event's own source. Every number here is read from
../artwork/generate.py, ../artwork/background-source.py.txt or speakers.json."""

import ast
import hashlib
import json
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTWORK = ROOT.parent / "artwork"

# ast.unparse output changes between Python versions (3.12 re-quotes nested f-strings). The rows are
# the film's code ground and its scramble-glyph pool, so pin them: this is the Python 3.11 formatting.
ROWS_SHA256 = "ea4fd65115ec30194ad4d06a17132bca6fe9ea49ce852508507334c15ee12841"

WRAP = 62  # characters per code row at 15 px JetBrains Mono in a 640 px column
NBSP = " "


def code_rows():
    formatted = ast.unparse(ast.parse((ARTWORK / "background-source.py.txt").read_text("utf-8")))
    # Keep coordinate tuples on one row so each "(x, y)" has one screen position.
    formatted = re.sub(r"\((-?\d+), (-?\d+)\)", lambda m: f"({m[1]},{NBSP}{m[2]})", formatted)
    rows = []
    for line in formatted.splitlines():
        rows.extend(
            textwrap.wrap(line, width=WRAP, subsequent_indent="        ",
                          break_long_words=True, break_on_hyphens=False) or [""]
        )
    return [r.replace(NBSP, " ") for r in rows]


def tuple_spans(rows, name):
    """Row and column of each (x, y) literal in the NAME = [...] assignment."""
    start = next(i for i, r in enumerate(rows) if r.startswith(f"{name} = ["))
    spans, i = [], start
    while True:
        for m in re.finditer(r"\((-?\d+), (-?\d+)\)", rows[i]):
            spans.append({"row": i, "col": m.start(), "len": m.end() - m.start(),
                          "pt": [int(m[1]), int(m[2])]})
        if rows[i].rstrip().endswith("]"):
            break
        i += 1
    return {"row": start, "rows": i - start + 1, "spans": spans}


def generator_constants():
    tree = ast.parse((ARTWORK / "generate.py").read_text("utf-8"))
    consts = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            n = node.targets[0].id
            if n in ("OUTER", "UPPER", "LOWER"):
                consts[n] = ast.literal_eval(node.value)
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Tuple):
            names = [t.id for t in node.targets[0].elts]
            if names == ["DX", "DY"]:
                consts["DX"], consts["DY"] = ast.literal_eval(node.value)
            if names == ["PAPER", "INK", "RED"]:
                consts["PAPER"], consts["INK"], consts["RED"] = ast.literal_eval(node.value)
    flyer = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_flyer")
    for node in flyer.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "profile":
            consts["PROFILE"] = ast.literal_eval(node.value)
    return consts


def main():
    rows = code_rows()
    digest = hashlib.sha256("\n".join(rows).encode()).hexdigest()
    if digest != ROWS_SHA256 and "--accept-new-rows" not in sys.argv:
        sys.exit(f"code rows formatted differently on Python {sys.version.split()[0]} (sha256 {digest[:12]}); "
                 "run with python3.11 to reproduce the film, or pass --accept-new-rows to change it")
    consts = generator_constants()
    # the film highlights these tuples in the code ground, so they must match the generator's
    for name in ("OUTER", "UPPER", "LOWER"):
        found = [s["pt"] for s in tuple_spans(rows, name)["spans"]]
        if found != [list(p) for p in consts[name]]:
            sys.exit(f"{name} in the code ground does not match generate.py: {found}")
    speakers = json.loads((ROOT / "speakers.json").read_text("utf-8"))["speakers"]
    data = {
        "code": rows,
        "codeSpans": {n: tuple_spans(rows, n) for n in ("OUTER", "UPPER", "LOWER")},
        "geo": consts,
        "speakers": [
            {k: s[k] for k in ("id", "name", "title", "organization", "headshot_dimensions")}
            | {"src": "assets/img/" + Path(s["headshot"]).name}
            for s in sorted(speakers, key=lambda s: s["order"])
        ],
    }
    out = ROOT / "assets/data.js"
    out.write_text("window.BS_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n", "utf-8")
    print(f"{len(rows)} code rows; OUTER at row {data['codeSpans']['OUTER']['row']}; wrote {out}")


if __name__ == "__main__":
    main()

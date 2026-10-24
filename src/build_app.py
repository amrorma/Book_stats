"""
build_app.py

Build the single-file browser app "متصفح القرآن.html" from
    1. the curated workbook  (القرآن الكريم.xlsx)
    2. the page template     (src/template.html, placeholders __DATA__ and __FONT__)
    3. the Uthmani font      (fonts/UthmanicHafs.woff2, KFGQPC Uthmanic Script HAFS)

The result has no external dependencies apart from two Google Fonts
(Amiri, IBM Plex Sans Arabic) and can be opened offline, shared as a file,
or published as a web page.

Usage (from the repository root)
    python3 src/build_app.py
    python3 src/build_app.py --xlsx "القرآن الكريم.xlsx" --out "متصفح القرآن.html"
"""

# ---------------------------------------------------------------------------
# Required libraries
# ---------------------------------------------------------------------------
import argparse   # command-line options
import base64     # embedding the font as a data URI
from pathlib import Path  # path handling

from build_data import build_payload, payload_to_json  # workbook -> JSON payload

# ---------------------------------------------------------------------------
# Input / output paths and parameters
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_XLSX = REPO_ROOT / "القرآن الكريم.xlsx"
DEFAULT_TEMPLATE = REPO_ROOT / "src" / "template.html"
DEFAULT_FONT = REPO_ROOT / "fonts" / "UthmanicHafs.woff2"
DEFAULT_OUT = REPO_ROOT / "متصفح القرآن.html"

# Standalone document head: the explicit UTF-8 charset keeps the Arabic text
# intact when the file is opened from disk or shared through messengers.
STANDALONE_HEAD = (
    '<!doctype html>\n<html lang="ar" dir="rtl">\n<head>\n'
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
)


# ---------------------------------------------------------------------------
# Build steps
# ---------------------------------------------------------------------------
def build(xlsx, template, font, out):
    """Assemble the app and write it to `out`."""
    # --- 1. workbook -> compact JSON payload --------------------------------
    payload = build_payload(xlsx)
    data_json = payload_to_json(payload)
    assert "</script" not in data_json, "payload would close the <script> element"

    # --- 2. font -> base64 for the @font-face data URI -----------------------
    font_b64 = base64.b64encode(Path(font).read_bytes()).decode()

    # --- 3. fill the template -------------------------------------------------
    page = Path(template).read_text(encoding="utf-8")
    assert page.count("__DATA__") == 1 and page.count("__FONT__") == 1, "template placeholders missing"
    page = page.replace("__FONT__", font_b64).replace("__DATA__", data_json)

    # --- 4. export ------------------------------------------------------------
    Path(out).write_text(STANDALONE_HEAD + page, encoding="utf-8")
    print(f"{payload['n']} words, {len(payload['forms'])} distinct forms, "
          f"{len(payload['roots'])} roots -> {out} ({Path(out).stat().st_size / 1e6:.2f} MB)")


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build متصفح القرآن.html from the curated workbook.")
    parser.add_argument("--xlsx", default=DEFAULT_XLSX, help="curated word-level workbook")
    parser.add_argument("--template", default=DEFAULT_TEMPLATE, help="HTML template with __DATA__ and __FONT__")
    parser.add_argument("--font", default=DEFAULT_FONT, help="Uthmani woff2 font")
    parser.add_argument("--out", default=DEFAULT_OUT, help="output HTML file")
    args = parser.parse_args()
    build(args.xlsx, args.template, args.font, args.out)

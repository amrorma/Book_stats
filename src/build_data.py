"""
build_data.py

Read the curated word-level Quran workbook (sheet "الكلمات") and convert it
into the compact JSON payload that is embedded in the browser app.

Every column is located by its header name, so the column order in the
workbook may change. Word forms and roots are taken exactly as written in
the table, diacritics included; nothing is normalised here.

Payload fields
    forms       distinct words (column الكلمة), in order of first appearance
    roots       distinct roots (column الجذر), in order of first appearance
    tokForm     base64 Uint16 array: form index of every word position
    tokRoot     base64 Uint16 array: root index of every word position
    verseStart  index of the first word of every verse (6236 entries)
    surahs      [name, "m" (Meccan) | "d" (Medinan), index of first verse]
    pageStart   index of the first word of every mushaf page (604 entries)
    juzStart    index of the first word of every juz (30 entries)
    n           number of word positions
    uVerses     Uthmani text of every verse
    uA, uB      base64 Uint16 arrays: start/end of the red (current) word
                inside its Uthmani verse text

Usage
    python3 src/build_data.py "القرآن الكريم.xlsx" build/data.json
"""

# ---------------------------------------------------------------------------
# Required libraries
# ---------------------------------------------------------------------------
import array      # compact unsigned 16-bit arrays for the per-word indices
import base64     # base64 encoding of those arrays for embedding in HTML
import json       # serialisation of the payload
import sys        # command-line arguments
from pathlib import Path  # path handling

import openpyxl   # reading the .xlsx workbook, including rich text

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
SHEET_NAME = "الكلمات"                       # sheet with one row per word
UTHMANI_VERSE_PREFIX = "نص الآية بالرسم العثماني"  # header prefix of the Uthmani verse column
RED_RGB = "FFFF0000"                          # font colour marking the current word
EXPECTED = {"surahs": 114, "verses": 6236, "pages": 604, "juz": 30}  # sanity checks


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def rich_text_parts(cell_value):
    """Split a (rich-text) cell value into a list of (text, font) runs."""
    if cell_value is None:
        return []
    if isinstance(cell_value, str):            # plain string: one run without font
        return [(cell_value, None)]
    return [(run.text, getattr(run, "font", None)) if hasattr(run, "text")
            else (str(run), None) for run in cell_value]


def red_span(parts):
    """Return (start, end) character offsets of the red run, or None."""
    offset, span = 0, None
    for text, font in parts:
        is_red = (font is not None and font.color is not None
                  and font.color.rgb == RED_RGB)
        if is_red:
            span = (offset, offset + len(text))
        offset += len(text)
    return span


def encode_u16(values):
    """Encode an array('H') as a base64 string."""
    return base64.b64encode(values.tobytes()).decode()


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------
def build_payload(xlsx_path):
    """Read the workbook and return the payload dictionary."""
    # --- load the sheet and map header names to column indices -------------
    workbook = openpyxl.load_workbook(xlsx_path, rich_text=True)
    sheet = workbook[SHEET_NAME]
    header = [cell.value for cell in sheet[1]]
    column = {name: idx for idx, name in enumerate(header) if name}
    uthmani_col = next(idx for idx, name in enumerate(header)
                       if name and name.startswith(UTHMANI_VERSE_PREFIX))

    def value(row, name):
        """Cell value of a row in the column with the given header."""
        return row[column[name]].value

    # --- keep data rows and sort them by their position in the Quran -------
    rows = [r for r in sheet.iter_rows(min_row=2)
            if r[column["رقم السورة"]].value is not None]
    rows.sort(key=lambda r: value(r, "ترتيب الكلمة في القرآن"))

    # --- accumulators -------------------------------------------------------
    forms, roots = {}, {}                          # value -> index, insertion ordered
    tok_form, tok_root, red_a, red_b = (array.array("H") for _ in range(4))
    verse_start, surahs, page_start, juz_start, uthmani_verses = [], [], [], [], []
    prev_verse = prev_surah = prev_page = prev_juz = None

    # --- one pass over all word positions -----------------------------------
    for i, row in enumerate(rows):
        verse_key = (value(row, "رقم السورة"), value(row, "رقم الآية"))
        parts = rich_text_parts(row[uthmani_col].value)
        verse_text = "".join(text for text, _ in parts)

        if verse_key != prev_verse:                 # first word of a new verse
            verse_start.append(i)
            uthmani_verses.append(verse_text)
            prev_verse = verse_key
        assert uthmani_verses[-1] == verse_text, ("verse text differs inside one verse", verse_key)

        if verse_key[0] != prev_surah:              # first word of a new surah
            place = "m" if value(row, "مكان نزول السورة").startswith("مك") else "d"
            surahs.append([value(row, "السورة"), place, len(verse_start) - 1])
            prev_surah = verse_key[0]
        if value(row, "الصفحة") != prev_page:        # first word of a new page
            page_start.append(i)
            prev_page = value(row, "الصفحة")
        if value(row, "الجزء") != prev_juz:         # first word of a new juz
            juz_start.append(i)
            prev_juz = value(row, "الجزء")

        span = red_span(parts)                      # where this word sits in the Uthmani verse
        assert span, ("no red word", verse_key, i)
        tok_form.append(forms.setdefault(value(row, "الكلمة"), len(forms)))
        tok_root.append(roots.setdefault(value(row, "الجذر"), len(roots)))
        red_a.append(span[0])
        red_b.append(span[1])

    # --- sanity checks -------------------------------------------------------
    order = [value(r, "ترتيب الكلمة في القرآن") for r in rows]
    assert order == list(range(1, len(rows) + 1)), "word order is not 1..n"
    assert len(surahs) == EXPECTED["surahs"]
    assert len(verse_start) == EXPECTED["verses"]
    assert len(page_start) == EXPECTED["pages"]
    assert len(juz_start) == EXPECTED["juz"]

    # --- assemble the payload -----------------------------------------------
    return {
        "forms": list(forms), "roots": list(roots),
        "tokForm": encode_u16(tok_form), "tokRoot": encode_u16(tok_root),
        "verseStart": verse_start, "surahs": surahs,
        "pageStart": page_start, "juzStart": juz_start, "n": len(rows),
        "uVerses": uthmani_verses, "uA": encode_u16(red_a), "uB": encode_u16(red_b),
    }


def payload_to_json(payload):
    """Serialise the payload compactly, keeping Arabic as UTF-8."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    input_xlsx = Path(sys.argv[1] if len(sys.argv) > 1 else "القرآن الكريم.xlsx")
    output_json = Path(sys.argv[2] if len(sys.argv) > 2 else "build/data.json")
    payload = build_payload(input_xlsx)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    text = payload_to_json(payload)
    output_json.write_text(text, encoding="utf-8")
    print(f"rows {payload['n']} | distinct words {len(payload['forms'])} | "
          f"roots {len(payload['roots'])} | {len(text.encode()) // 1024} KB -> {output_json}")

# متصفح القرآن — Quran Root Browser

A word-level dataset of the Quran and an interactive single-file browser built from it.

Every root and every word blooms as a sunflower:

- **Core petals.** The most frequent word forms (or surahs, in word mode) form the core petals. Each petal shows how often its form occurs.
- **Outer ring.** An outer ring marks every occurrence across the mushaf, grouped by surah.
- **Others petal.** A plum "others" petal (صيغ أخرى / سور أخرى) collects the rarer forms. Clicking it unfolds them into up to three rows of smaller petals.
- **Verse list.** The verse list shows each occurrence in modern spelling (الإملاء الحديث), Uthmani script (الرسم العثماني), or both. The Uthmani line is blue when both are shown.

## Repository layout

| Path | Content |
|---|---|
| `القرآن الكريم.xlsx` | Curated word-level dataset (sheet `الكلمات`), one row per word, 87,399 rows. This is the source of truth. |
| `متصفح القرآن.html` | The built app: one self-contained file (≈2.9 MB) with data and Uthmani font embedded. Open it in any browser. |
| `src/template.html` | App source (HTML, CSS, JS) with the placeholders `__DATA__` and `__FONT__`. |
| `src/build_data.py` | Workbook → compact JSON payload. Columns are found by header name. |
| `src/build_app.py` | Builds `متصفح القرآن.html` from the workbook, template and font. |
| `tests/test_layout.py` | Headless-browser layout tests (desktop and two phone sizes). |
| `fonts/UthmanicHafs.woff2` | KFGQPC Uthmanic Script HAFS (v9), King Fahd Glorious Quran Printing Complex. |

### Workbook columns (sheet `الكلمات`)

- الصفحة، الكلمة، الكلمة بالرسم العثماني، الجزء
- مكان نزول السورة، رقم السورة، السورة، رقم الآية
- أول حرف في الكلمة، الجذر
- frequency and rank columns
- ترتيب الكلمة في الآية / في القرآن
- نص الآية and نص الآية بالرسم العثماني, with the current word in red

The app uses the values of `الكلمة` and `الجذر` exactly as written, diacritics included.

## Rebuilding the app after editing the workbook

```bash
python3 -m pip install -r requirements.txt
python3 src/build_app.py                 # writes متصفح القرآن.html
python3 -m playwright install chromium   # once, for the tests
python3 tests/test_layout.py             # exit code 0 = all layout checks pass
```

`build_data.py` checks the workbook before building:

- word order is 1..n
- 114 surahs, 6236 verses, 604 pages and 30 juz
- every row has exactly one red word in its Uthmani verse text

If any of these fails, the build stops.

## Notes

- **Fonts.** The Uthmani font is embedded. Amiri and IBM Plex Sans Arabic load from Google Fonts. Without a network connection the app falls back to system Arabic fonts.
- **Uthmani text.** The Uthmani verse text keeps pause and section marks. The single Uthmani words in the list omit pause marks.
- **Workbook size.** The workbook is stored compactly: shared strings and UTF-8. If Excel re-saves it, the file may grow again.

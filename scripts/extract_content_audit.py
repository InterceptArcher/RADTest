#!/usr/bin/env python3
"""
Extract an HP content-audit workbook (.xlsx) into the flat CSV that
`backend/content_audit.py` loads.

Why this exists
---------------
The audit workbook stores each asset's real DAM URL as a *hyperlink* behind the
visible cell text "Access here" — the cell value is NOT the URL. The first time
a content audit was integrated, the URLs were pulled out of the workbook by hand
(commit acd092d). This script makes that a repeatable, committed step.

It is intentionally stdlib-only (zipfile + xml.etree) so it runs anywhere with a
plain Python 3 — no openpyxl / pip required. An .xlsx is just a zip of XML.

Usage
-----
    python3 scripts/extract_content_audit.py            # uses V2 defaults
    python3 scripts/extract_content_audit.py --input <xlsx> --output <csv> --sheet Audit

The output CSV's headers match the workbook's own column names (V2:
`Type` / `Customer Journey` / `DAM Link`), which `content_audit._COLUMN_MAP`
maps onto its stable internal keys.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

# OOXML namespaces
_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

# The columns we carry into the CSV, in order, by their workbook header name.
# The workbook also has an unnamed index column and a "QA Flags" column; both are
# intentionally dropped — they are not consumed by the pipeline.
OUTPUT_HEADERS = [
    "Asset Name", "Industry", "Service/Solution", "Year Published", "Audience",
    "Asset Summary", "Type", "Format", "Page Count", "Marketing or Sales",
    "Customer Journey", "Inventory Recommendations", "DAM Link", "Audit Notes",
]
LINK_HEADER = "DAM Link"          # the column whose value is a cell hyperlink
ASSET_NAME_HEADER = "Asset Name"  # rows without this are skipped

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT = os.path.join(
    _REPO_ROOT, "template ",  # NB: the directory name has a trailing space
    "HP Canada_RAD Intelligence Desk_Content Audit_V2_Internal.xlsx",
)
DEFAULT_OUTPUT = os.path.join(
    _REPO_ROOT, "hp_assets",
    "HP Canada_RAD Intelligence Desk_Content Audit_V2.csv",
)


def _q(tag: str) -> str:
    return f"{{{_MAIN}}}{tag}"


def _col_letter(cell_ref: str) -> str:
    return re.match(r"([A-Z]+)", cell_ref).group(1)


def _row_number(cell_ref: str) -> int:
    return int(re.match(r"[A-Z]+(\d+)", cell_ref).group(1))


def _collapse(value: str) -> str:
    """Flatten embedded newlines / runs of whitespace, matching the loader."""
    return " ".join((value or "").split())


def _read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    strings = []
    for si in root.findall(_q("si")):
        strings.append("".join(t.text or "" for t in si.iter(_q("t"))))
    return strings


def _resolve_sheet_path(zf: zipfile.ZipFile, sheet_name: str) -> str:
    """Map a sheet's display name to its `xl/worksheets/sheetN.xml` part."""
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rid = None
    for sheet in wb.iter(_q("sheet")):
        if sheet.get("name") == sheet_name:
            rid = sheet.get(f"{{{_REL}}}id")
            break
    if rid is None:
        names = [s.get("name") for s in wb.iter(_q("sheet"))]
        raise SystemExit(f"Sheet {sheet_name!r} not found. Available: {names}")
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    for rel in rels:
        if rel.get("Id") == rid:
            target = rel.get("Target")
            return target if target.startswith("xl/") else f"xl/{target}"
    raise SystemExit(f"Could not resolve relationship {rid!r} for sheet {sheet_name!r}")


def _read_hyperlinks(zf: zipfile.ZipFile, sheet_path: str, sheet_xml: bytes) -> dict[str, str]:
    """Return {cell_ref: target_url} for external hyperlinks on the sheet."""
    sheet = ET.fromstring(sheet_xml)
    ref_to_rid: dict[str, str] = {}
    for h in sheet.iter(_q("hyperlink")):
        ref = (h.get("ref") or "").split(":")[0]  # single cell, even if a range is given
        rid = h.get(f"{{{_REL}}}id")
        if ref and rid:
            ref_to_rid[ref] = rid
    if not ref_to_rid:
        return {}
    base = os.path.basename(sheet_path)
    rels_path = sheet_path.replace(base, f"_rels/{base}.rels")
    if rels_path not in zf.namelist():
        return {}
    rels = ET.fromstring(zf.read(rels_path))
    rid_to_target = {r.get("Id"): r.get("Target") for r in rels}
    return {ref: rid_to_target[rid] for ref, rid in ref_to_rid.items() if rid in rid_to_target}


def _cell_value(cell: ET.Element, shared: list[str]) -> str:
    ctype = cell.get("t")
    v = cell.find(_q("v"))
    if ctype == "s" and v is not None:
        return shared[int(v.text)]
    if ctype == "inlineStr":
        return "".join(t.text or "" for t in cell.iter(_q("t")))
    return v.text if v is not None else ""


def extract(input_path: str, output_path: str, sheet_name: str) -> dict:
    if not os.path.exists(input_path):
        raise SystemExit(f"Input workbook not found: {input_path}")

    with zipfile.ZipFile(input_path) as zf:
        shared = _read_shared_strings(zf)
        sheet_path = _resolve_sheet_path(zf, sheet_name)
        sheet_xml = zf.read(sheet_path)
        hyperlinks = _read_hyperlinks(zf, sheet_path, sheet_xml)

        sheet = ET.fromstring(sheet_xml)
        rows: dict[int, dict[str, str]] = {}
        for cell in sheet.iter(_q("c")):
            ref = cell.get("r")
            if not ref:
                continue
            rows.setdefault(_row_number(ref), {})[_col_letter(ref)] = _cell_value(cell, shared)

    if 1 not in rows:
        raise SystemExit("No header row found in sheet")

    # header text -> column letter (headers are matched stripped)
    header_to_col = {(_collapse(v)): col for col, v in rows[1].items() if _collapse(v)}
    missing = [h for h in OUTPUT_HEADERS if h not in header_to_col]
    if missing:
        raise SystemExit(f"Workbook is missing expected columns: {missing}")

    link_col = header_to_col[LINK_HEADER]
    name_col = header_to_col[ASSET_NAME_HEADER]

    written, with_link, blank_link = 0, 0, 0
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADERS)
        writer.writeheader()
        for r in sorted(n for n in rows if n > 1):
            row = rows[r]
            if not _collapse(row.get(name_col, "")):
                continue  # skip rows with no asset name (e.g. trailing blank row)
            out = {}
            for header in OUTPUT_HEADERS:
                col = header_to_col[header]
                if header == LINK_HEADER:
                    url = hyperlinks.get(f"{col}{r}", "")  # real URL, blank if none
                    out[header] = url
                    if url:
                        with_link += 1
                    else:
                        blank_link += 1
                else:
                    out[header] = _collapse(row.get(col, ""))
            writer.writerow(out)
            written += 1

    return {"written": written, "with_link": with_link, "blank_link": blank_link}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default=DEFAULT_INPUT, help="path to the .xlsx workbook")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="path to the CSV to write")
    parser.add_argument("--sheet", default="Audit", help="worksheet name to extract (default: Audit)")
    args = parser.parse_args(argv)

    stats = extract(args.input, args.output, args.sheet)
    print(f"Wrote {stats['written']} assets to {args.output}")
    print(f"  with resolved DAM URL: {stats['with_link']}")
    print(f"  without a link:        {stats['blank_link']}")
    if stats["written"] == 0:
        sys.exit("ERROR: no rows written")


if __name__ == "__main__":
    main()

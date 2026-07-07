"""
Fix pptxgenjs 4.x PPTX files.

Two classes of bugs are patched:

A) Embedded Excel workbook (bubble-chart data):
   1. Table ref is hardcoded to "A1:C3" regardless of actual row count.
   2. Column 1 is named "X-Values" but the header cell contains "X-Axis".
   PowerPoint validates both and triggers its repair dialog on mismatch.

B) Slide XML — negative shape extents:
   pptxgenjs writes negative cy/cx in <a:ext> for "upward" or "leftward"
   lines.  OOXML's ST_PositiveCoordinate constraint forbids negative values.
   The fix shifts the origin to the correct corner, makes the extent positive,
   and adds flipV="1" / flipH="1" to preserve line direction.

Usage:
    python fix_pptx_bubble_charts.py [path/to/file.pptx]

Defaults to prototypes/output/rb_style_infographic_experiment.pptx.
Writes the fix in-place (originals are not kept; run from a clean state).
"""

from __future__ import annotations

import io
import re
import sys
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PPTX = BASE_DIR / "prototypes" / "output" / "rb_style_infographic_experiment.pptx"


def _count_sheet_rows(zin: zipfile.ZipFile, sheet_name: str = "xl/worksheets/sheet1.xml") -> int:
    """Return the highest row number present in the worksheet."""
    try:
        raw = zin.read(sheet_name).decode("utf-8")
        rows = [int(r) for r in re.findall(r'<row r="(\d+)"', raw)]
        return max(rows, default=1)
    except KeyError:
        return 1


def _fix_xlsx(xlsx_bytes: bytes) -> bytes:
    """Return a patched copy of the embedded Excel workbook."""
    src = io.BytesIO(xlsx_bytes)

    # Pre-scan to determine actual row count before rewriting anything.
    with zipfile.ZipFile(src, "r") as zin:
        max_row = _count_sheet_rows(zin)

    src.seek(0)
    dst = io.BytesIO()

    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)

            if item.filename == "xl/worksheets/sheet1.xml":
                # Fix <dimension ref="A1:C?"> in case it's also wrong.
                # Replacement must include the closing quote (no extra b'"' needed).
                data = re.sub(
                    rb'<dimension ref="A1:C\d+"',
                    f'<dimension ref="A1:C{max_row}"'.encode(),
                    data,
                )

            elif item.filename == "xl/tables/table1.xml":
                text = data.decode("utf-8")
                # Fix table ref range: ref="A1:C3" → ref="A1:C{max_row}"
                text = re.sub(
                    r'(ref="A1:C)\d+(")',
                    rf'\g<1>{max_row}\2',
                    text,
                )
                # Fix column 1 name: "X-Values" → "X-Axis" (must match header cell)
                text = text.replace('name="X-Values"', 'name="X-Axis"')
                data = text.encode("utf-8")

            zout.writestr(item, data)

    return dst.getvalue()


def _fix_negative_extents(xml_bytes: bytes) -> tuple[bytes, int]:
    """
    Fix <a:xfrm> blocks that have a negative cy or cx in <a:ext>.

    OOXML ST_PositiveCoordinate forbids negative values.  pptxgenjs 4.x
    writes negative values for lines that go upward or leftward instead of
    using flipV/flipH + a positive extent.

    Returns the patched bytes and the number of fixes applied.
    """
    import xml.etree.ElementTree as ET

    NS = {
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    for prefix, uri in NS.items():
        ET.register_namespace(prefix, uri)

    # Preserve the XML declaration (ET strips it).
    text = xml_bytes.decode("utf-8")
    decl = ""
    if text.startswith("<?xml"):
        decl = text[: text.index("?>") + 2] + "\n"

    root = ET.fromstring(text)
    fixes = 0

    # <a:xfrm> can appear in <p:spPr> and <p:grpSpPr>
    for xfrm in root.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}xfrm"):
        off = xfrm.find("{http://schemas.openxmlformats.org/drawingml/2006/main}off")
        ext = xfrm.find("{http://schemas.openxmlformats.org/drawingml/2006/main}ext")
        if off is None or ext is None:
            continue

        cx = int(ext.get("cx", "0"))
        cy = int(ext.get("cy", "0"))
        ox = int(off.get("x", "0"))
        oy = int(off.get("y", "0"))

        changed = False
        if cx < 0:
            off.set("x", str(ox + cx))
            ext.set("cx", str(-cx))
            xfrm.set("flipH", "1")
            changed = True
        if cy < 0:
            off.set("y", str(oy + cy))
            ext.set("cy", str(-cy))
            xfrm.set("flipV", "1")
            changed = True
        if changed:
            fixes += 1

    patched = ET.tostring(root, encoding="unicode", xml_declaration=False)
    return (decl + patched).encode("utf-8"), fixes


def fix_pptx(pptx_path: Path) -> None:
    raw = pptx_path.read_bytes()
    src = io.BytesIO(raw)
    dst = io.BytesIO()

    with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)

            # Fix embedded Excel workbooks (chart data).
            if item.filename.startswith("ppt/embeddings/") and item.filename.endswith(".xlsx"):
                try:
                    data = _fix_xlsx(data)
                    print(f"  patched {item.filename}")
                except Exception as exc:
                    print(f"  WARNING: could not patch {item.filename}: {exc}")

            # Fix negative extents in slide XML.
            elif item.filename.startswith("ppt/slides/") and item.filename.endswith(".xml"):
                try:
                    data, n = _fix_negative_extents(data)
                    if n:
                        print(f"  fixed {n} negative extent(s) in {item.filename}")
                except Exception as exc:
                    print(f"  WARNING: could not fix extents in {item.filename}: {exc}")

            zout.writestr(item, data)

    pptx_path.write_bytes(dst.getvalue())
    print(f"Fixed: {pptx_path}")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PPTX
    if not target.exists():
        sys.exit(f"File not found: {target}")
    print(f"Patching {target} ...")
    fix_pptx(target)

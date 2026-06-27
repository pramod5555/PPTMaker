"""
convert_pymupdf.py — PDF -> PNG conversion using PyMuPDF (no poppler needed).

Converts every PDF in /pdfs/ to per-page PNGs in /slides/.
Skips pages that already exist (safe to re-run).

Usage:
    python convert_pymupdf.py                    # all PDFs
    python convert_pymupdf.py --pdf myfile.pdf   # one specific PDF
    python convert_pymupdf.py --dpi 120          # faster/smaller (default 150)
    python convert_pymupdf.py --max-pages 0      # 0 = no limit (default 0)
    python convert_pymupdf.py --new-only         # skip PDFs with any existing slides
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

BASE_DIR  = Path(__file__).parent
PDFS_DIR  = BASE_DIR / "pdfs"
SLIDES_DIR = BASE_DIR / "slides"
SLIDES_DIR.mkdir(exist_ok=True)


def pdf_stem(pdf_path: Path) -> str:
    """Normalised stem used as prefix for slide filenames."""
    return pdf_path.stem.lower().replace(" ", "_")


def already_converted(stem: str) -> set[str]:
    return {p.name for p in SLIDES_DIR.glob(f"{stem}_slide_*.png")}


def convert_one(pdf_path: Path, dpi: int, max_pages: int, new_only: bool) -> int:
    stem     = pdf_stem(pdf_path)
    existing = already_converted(stem)

    if new_only and existing:
        print(f"  [skip]  {pdf_path.name} — {len(existing)} slides already exist")
        return 0

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        print(f"  [error] {pdf_path.name}: {exc}")
        return 0

    pages = min(len(doc), max_pages) if max_pages > 0 else len(doc)
    new_count = 0
    mat = fitz.Matrix(dpi / 72, dpi / 72)  # 72 pt/inch baseline

    for page_num in range(1, pages + 1):
        out_name = f"{stem}_slide_{page_num:03d}.png"
        if out_name in existing:
            continue
        page = doc[page_num - 1]
        pix  = page.get_pixmap(matrix=mat, alpha=False)
        pix.save(str(SLIDES_DIR / out_name))
        new_count += 1

    doc.close()
    if new_count:
        print(f"  [done]  {pdf_path.name}: {new_count} new PNGs  ({pages} pages total)")
    else:
        print(f"  [skip]  {pdf_path.name}: all {pages} pages already exist")
    return new_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert PDFs -> slide PNGs via PyMuPDF")
    parser.add_argument("--pdf",       default=None, help="Convert a single PDF file")
    parser.add_argument("--dpi",       type=int, default=150)
    parser.add_argument("--max-pages", type=int, default=0, help="0 = no limit")
    parser.add_argument("--new-only",  action="store_true",
                        help="Skip PDFs that already have any converted slides")
    args = parser.parse_args()

    if args.pdf:
        pdf_files = [Path(args.pdf).resolve()]
        if not pdf_files[0].exists():
            # Try relative to pdfs/
            pdf_files = [PDFS_DIR / args.pdf]
        if not pdf_files[0].exists():
            print(f"PDF not found: {args.pdf}")
            sys.exit(1)
    else:
        pdf_files = sorted(PDFS_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDFs found in {PDFS_DIR}")
        sys.exit(0)

    print(f"Converting {len(pdf_files)} PDF(s) at {args.dpi} DPI"
          + (f", max {args.max_pages} pages each" if args.max_pages else ""))
    print()

    total_new = 0
    for p in pdf_files:
        total_new += convert_one(p, args.dpi, args.max_pages, args.new_only)

    existing_total = len(list(SLIDES_DIR.glob("*.png")))
    print(f"\nNew PNGs created : {total_new}")
    print(f"Total PNGs       : {existing_total}")


if __name__ == "__main__":
    main()

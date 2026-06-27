"""
converter.py — Convert PDFs in /pdfs/ to slide PNGs in /slides/.

Requires Poppler on the system PATH for pdf2image to work:
  Windows: https://github.com/oschwartz10612/poppler-windows/releases
           Extract and add bin/ to PATH, or set POPPLER_PATH in .env
  macOS:   brew install poppler
  Linux:   apt install poppler-utils
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError
from tqdm import tqdm

BASE_DIR = Path(__file__).parent

# Load .env from the same directory as this script (works regardless of CWD)
load_dotenv(dotenv_path=BASE_DIR / ".env")

PDFS_DIR = BASE_DIR / "pdfs"
SLIDES_DIR = BASE_DIR / "slides"
SLIDES_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "converter.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

DPI = 150
MAX_PAGES = 15


def _find_poppler_path() -> str | None:
    # 1. Explicit env var from .env or shell
    env_val = os.getenv("POPPLER_PATH")
    if env_val:
        return env_val
    # 2. Auto-detect a local poppler/ subfolder extracted by the setup instructions
    for candidate in BASE_DIR.glob("poppler/**/pdftoppm.exe"):
        return str(candidate.parent)
    return None


POPPLER_PATH = _find_poppler_path()


def convert_pdf(pdf_path: Path) -> int:
    """
    Convert one PDF to PNGs. Returns number of new PNGs written.
    Skips pages that already exist (resume support).
    """
    stem = pdf_path.stem
    new_slides = 0

    # Check which pages are already done so we can skip
    existing = {f.name for f in SLIDES_DIR.glob(f"{stem}_slide_*.png")}

    try:
        kwargs = {"dpi": DPI, "last_page": MAX_PAGES}
        if POPPLER_PATH:
            kwargs["poppler_path"] = POPPLER_PATH

        images = convert_from_path(str(pdf_path), **kwargs)
    except PDFInfoNotInstalledError:
        log.error(
            f"{pdf_path.name}: Poppler not found. "
            "Install Poppler and add it to PATH (or set POPPLER_PATH in .env)."
        )
        return 0
    except PDFPageCountError as e:
        log.error(f"{pdf_path.name}: Page count error — {e}")
        return 0
    except Exception as e:
        log.error(f"{pdf_path.name}: Conversion failed — {e}")
        return 0

    log.info(f"{pdf_path.name}: {len(images)} page(s) to process")

    for page_num, img in enumerate(images, start=1):
        out_name = f"{stem}_slide_{page_num:03d}.png"
        if out_name in existing:
            log.info(f"Skip (exists): {out_name}")
            continue
        out_path = SLIDES_DIR / out_name
        try:
            img.save(str(out_path), "PNG")
            new_slides += 1
        except Exception as e:
            log.error(f"Could not save {out_name}: {e}")

    return new_slides


def main():
    pdf_files = sorted(PDFS_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {PDFS_DIR}. Run scraper.py first (or drop PDFs manually).")
        sys.exit(0)

    print(f"Found {len(pdf_files)} PDF(s). Converting at {DPI} DPI, cap {MAX_PAGES} pages each.\n")

    total_new = 0
    for pdf_path in tqdm(pdf_files, desc="Converting PDFs", unit="pdf"):
        n = convert_pdf(pdf_path)
        total_new += n
        log.info(f"{pdf_path.name}: {n} new slides written")

    all_slides = len(list(SLIDES_DIR.glob("*.png")))
    print(f"\nNew slide PNGs created this run : {total_new}")
    print(f"Total slide PNGs in /slides/    : {all_slides}")
    print(f"Slides directory                : {SLIDES_DIR}")


if __name__ == "__main__":
    main()

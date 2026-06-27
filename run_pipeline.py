"""
run_pipeline.py — Orchestrate the full slide dataset pipeline.

Usage:
  python run_pipeline.py                                # scrape + convert + batch_prep
  python run_pipeline.py --skip-scrape                  # convert + batch_prep (PDFs ready)
  python run_pipeline.py --skip-scrape --skip-convert   # batch_prep only (PNGs ready)
  python run_pipeline.py --ingest-only                  # build dataset.json from labels
  python run_pipeline.py --seeds                        # scrape using curated seed URLs
  python run_pipeline.py --seeds --skip-scrape          # seeds only, then convert+batch
"""

import argparse
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent


def run_script(script_name: str, extra_args: list[str] | None = None) -> int:
    """Run a sibling script with the current Python interpreter."""
    script_path = BASE_DIR / script_name
    cmd = [sys.executable, str(script_path)] + (extra_args or [])

    sep = "=" * 56
    print(f"\n{sep}")
    print(f"  RUNNING: {script_name}")
    print(sep)

    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="PPT Dataset Pipeline Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Skip scraper.py (PDFs already in /pdfs/)",
    )
    parser.add_argument(
        "--skip-convert",
        action="store_true",
        help="Skip converter.py (PNGs already in /slides/)",
    )
    parser.add_argument(
        "--ingest-only",
        action="store_true",
        help="Skip everything except label_ingest.py",
    )
    parser.add_argument(
        "--sitemap",
        action="store_true",
        help="Pass --sitemap flag to scraper.py (sitemap.xml fallback for JS-heavy sites)",
    )
    parser.add_argument(
        "--seeds",
        action="store_true",
        help="Pass --seeds flag to scraper.py (download curated known-good PDF URLs)",
    )
    parser.add_argument(
        "--seeds-only",
        action="store_true",
        help="Only download seed PDFs, skip all web scrapers",
    )
    args = parser.parse_args()

    if args.ingest_only:
        rc = run_script("label_ingest.py")
        sys.exit(rc)

    errors: list[str] = []

    if not args.skip_scrape:
        scraper_args = []
        if args.sitemap:
            scraper_args.append("--sitemap")
        if args.seeds:
            scraper_args.append("--seeds")
        if args.seeds_only:
            scraper_args.append("--seeds-only")
        rc = run_script("scraper.py", scraper_args)
        if rc != 0:
            errors.append(f"scraper.py exited {rc} — see scraper.log")

    if not args.skip_convert:
        rc = run_script("converter.py")
        if rc != 0:
            errors.append(f"converter.py exited {rc} — see converter.log")

    rc = run_script("batch_prep.py")
    if rc != 0:
        errors.append(f"batch_prep.py exited {rc}")

    print("\n" + "=" * 56)
    print("  PIPELINE COMPLETE")
    print("=" * 56)

    if errors:
        print("\nWarnings / errors:")
        for e in errors:
            print(f"  ✗ {e}")

    print(
        "\nNext steps:"
        "\n  1. Open  ppt-dataset/batches/INSTRUCTIONS.txt"
        "\n  2. Label each batch on claude.ai (upload 5 PNGs + paste prompt.txt)"
        "\n  3. Save each response as  batches/batch_XXX/response.json"
        "\n  4. Run:  python run_pipeline.py --ingest-only"
    )


if __name__ == "__main__":
    main()

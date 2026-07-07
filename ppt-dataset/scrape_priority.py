"""Run Bain and L.E.K. scraping with priority."""
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from scraper import scrape_bain, scrape_lek, download_pdf, SEED_PDFS

bain_seeds = [e for e in SEED_PDFS if e[0] == "bain"]
print(f"Trying {len(bain_seeds)} direct Bain seed PDFs...")
for entry in bain_seeds:
    company, url = entry[0], entry[1]
    fname = entry[2] if len(entry) > 2 else None
    ok = download_pdf(url, company, filename=fname)
    print(f"  {fname}: {'OK' if ok else 'FAIL/EXISTS'}")

print("\nScraping Bain topic pages (limit 50)...")
b = scrape_bain(50)

print(f"\nScraping L.E.K. (limit 30)...")
l = scrape_lek(30)

print(f"\nDone. Bain new PDFs: {b}, L.E.K. new PDFs: {l}")

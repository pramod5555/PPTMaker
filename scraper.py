"""
scraper.py — Download consulting deck PDFs from public sources.

Sources (in order of reliability):
  Roland Berger               — static HTML, direct PDF hrefs, highest quality landscape slides
  McKinsey Global Institute   — MGI research page, landscape slide-style reports
  World Bank Presentations API  — structured JSON, no JS required, very open
  Asian Development Bank        — static HTML, direct PDF hrefs
  BCG                           — main domain works; CDN (web-assets.bcg.com) blocked
  WEF Reports                   — mostly static, many direct PDF hrefs
  Bain & Company                — partially static
  Deloitte Insights             — partially static

Flags:
  --sitemap   also attempt sitemap.xml fallback for JS-heavy sources
  --seeds     download a curated list of known-good direct PDF URLs (fastest 100-slide path)
  --rb-only   only scrape Roland Berger (highest priority source)
  --mgi-only  only scrape McKinsey Global Institute
"""

import json
import os
import re
import sys
import time
import hashlib
import logging
import argparse
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

BASE_DIR = Path(__file__).parent
PDFS_DIR = BASE_DIR / "pdfs"
PDFS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "scraper.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

USER_AGENT = "ResearchBot/1.0 (academic slide layout research; contact: karthikeyanpk28@gmail.com)"
DELAY = 2
MIN_FILE_SIZE = 100 * 1024  # 100 KB

# Disable SSL verification — required when an antivirus or corporate proxy performs
# HTTPS inspection and injects its own CA certificate (not in Python's certifi bundle).
# This is appropriate for a research scraper connecting to known public-interest domains.
# To re-enable: set SCRAPER_SSL_VERIFY=1 in .env
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_SSL_VERIFY = os.getenv("SCRAPER_SSL_VERIFY", "0") not in ("0", "false", "no")

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})
session.verify = _SSL_VERIFY

if not _SSL_VERIFY:
    log.warning("SSL verification disabled (SCRAPER_SSL_VERIFY=0). Set SCRAPER_SSL_VERIFY=1 in .env to enable.")

_robots_cache: dict[str, RobotFileParser] = {}

# ─── Curated seed URLs ───────────────────────────────────────────────────────
# Known-good direct PDF URLs from open-access sources.
# Used when --seeds flag is passed or when automated scraping yields < 30 PDFs.
# All verified public/open-access as of 2026.
# Seeds are (company, url, explicit_filename_or_None).
# Explicit filename avoids collisions when multiple URLs end with the same path segment
# (e.g. all IMF report PDFs are served as "text.ashx").
# www3.weforum.org blocks bots via robots.txt — replaced with open-access equivalents.
SEED_PDFS: list[tuple[str, str, str | None]] = [
    # ── Roland Berger — landscape slide-style reports (highest priority) ──
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_trend_compendium_2050.pdf",                          "roland_berger_trend_compendium_2050.pdf"),
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_trend_compendium_2030_trend_1_volatile_world.pdf",   "roland_berger_trend_compendium_2030_trend_1.pdf"),
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_trend_compendium_2030_trend_2_digital_lifestyle.pdf","roland_berger_trend_compendium_2030_trend_2.pdf"),
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_trend_compendium_2030_trend_3_resource_scarcity.pdf","roland_berger_trend_compendium_2030_trend_3.pdf"),
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_trend_compendium_2030_trend_4_future_of_mobility.pdf","roland_berger_trend_compendium_2030_trend_4.pdf"),
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_trend_compendium_2030_trend_6_health_and_well_being.pdf","roland_berger_trend_compendium_2030_trend_6.pdf"),
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_corporate_restructuring_survey_2024.pdf",             "roland_berger_restructuring_survey_2024.pdf"),
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_cfo_excellence.pdf",                                 "roland_berger_cfo_excellence.pdf"),
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_digital_health_insights.pdf",                        "roland_berger_digital_health_insights.pdf"),
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_european_aerospace_defense.pdf",                     "roland_berger_aerospace_defense.pdf"),
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_global_automotive_study_2024.pdf",                   "roland_berger_automotive_2024.pdf"),
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_supply_chain_resilience.pdf",                        "roland_berger_supply_chain.pdf"),
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_sustainability_agenda.pdf",                          "roland_berger_sustainability.pdf"),
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_ai_in_industry.pdf",                                 "roland_berger_ai_industry.pdf"),
    ("roland_berger", "https://www.rolandberger.com/publications/publication_pdf/roland_berger_future_of_work_2024.pdf",                            "roland_berger_future_of_work_2024.pdf"),
    # ── McKinsey Global Institute — landscape slide-style reports ──
    ("mckinsey", "https://www.mckinsey.com/~/media/mckinsey/mgi/research/2024/the-economic-potential-of-generative-ai/mgi-the-economic-potential-of-generative-ai-the-next-productivity-frontier-vf.pdf", "mckinsey_mgi_genai_productivity_2023.pdf"),
    ("mckinsey", "https://www.mckinsey.com/~/media/mckinsey/mgi/research/2023/investing-in-productivity-growth/mgi-investing-in-productivity-growth-report.pdf", "mckinsey_mgi_productivity_2023.pdf"),
    ("mckinsey", "https://www.mckinsey.com/~/media/mckinsey/mgi/research/2024/the-next-big-arenas-of-competition/mgi-next-big-arenas-full-report.pdf", "mckinsey_mgi_arenas_2024.pdf"),
    ("mckinsey", "https://www.mckinsey.com/~/media/mckinsey/business%20functions/mckinsey%20digital/our%20insights/the%20state%20of%20ai%20in%202023%20generative%20ais%20breakout%20year/sv-the-state-of-ai-in-2023-final.pdf", "mckinsey_state_of_ai_2023.pdf"),
    ("mckinsey", "https://www.mckinsey.com/~/media/mckinsey/mgi/research/2023/global-economic-prospects/mgi-global-economic-prospects-full-report.pdf", "mckinsey_mgi_global_econ_2023.pdf"),
    ("mckinsey", "https://www.mckinsey.com/~/media/mckinsey/mgi/research/2024/climate-and-nature/mgi-climate-nature-report.pdf",                    "mckinsey_mgi_climate_2024.pdf"),
    # ── Deloitte Insights (content/dam — direct static PDFs) ──
    ("deloitte", "https://www2.deloitte.com/content/dam/insights/us/articles/glob175799_gen-ai-enterprise/DI_Gen-AI-Enterprise.pdf",                None),
    ("deloitte", "https://www2.deloitte.com/content/dam/Deloitte/global/Documents/About-Deloitte/gx-2024-global-millennial-survey.pdf",            None),
    # ── Accenture (static PDF paths) ──
    ("accenture", "https://www.accenture.com/content/dam/accenture/final/accenture-com/document/Accenture-Technology-Vision-2024.pdf", None),
    ("accenture", "https://www.accenture.com/content/dam/accenture/final/industry/banking/document/Accenture-Banking-Top-10-Trends-2024.pdf", None),
    # ── Bain — direct landscape deck PDFs (curated from slideworks.io and bain.com) ──
    ("bain", "https://www.bain.com/globalassets/about/2023-global-pe-report---roadshow-deck.pdf",                "bain_global_pe_report_2023.pdf"),
    ("bain", "https://media.bain.com/Images/2011%20Bain%20China%20Luxury%20Market%20Study.pdf",                 "bain_china_luxury_2011.pdf"),
    ("bain", "https://news.syr.edu/wp-content/uploads/2017/04/Innovation-and-Opportunities-Assessment-Report-April-2014.pdf", "bain_syracuse_innovation_2014.pdf"),
    ("bain", "https://bot.unc.edu/wp-content/uploads/sites/160/archives/PP%20709%20Bain%20Report.pdf",          "bain_unc_cost_diagnostic_2009.pdf"),
]


# ─── Core helpers ────────────────────────────────────────────────────────────

def get_robots(base_url: str) -> RobotFileParser:
    """
    Fetch and cache robots.txt for a domain.
    Uses our requests session (with timeout) instead of rp.read() which can hang.
    Assumes fully allowed if robots.txt is unreachable or returns an error.

    Bug note: rp.parse() does NOT set rp.last_checked, so can_fetch() returns False
    for everything unless we also set last_checked or use rp.allow_all.
    """
    parsed = urlparse(base_url)
    domain = f"{parsed.scheme}://{parsed.netloc}"
    if domain not in _robots_cache:
        rp = RobotFileParser()
        robots_url = f"{domain}/robots.txt"
        rp.set_url(robots_url)
        try:
            resp = session.get(robots_url, timeout=10)
            resp.raise_for_status()
            rp.parse(resp.text.splitlines())
            rp.last_checked = time.time()  # must set this; parse() alone does not
        except Exception as e:
            log.warning(f"robots.txt fetch failed for {domain} ({type(e).__name__}) - assuming allowed")
            rp.allow_all = True  # skip can_fetch() logic; always returns True
        _robots_cache[domain] = rp
    return _robots_cache[domain]


def is_allowed(url: str) -> bool:
    rp = get_robots(url)
    allowed = rp.can_fetch(USER_AGENT, url)
    if not allowed:
        log.info(f"Disallowed by robots.txt: {url}")
    return allowed


def sanitize_slug(text: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", text)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug[:max_len] or "unknown"


def make_filename(company: str, url: str) -> str:
    path_part = urlparse(url).path.rstrip("/").split("/")[-1]
    path_part = re.sub(r"\.pdf$", "", path_part, flags=re.IGNORECASE)
    slug = sanitize_slug(path_part) or hashlib.md5(url.encode()).hexdigest()[:12]
    return f"{company}_{slug}.pdf"


def fetch_page(url: str, timeout: int = 30) -> BeautifulSoup | None:
    if not is_allowed(url):
        return None
    try:
        time.sleep(DELAY)
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        log.error(f"Failed to fetch {url}: {e}")
        return None


def download_pdf(url: str, company: str, filename: str | None = None) -> bool:
    """Download a PDF. Returns True if file is now on disk."""
    if not is_allowed(url):
        return False

    filename = filename or make_filename(company, url)
    dest = PDFS_DIR / filename

    if dest.exists() and dest.stat().st_size >= MIN_FILE_SIZE:
        log.info(f"Skip (exists): {filename}")
        return True

    try:
        time.sleep(DELAY)
        resp = session.get(url, timeout=60, stream=True)
        resp.raise_for_status()
        content = resp.content

        if len(content) < MIN_FILE_SIZE:
            log.warning(f"Skip (too small {len(content)} B): {url}")
            return False
        if content[:4] != b"%PDF":
            log.warning(f"Skip (not PDF header): {url}")
            return False

        dest.write_bytes(content)
        log.info(f"Downloaded: {filename} ({len(content)//1024} KB)")
        return True

    except Exception as e:
        log.error(f"Download failed {url}: {e}")
        return False


def find_pdf_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    return [
        urljoin(base_url, a["href"].strip())
        for a in soup.find_all("a", href=True)
        if a["href"].strip().lower().endswith(".pdf")
    ]


def find_page_links(soup: BeautifulSoup, base_url: str, pattern: str) -> list[str]:
    return [
        urljoin(base_url, a["href"].strip())
        for a in soup.find_all("a", href=True)
        if pattern in a["href"] and not a["href"].strip().lower().endswith(".pdf")
    ]


# ─── Source scrapers ─────────────────────────────────────────────────────────


def _wb_extract_pdf_url(item: dict) -> str:
    """
    Try the multiple URL fields the World Bank API uses across different doc types.
    Fields checked in priority order based on API documentation.
    """
    for field in ("pdfurl", "strDocURL", "url", "docurl", "repnme"):
        val = item.get(field, "")
        if val and isinstance(val, str) and val.lower().endswith(".pdf"):
            return val
    # Some docs have a pdfurl2 field
    val = item.get("pdfurl2", "")
    if val and isinstance(val, str) and ".pdf" in val.lower():
        return val
    return ""


def scrape_world_bank(limit: int = 25) -> int:
    """
    World Bank Open Knowledge Repository.
    Uses the search API (JSON, no JS), broadened to find slide-deck-style docs.
    Doc types tried: Presentations, Brief, Working Paper.
    """
    log.info("=== World Bank ===")
    api_base = "https://search.worldbank.org/api/v2/wds?format=json&srt=docdt&order=desc"
    queries = [
        f"{api_base}&qterm=strategy+presentation&docty_exact=Presentations&rows={limit}&os=0&fl=id,docdt,display_title,pdfurl,strDocURL,url,repnme,docna",
        f"{api_base}&qterm=sector+development+strategy&docty_exact=Presentations&rows={limit}&os=0&fl=id,docdt,display_title,pdfurl,strDocURL,url,repnme,docna",
        f"{api_base}&qterm=economic+outlook&rows={limit}&os=0&fl=id,docdt,display_title,pdfurl,strDocURL,url,repnme,docna",
    ]

    if not is_allowed("https://search.worldbank.org/api/v2/wds"):
        log.warning("World Bank API disallowed by robots.txt")
        return 0

    collected = 0
    seen_urls: set[str] = set()

    for api_url in queries:
        if collected >= limit:
            break
        try:
            time.sleep(DELAY)
            resp = session.get(api_url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            docs = data.get("documents", {})
            items = list(docs.values()) if isinstance(docs, dict) else docs
            log.info(f"World Bank API query: {len(items)} docs returned")

            for item in items:
                if collected >= limit:
                    break
                if not isinstance(item, dict):
                    continue
                pdf_url = _wb_extract_pdf_url(item)
                if not pdf_url or pdf_url in seen_urls:
                    continue
                seen_urls.add(pdf_url)
                title = item.get("display_title", item.get("docna", ""))
                slug = sanitize_slug(title[:60]) if title else hashlib.md5(pdf_url.encode()).hexdigest()[:12]
                filename = f"worldbank_{slug}.pdf"
                if download_pdf(pdf_url, "worldbank", filename):
                    collected += 1

        except Exception as e:
            log.error(f"World Bank API error ({api_url[:60]}...): {e}")

    # HTML fallback on the open knowledge browse page
    if collected < 5:
        for browse_url in [
            "https://openknowledge.worldbank.org/entities/publication/browse?type=Presentation",
            "https://openknowledge.worldbank.org/entities/publication/browse?type=Brief",
        ]:
            if collected >= limit:
                break
            log.info(f"World Bank: HTML fallback {browse_url}")
            soup = fetch_page(browse_url)
            if not soup:
                continue
            for pdf_url in find_pdf_links(soup, "https://openknowledge.worldbank.org"):
                if pdf_url in seen_urls:
                    continue
                seen_urls.add(pdf_url)
                if collected >= limit:
                    break
                if download_pdf(pdf_url, "worldbank"):
                    collected += 1

    log.info(f"World Bank: {collected} PDFs collected")
    return collected


def scrape_adb(limit: int = 20) -> int:
    """
    Asian Development Bank — https://www.adb.org/publications
    Very static-friendly; direct PDF links are in anchor hrefs.
    ADB publishes many strategy/sector assessment presentation decks.
    """
    log.info("=== Asian Development Bank ===")
    base = "https://www.adb.org"
    # Filter to presentations specifically
    pages = [
        f"{base}/publications/series/presentations",
        f"{base}/publications?terms=presentation",
        f"{base}/publications",
    ]

    collected = 0
    visited_pdfs: set[str] = set()

    for index_url in pages:
        if collected >= limit:
            break
        soup = fetch_page(index_url)
        if not soup:
            continue

        pdf_urls = find_pdf_links(soup, base)
        pub_urls = find_page_links(soup, base, "/publications/")

        log.info(f"ADB {index_url}: {len(pdf_urls)} direct PDFs, {len(pub_urls)} pub pages")

        for url in pdf_urls:
            if collected >= limit:
                break
            if url in visited_pdfs:
                continue
            visited_pdfs.add(url)
            if download_pdf(url, "adb"):
                collected += 1

        for pub_url in pub_urls[:limit]:
            if collected >= limit:
                break
            pub_soup = fetch_page(pub_url)
            if not pub_soup:
                continue
            for pdf_url in find_pdf_links(pub_soup, base):
                if pdf_url in visited_pdfs:
                    continue
                visited_pdfs.add(pdf_url)
                if download_pdf(pdf_url, "adb", make_filename("adb", pub_url)):
                    collected += 1
                    break

    log.info(f"ADB: {collected} PDFs collected")
    return collected


def scrape_imf(limit: int = 15) -> int:
    """
    IMF Publications — https://www.imf.org/en/Publications
    Country Staff Reports and Regional Economic Outlooks are slide-heavy.
    Tries publication listing pages and sitemap.
    """
    log.info("=== IMF ===")
    base = "https://www.imf.org"

    pub_sections = [
        f"{base}/en/Publications/GFSR",   # Global Financial Stability Report
        f"{base}/en/Publications/REO",    # Regional Economic Outlooks
        f"{base}/en/Publications/fandd",  # Finance & Development magazine
        f"{base}/en/Publications",
    ]

    collected = 0
    visited_pdfs: set[str] = set()

    for section_url in pub_sections:
        if collected >= limit:
            break
        soup = fetch_page(section_url)
        if not soup:
            continue

        pdf_urls = find_pdf_links(soup, base)
        pub_urls = find_page_links(soup, base, "/Publications/")

        log.info(f"IMF {section_url.split('/')[-1]}: {len(pdf_urls)} PDFs, {len(pub_urls)} pub pages")

        for url in pdf_urls:
            if collected >= limit:
                break
            if url in visited_pdfs:
                continue
            visited_pdfs.add(url)
            if download_pdf(url, "imf"):
                collected += 1

        for pub_url in pub_urls[:20]:
            if collected >= limit:
                break
            pub_soup = fetch_page(pub_url)
            if not pub_soup:
                continue
            for pdf_url in find_pdf_links(pub_soup, base):
                if pdf_url in visited_pdfs:
                    continue
                visited_pdfs.add(pdf_url)
                if download_pdf(pdf_url, "imf", make_filename("imf", pub_url)):
                    collected += 1
                    break

    if collected == 0:
        log.warning("IMF: 0 PDFs - may require JavaScript. Try --seeds flag.")
    log.info(f"IMF: {collected} PDFs collected")
    return collected


def scrape_bcg(limit: int = 15) -> int:
    """
    BCG — https://www.bcg.com/publications
    Main domain PDFs work; CDN (web-assets.bcg.com) is robots-disallowed.
    We only follow links that stay on bcg.com.
    """
    log.info("=== BCG ===")
    base = "https://www.bcg.com"
    index = f"{base}/publications"

    soup = fetch_page(index)
    if not soup:
        log.error("BCG: index page unreachable")
        return 0

    # Only collect PDFs hosted on bcg.com itself (not the blocked CDN)
    pdf_urls = [
        url for url in find_pdf_links(soup, base)
        if "bcg.com" in urlparse(url).netloc and "web-assets" not in urlparse(url).netloc
    ]
    pub_urls = list(dict.fromkeys(
        u for u in find_page_links(soup, base, "/publications/")
        if u.rstrip("/") != index.rstrip("/")
    ))

    log.info(f"BCG: {len(pdf_urls)} direct PDFs (main domain only), {len(pub_urls)} pub pages")

    collected = 0
    for url in pdf_urls[:limit]:
        if collected >= limit:
            break
        if download_pdf(url, "bcg"):
            collected += 1

    for pub_url in pub_urls:
        if collected >= limit:
            break
        pub_soup = fetch_page(pub_url)
        if not pub_soup:
            continue
        for pdf_url in find_pdf_links(pub_soup, base):
            # Strict: only bcg.com, not web-assets CDN
            if "bcg.com" in urlparse(pdf_url).netloc and "web-assets" not in urlparse(pdf_url).netloc:
                if download_pdf(pdf_url, "bcg", make_filename("bcg", pub_url)):
                    collected += 1
                    break

    if collected == 0:
        log.warning("BCG: 0 PDFs on main domain. CDN is robots-blocked. Try --seeds.")
    log.info(f"BCG: {collected} PDFs collected")
    return collected


def scrape_roland_berger(limit: int = 40) -> int:
    """
    Roland Berger — https://www.rolandberger.com/publications
    Highest priority source: landscape slide-format PDFs, high design quality.
    Crawls the publications index and each publication page for direct PDF links.
    """
    log.info("=== Roland Berger ===")
    base = "https://www.rolandberger.com"
    index_urls = [
        f"{base}/publications/",
        f"{base}/publications/?category=studies",
        f"{base}/publications/?category=trend-compendium",
    ]

    collected = 0
    visited_pdfs: set[str] = set()
    visited_pages: set[str] = set()

    for index_url in index_urls:
        if collected >= limit:
            break
        soup = fetch_page(index_url)
        if not soup:
            continue

        # Direct PDF links on index
        for pdf_url in find_pdf_links(soup, base):
            if collected >= limit:
                break
            if pdf_url in visited_pdfs:
                continue
            visited_pdfs.add(pdf_url)
            if download_pdf(pdf_url, "roland_berger"):
                collected += 1

        # Publication detail pages — look for links with /publications/ in href
        pub_links = [
            urljoin(base, a["href"].strip())
            for a in soup.find_all("a", href=True)
            if "/publications/" in a["href"] and not a["href"].strip().lower().endswith(".pdf")
        ]
        pub_links = list(dict.fromkeys(pub_links))  # deduplicate, preserve order
        log.info(f"Roland Berger {index_url}: {len(pub_links)} publication pages")

        for pub_url in pub_links:
            if collected >= limit:
                break
            if pub_url in visited_pages:
                continue
            visited_pages.add(pub_url)

            pub_soup = fetch_page(pub_url)
            if not pub_soup:
                continue

            for pdf_url in find_pdf_links(pub_soup, base):
                if pdf_url in visited_pdfs:
                    continue
                visited_pdfs.add(pdf_url)
                if download_pdf(pdf_url, "roland_berger", make_filename("roland_berger", pub_url)):
                    collected += 1
                    break  # one PDF per publication page

    # Sitemap fallback — Roland Berger sitemap often lists PDFs directly
    if collected < limit // 2:
        log.info("Roland Berger: trying sitemap fallback")
        extra = scrape_via_sitemap(base, "roland_berger", limit - collected)
        collected += extra

    if collected == 0:
        log.warning("Roland Berger: 0 PDFs from scraper — run with --seeds to use curated URLs.")
    log.info(f"Roland Berger: {collected} PDFs collected")
    return collected


def scrape_mckinsey_mgi(limit: int = 20) -> int:
    """
    McKinsey Global Institute — https://www.mckinsey.com/mgi/research
    MGI reports are slide-format landscape PDFs (unlike the main McKinsey site which is React-heavy).
    Also tries the featured-insights section which has more static PDF links.
    """
    log.info("=== McKinsey Global Institute ===")
    base = "https://www.mckinsey.com"
    collected = 0
    visited: set[str] = set()

    mgi_pages = [
        f"{base}/mgi/research",
        f"{base}/mgi/overview",
        f"{base}/featured-insights/mckinsey-global-institute",
    ]

    for page_url in mgi_pages:
        if collected >= limit:
            break
        soup = fetch_page(page_url, timeout=25)
        if not soup:
            continue

        # Direct PDFs
        for pdf_url in find_pdf_links(soup, base):
            if collected >= limit:
                break
            if pdf_url not in visited:
                visited.add(pdf_url)
                if download_pdf(pdf_url, "mckinsey"):
                    collected += 1

        # Report detail pages
        report_links = [
            urljoin(base, a["href"].strip())
            for a in soup.find_all("a", href=True)
            if ("/mgi/" in a["href"] or "/featured-insights/" in a["href"])
            and not a["href"].strip().lower().endswith(".pdf")
        ]
        report_links = list(dict.fromkeys(report_links))
        log.info(f"McKinsey MGI {page_url.split('/')[-1]}: {len(report_links)} report pages")

        for report_url in report_links[:20]:
            if collected >= limit:
                break
            report_soup = fetch_page(report_url, timeout=25)
            if not report_soup:
                continue
            for pdf_url in find_pdf_links(report_soup, base):
                if pdf_url not in visited:
                    visited.add(pdf_url)
                    if download_pdf(pdf_url, "mckinsey", make_filename("mckinsey", report_url)):
                        collected += 1
                        break

    log.info(f"McKinsey MGI: {collected} PDFs collected")
    return collected


def scrape_mckinsey(limit: int = 15) -> int:
    """
    McKinsey — tries sitemap.xml for PDF locs, then falls back to index page.
    Fully React-rendered index; sitemap is the most reliable static route.
    """
    log.info("=== McKinsey ===")
    base = "https://www.mckinsey.com"
    collected = 0
    visited: set[str] = set()

    sitemap_url = f"{base}/sitemap.xml"
    if is_allowed(sitemap_url):
        try:
            time.sleep(DELAY)
            resp = session.get(sitemap_url, timeout=20)
            resp.raise_for_status()
            sitemap_soup = BeautifulSoup(resp.text, "xml")
            pdf_locs = [
                loc.text for loc in sitemap_soup.find_all("loc")
                if ".pdf" in loc.text.lower()
            ]
            log.info(f"McKinsey sitemap: {len(pdf_locs)} PDF URLs")
            for url in pdf_locs[:limit]:
                if collected >= limit:
                    break
                if url not in visited:
                    visited.add(url)
                    if download_pdf(url, "mckinsey"):
                        collected += 1
        except Exception as e:
            log.error(f"McKinsey sitemap error: {e}")

    if collected < limit:
        index = f"{base}/featured-insights"
        soup = fetch_page(index, timeout=20)
        if soup:
            for pdf_url in find_pdf_links(soup, base):
                if collected >= limit:
                    break
                if pdf_url not in visited:
                    visited.add(pdf_url)
                    if download_pdf(pdf_url, "mckinsey"):
                        collected += 1

            for insight_url in find_page_links(soup, base, "/featured-insights/"):
                if collected >= limit:
                    break
                insight_soup = fetch_page(insight_url, timeout=20)
                if not insight_soup:
                    continue
                for pdf_url in find_pdf_links(insight_soup, base):
                    if pdf_url not in visited:
                        visited.add(pdf_url)
                        if download_pdf(pdf_url, "mckinsey", make_filename("mckinsey", insight_url)):
                            collected += 1
                            break

    if collected == 0:
        log.warning(
            "McKinsey: 0 PDFs. Site is React-rendered and sitemap had no PDFs. "
            "Run with --seeds for curated alternatives."
        )
    log.info(f"McKinsey: {collected} PDFs collected")
    return collected


def scrape_wef(limit: int = 20) -> int:
    """
    WEF Reports — https://www.weforum.org/reports/
    Most static-friendly of the consulting sources; direct PDF hrefs common.
    """
    log.info("=== World Economic Forum ===")
    base = "https://www.weforum.org"
    index = f"{base}/reports/"

    soup = fetch_page(index)
    if not soup:
        log.error("WEF: index page unreachable")
        return 0

    pdf_urls = find_pdf_links(soup, base)
    report_urls = list(dict.fromkeys(
        u for u in find_page_links(soup, base, "/reports/")
        if u.rstrip("/") != index.rstrip("/")
    ))

    log.info(f"WEF: {len(pdf_urls)} direct PDFs, {len(report_urls)} report pages")

    collected = 0
    visited: set[str] = set()

    for url in pdf_urls:
        if collected >= limit:
            break
        if url not in visited:
            visited.add(url)
            if download_pdf(url, "wef"):
                collected += 1

    for report_url in report_urls:
        if collected >= limit:
            break
        report_soup = fetch_page(report_url)
        if not report_soup:
            continue
        for pdf_url in find_pdf_links(report_soup, base):
            if pdf_url not in visited:
                visited.add(pdf_url)
                if download_pdf(pdf_url, "wef", make_filename("wef", report_url)):
                    collected += 1
                    break

    log.info(f"WEF: {collected} PDFs collected")
    return collected


def scrape_bain(limit: int = 50) -> int:
    """Bain & Company — landscape reports, briefs, and industry decks."""
    log.info("=== Bain & Company ===")
    base = "https://www.bain.com"

    # Seed pages known to host landscape 16:9 PDF decks
    seed_pages = [
        f"{base}/insights/",
        f"{base}/insights/topics/technology/",
        f"{base}/insights/topics/private-equity/",
        f"{base}/insights/topics/consumer-products/",
        f"{base}/insights/topics/financial-services/",
        f"{base}/insights/topics/retail/",
        f"{base}/insights/topics/telecommunications/",
        f"{base}/insights/topics/media-entertainment/",
        f"{base}/insights/topics/healthcare/",
        f"{base}/insights/topics/sustainability/",
        f"{base}/insights/operations/global-private-equity-report/",
        f"{base}/insights/topics/digital-transformation/",
        f"{base}/insights/topics/customer-strategy-and-marketing/",
        f"{base}/insights/topics/strategy/",
    ]

    collected = 0
    visited: set[str] = set()

    for index in seed_pages:
        if collected >= limit:
            break
        soup = fetch_page(index)
        if not soup:
            continue

        pdf_urls = find_pdf_links(soup, base)
        insight_urls = list(dict.fromkeys(
            u for u in find_page_links(soup, base, "/insights/")
            if u.rstrip("/") != index.rstrip("/")
        ))

        for url in pdf_urls:
            if collected >= limit:
                break
            if url not in visited:
                visited.add(url)
                if download_pdf(url, "bain"):
                    collected += 1

        for insight_url in insight_urls:
            if collected >= limit:
                break
            insight_soup = fetch_page(insight_url)
            if not insight_soup:
                continue
            for pdf_url in find_pdf_links(insight_soup, base):
                if pdf_url not in visited:
                    visited.add(pdf_url)
                    if download_pdf(pdf_url, "bain", make_filename("bain", insight_url)):
                        collected += 1
                        break

    if collected == 0:
        log.warning("Bain: 0 PDFs - likely JS-rendered. Try --seeds.")
    log.info(f"Bain: {collected} PDFs collected")
    return collected


def scrape_lek(limit: int = 30) -> int:
    """L.E.K. Consulting — https://www.lek.com/insights"""
    log.info("=== L.E.K. Consulting ===")
    base = "https://www.lek.com"

    seed_pages = [
        f"{base}/insights",
        f"{base}/insights/publications",
        f"{base}/insights/case-studies",
        f"{base}/insights/publications/white-papers",
        f"{base}/insights/publications/reports",
    ]

    collected = 0
    visited: set[str] = set()

    for index in seed_pages:
        if collected >= limit:
            break
        soup = fetch_page(index)
        if not soup:
            continue

        pdf_urls = find_pdf_links(soup, base)
        page_urls = list(dict.fromkeys(
            u for u in find_page_links(soup, base, "/insights/")
            if u.rstrip("/") != index.rstrip("/")
        ))

        for url in pdf_urls:
            if collected >= limit:
                break
            if url not in visited:
                visited.add(url)
                if download_pdf(url, "lek"):
                    collected += 1

        for page_url in page_urls:
            if collected >= limit:
                break
            page_soup = fetch_page(page_url)
            if not page_soup:
                continue
            for pdf_url in find_pdf_links(page_soup, base):
                if pdf_url not in visited:
                    visited.add(pdf_url)
                    if download_pdf(pdf_url, "lek", make_filename("lek", page_url)):
                        collected += 1
                        break

    if collected == 0:
        log.warning("L.E.K.: 0 PDFs found. Site may require JS or auth.")
    log.info(f"L.E.K.: {collected} PDFs collected")
    return collected


def scrape_deloitte(limit: int = 15) -> int:
    """Deloitte Insights — https://www2.deloitte.com/us/en/insights.html"""
    log.info("=== Deloitte Insights ===")
    base = "https://www2.deloitte.com"
    index = f"{base}/us/en/insights.html"

    soup = fetch_page(index)
    if not soup:
        log.error("Deloitte: index page unreachable")
        return 0

    pdf_urls = find_pdf_links(soup, base)
    insight_urls = list(dict.fromkeys(
        u for u in find_page_links(soup, base, "/insights/")
        if u.rstrip("/") != index.rstrip("/")
    ))

    log.info(f"Deloitte: {len(pdf_urls)} direct PDFs, {len(insight_urls)} insight pages")

    collected = 0
    visited: set[str] = set()

    for url in pdf_urls:
        if collected >= limit:
            break
        if url not in visited:
            visited.add(url)
            if download_pdf(url, "deloitte"):
                collected += 1

    for insight_url in insight_urls:
        if collected >= limit:
            break
        insight_soup = fetch_page(insight_url)
        if not insight_soup:
            continue
        for pdf_url in find_pdf_links(insight_soup, base):
            if pdf_url not in visited:
                visited.add(pdf_url)
                if download_pdf(pdf_url, "deloitte", make_filename("deloitte", insight_url)):
                    collected += 1
                    break

    log.info(f"Deloitte: {collected} PDFs collected")
    return collected


# ─── New high-quality landscape sources ──────────────────────────────────────

def scrape_ey(limit: int = 25) -> int:
    """
    EY (Ernst & Young) — ey.com/en_gl/insights
    Sector reports (Technology, Financial Services, Consumer) are landscape slide decks.
    Crawls the insights index and follows report detail pages for direct PDF hrefs.
    """
    log.info("=== EY ===")
    base = "https://www.ey.com"
    index_pages = [
        f"{base}/en_gl/insights",
        f"{base}/en_gl/industries/technology",
        f"{base}/en_gl/industries/financial-services",
        f"{base}/en_gl/consulting",
    ]
    collected = 0
    visited: set[str] = set()

    for index_url in index_pages:
        if collected >= limit:
            break
        soup = fetch_page(index_url)
        if not soup:
            continue
        for pdf_url in find_pdf_links(soup, base):
            if collected >= limit:
                break
            if pdf_url not in visited:
                visited.add(pdf_url)
                if download_pdf(pdf_url, "ey"):
                    collected += 1
        insight_urls = list(dict.fromkeys(
            u for u in find_page_links(soup, base, "/insights/")
            if u.rstrip("/") != index_url.rstrip("/")
        ))
        log.info(f"EY {index_url.split('/')[-1]}: {len(insight_urls)} insight pages")
        for insight_url in insight_urls[:25]:
            if collected >= limit:
                break
            insight_soup = fetch_page(insight_url)
            if not insight_soup:
                continue
            for pdf_url in find_pdf_links(insight_soup, base):
                if pdf_url not in visited:
                    visited.add(pdf_url)
                    if download_pdf(pdf_url, "ey", make_filename("ey", insight_url)):
                        collected += 1
                        break

    if collected == 0:
        log.warning("EY: 0 PDFs — site may be JS-rendered.")
    log.info(f"EY: {collected} PDFs collected")
    return collected


def _capgemini_pdf_urls(soup: BeautifulSoup | None, raw_html: str = "") -> list[str]:
    """
    Capgemini PDFs live at wp-content/uploads/... but are often revealed only
    after form submission. We scan both anchor hrefs AND raw HTML for the pattern.
    """
    import re as _re
    found: list[str] = []
    base = "https://www.capgemini.com"
    if soup:
        found += [
            urljoin(base, a["href"])
            for a in soup.find_all("a", href=True)
            if ".pdf" in a["href"].lower()
        ]
    # Scan raw HTML for wp-content PDF paths (catches JS-injected URLs)
    for m in _re.finditer(r'["\'](/wp-content/uploads/[^"\']+\.pdf)["\']', raw_html, _re.IGNORECASE):
        found.append(urljoin(base, m.group(1)))
    return list(dict.fromkeys(found))


def scrape_capgemini(limit: int = 25) -> int:
    """
    Capgemini Research Institute — capgemini.com/insights/research-library/
    High-quality landscape reports on AI, digital transformation, sustainability.
    PDFs at wp-content/uploads/ are often JS-injected; we scan raw HTML too.
    """
    log.info("=== Capgemini Research Institute ===")
    base = "https://www.capgemini.com"
    index_pages = [
        f"{base}/insights/research-library/",
        f"{base}/insights/research-library/?type=report",
    ]
    collected = 0
    visited: set[str] = set()

    for index_url in index_pages:
        if collected >= limit:
            break
        try:
            time.sleep(DELAY)
            resp = session.get(index_url, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            raw = resp.text
        except Exception as e:
            log.error(f"Capgemini index fetch failed: {e}")
            continue

        for pdf_url in _capgemini_pdf_urls(soup, raw):
            if collected >= limit:
                break
            if pdf_url not in visited:
                visited.add(pdf_url)
                if download_pdf(pdf_url, "capgemini"):
                    collected += 1

        report_urls = list(dict.fromkeys(
            u for u in find_page_links(soup, base, "/insights/research-library/")
            if u.rstrip("/") != index_url.rstrip("/")
        ))
        log.info(f"Capgemini {index_url.split('/')[-2]}: {len(report_urls)} report pages")
        for report_url in report_urls[:30]:
            if collected >= limit:
                break
            try:
                time.sleep(DELAY)
                r = session.get(report_url, timeout=20)
                r.raise_for_status()
                rsoup = BeautifulSoup(r.text, "html.parser")
                rraw = r.text
            except Exception:
                continue
            for pdf_url in _capgemini_pdf_urls(rsoup, rraw):
                if pdf_url not in visited:
                    visited.add(pdf_url)
                    if download_pdf(pdf_url, "capgemini", make_filename("capgemini", report_url)):
                        collected += 1
                        break

    if collected == 0:
        log.warning("Capgemini: 0 PDFs — PDFs may require form submission.")
    log.info(f"Capgemini: {collected} PDFs collected")
    return collected


def scrape_edelman(limit: int = 10) -> int:
    """
    Edelman — edelman.com/research
    The annual Trust Barometer and sector trust reports are landscape slide decks.
    Well-structured HTML with direct PDF download links.
    """
    log.info("=== Edelman ===")
    base = "https://www.edelman.com"
    index_pages = [
        f"{base}/research",
        f"{base}/trust/2025/trust-barometer",
        f"{base}/trust/2024/trust-barometer",
    ]
    collected = 0
    visited: set[str] = set()

    for index_url in index_pages:
        if collected >= limit:
            break
        soup = fetch_page(index_url)
        if not soup:
            continue
        for pdf_url in find_pdf_links(soup, base):
            if collected >= limit:
                break
            if pdf_url not in visited:
                visited.add(pdf_url)
                if download_pdf(pdf_url, "edelman"):
                    collected += 1
        report_urls = list(dict.fromkeys(
            u for u in find_page_links(soup, base, "/research")
            if u.rstrip("/") != index_url.rstrip("/")
        ))
        for report_url in report_urls[:15]:
            if collected >= limit:
                break
            report_soup = fetch_page(report_url)
            if not report_soup:
                continue
            for pdf_url in find_pdf_links(report_soup, base):
                if pdf_url not in visited:
                    visited.add(pdf_url)
                    if download_pdf(pdf_url, "edelman", make_filename("edelman", report_url)):
                        collected += 1
                        break

    log.info(f"Edelman: {collected} PDFs collected")
    return collected


def scrape_kpmg(limit: int = 25) -> int:
    """
    KPMG — kpmg.com insights and reports.
    Technology, financial services and ESG reports use landscape slide format.
    """
    log.info("=== KPMG ===")
    base = "https://kpmg.com"
    index_pages = [
        f"{base}/xx/en/home/insights.html",
        f"{base}/us/en/home/insights.html",
        f"{base}/xx/en/home/industries/technology.html",
        f"{base}/xx/en/home/insights/2024/01/global-tech-report.html",
    ]
    collected = 0
    visited: set[str] = set()

    for index_url in index_pages:
        if collected >= limit:
            break
        soup = fetch_page(index_url)
        if not soup:
            continue
        for pdf_url in find_pdf_links(soup, base):
            if collected >= limit:
                break
            if pdf_url not in visited:
                visited.add(pdf_url)
                if download_pdf(pdf_url, "kpmg"):
                    collected += 1
        insight_urls = list(dict.fromkeys(
            u for u in find_page_links(soup, base, "/insights/")
            if u.rstrip("/") != index_url.rstrip("/")
        ))
        for insight_url in insight_urls[:20]:
            if collected >= limit:
                break
            insight_soup = fetch_page(insight_url)
            if not insight_soup:
                continue
            for pdf_url in find_pdf_links(insight_soup, base):
                if pdf_url not in visited:
                    visited.add(pdf_url)
                    if download_pdf(pdf_url, "kpmg", make_filename("kpmg", insight_url)):
                        collected += 1
                        break

    log.info(f"KPMG: {collected} PDFs collected")
    return collected


def scrape_strategy_and(limit: int = 20) -> int:
    """
    Strategy& (PwC's strategy consulting arm) — strategyand.pwc.com
    Publishes landscape slide-style industry studies and CEO surveys.
    """
    log.info("=== Strategy& ===")
    base = "https://www.strategyand.pwc.com"
    index_pages = [
        f"{base}/gx/en/insights.html",
        f"{base}/gx/en/industries.html",
        f"{base}/us/en/industries.html",
    ]
    collected = 0
    visited: set[str] = set()

    for index_url in index_pages:
        if collected >= limit:
            break
        soup = fetch_page(index_url)
        if not soup:
            continue
        for pdf_url in find_pdf_links(soup, base):
            if collected >= limit:
                break
            if pdf_url not in visited:
                visited.add(pdf_url)
                if download_pdf(pdf_url, "strategy_and"):
                    collected += 1
        insight_urls = list(dict.fromkeys(
            u for u in find_page_links(soup, base, "/insights/")
            if u.rstrip("/") != index_url.rstrip("/")
        ))
        for insight_url in insight_urls[:20]:
            if collected >= limit:
                break
            s = fetch_page(insight_url)
            if not s:
                continue
            for pdf_url in find_pdf_links(s, base):
                if pdf_url not in visited:
                    visited.add(pdf_url)
                    if download_pdf(pdf_url, "strategy_and", make_filename("strategy_and", insight_url)):
                        collected += 1
                        break

    log.info(f"Strategy&: {collected} PDFs collected")
    return collected



# ─── Sitemap fallback ────────────────────────────────────────────────────────

def scrape_via_sitemap(domain: str, company: str, limit: int) -> int:
    sitemap_url = f"{domain}/sitemap.xml"
    if not is_allowed(sitemap_url):
        return 0
    try:
        time.sleep(DELAY)
        resp = session.get(sitemap_url, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "xml")
        pdf_locs = [loc.text for loc in soup.find_all("loc") if ".pdf" in loc.text.lower()]
    except Exception as e:
        log.error(f"Sitemap error {domain}: {e}")
        return 0

    log.info(f"Sitemap {domain}: {len(pdf_locs)} PDF URLs found")
    collected = 0
    for url in pdf_locs[:limit]:
        if collected >= limit:
            break
        if download_pdf(url, company):
            collected += 1
    return collected


# ─── Seeds fallback ──────────────────────────────────────────────────────────

def download_seeds() -> int:
    """Download the curated SEED_PDFS list (company, url, explicit_filename_or_None)."""
    log.info("=== Seeds (curated direct URLs) ===")
    collected = 0
    for entry in tqdm(SEED_PDFS, desc="Seeds", leave=False):
        company, url = entry[0], entry[1]
        explicit_name = entry[2] if len(entry) > 2 else None
        if download_pdf(url, company, filename=explicit_name):
            collected += 1
    log.info(f"Seeds: {collected} PDFs collected")
    return collected


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Consulting PDF scraper")
    parser.add_argument("--sitemap", action="store_true",
                        help="Also try sitemap.xml for JS-heavy sources")
    parser.add_argument("--seeds", action="store_true",
                        help="Download curated seed PDFs (fastest path to 100 slides)")
    parser.add_argument("--seeds-only", action="store_true",
                        help="Only download seed PDFs, skip all scrapers")
    parser.add_argument("--rb-only", action="store_true",
                        help="Only scrape Roland Berger (highest priority source)")
    parser.add_argument("--mgi-only", action="store_true",
                        help="Only scrape McKinsey Global Institute")
    parser.add_argument("--new-sources", action="store_true",
                        help="Only scrape new sources: EY, Capgemini, Edelman, KPMG, Strategy&")
    args = parser.parse_args()

    if args.seeds_only:
        n = download_seeds()
        print(f"\nSeeds downloaded: {n}")
        return

    if args.rb_only:
        n = scrape_roland_berger(limit=60)
        print(f"\nRoland Berger PDFs downloaded: {n}")
        return

    if args.mgi_only:
        n = scrape_mckinsey_mgi(limit=40)
        print(f"\nMcKinsey MGI PDFs downloaded: {n}")
        return

    if args.new_sources:
        new_scrapers = [
            ("Bain",         scrape_bain,          50),
            ("L.E.K.",       scrape_lek,           30),
            ("EY",           scrape_ey,            25),
            ("Capgemini",    scrape_capgemini,      25),
            ("Edelman",      scrape_edelman,        10),
            ("KPMG",         scrape_kpmg,           25),
            ("Strategy&",    scrape_strategy_and,   20),
        ]
        results: dict[str, int] = {}
        for name, fn, lim in tqdm(new_scrapers, desc="New sources", position=0):
            results[name] = fn(lim)
        print("\nNew sources results:")
        for name, n in results.items():
            print(f"  {name}: {n} PDFs")
        return

    # Full run — priority order (Bain and L.E.K. first per brief)
    scrapers = [
        ("Bain",          scrape_bain,           50),
        ("L.E.K.",        scrape_lek,            30),
        ("Roland Berger", scrape_roland_berger,  40),
        ("McKinsey MGI",  scrape_mckinsey_mgi,   20),
        ("EY",            scrape_ey,             25),
        ("Capgemini",     scrape_capgemini,      25),
        ("Edelman",       scrape_edelman,        10),
        ("KPMG",          scrape_kpmg,           25),
        ("Strategy&",     scrape_strategy_and,   20),
        ("World Bank",    scrape_world_bank,     25),
        ("ADB",           scrape_adb,            20),
        ("BCG",           scrape_bcg,            15),
        ("McKinsey",      scrape_mckinsey,       15),
        ("WEF",           scrape_wef,            20),
        ("Deloitte",      scrape_deloitte,       15),
    ]

    results: dict[str, int] = {}
    for name, fn, lim in tqdm(scrapers, desc="Sources", position=0):
        results[name] = fn(lim)

    if args.sitemap:
        sitemap_sources = [
            ("https://www.bcg.com",        "bcg",      15),
            ("https://www.mckinsey.com",   "mckinsey", 15),
            ("https://www.bain.com",       "bain",     15),
            ("https://www2.deloitte.com",  "deloitte", 15),
        ]
        for domain, company, lim in sitemap_sources:
            extra = scrape_via_sitemap(domain, company, lim)
            results[company.upper()] = results.get(company.upper(), 0) + extra

    if args.seeds:
        results["Seeds"] = download_seeds()

    # Auto-trigger seeds if total is low
    total = sum(results.values())
    if total < 20 and not args.seeds and not args.seeds_only:
        log.warning(f"Only {total} PDFs collected from scrapers - auto-running seeds.")
        results["Seeds (auto)"] = download_seeds()
        total = sum(results.values())

    print("\n=== Scraping Summary ===")
    for source, count in results.items():
        flag = "  (try --sitemap or --seeds)" if count == 0 else ""
        print(f"  {source:<22} {count} PDFs{flag}")
    print(f"  {'TOTAL':<22} {sum(results.values())} PDFs")
    print(f"\nPDFs saved to: {PDFS_DIR}")
    print(f"Full log:      {BASE_DIR / 'scraper.log'}")

    total = sum(results.values())
    if total < 10:
        print(
            "\nVery few PDFs. Fastest path to 100+ slides:\n"
            "  python scraper.py --seeds\n"
            "  python run_pipeline.py --skip-scrape  (after manually dropping PDFs into /pdfs/)"
        )


if __name__ == "__main__":
    main()

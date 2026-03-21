#!/usr/bin/env python3
"""
============================================================
NAUKRI DHABA - SARKARIRESULT.COM SCRAPER
File: scraper/sarkari_scraper.py
============================================================

Scrapes sarkariresult.com daily and generates HTML pages
for Naukri Dhaba — replacing all SarkariResult branding
with Naukri Dhaba.

SOURCES:
  Homepage  : https://www.sarkariresult.com
  Jobs      : https://www.sarkariresult.com/latestjob.php
  Results   : https://www.sarkariresult.com/result.php
  Admit Cards: https://www.sarkariresult.com/admitcard.php

SCHEDULE:
  Runs daily at 10:00 AM IST (04:30 UTC) via cron.
  See scraper/setup_cron.sh to install the cron job.

MANUAL RUN:
  python3 scraper/sarkari_scraper.py

LOGS:
  scraper/logs/scraper.log

============================================================
"""

import os
import re
import sys
import json
import time
import logging
import hashlib
import argparse
from datetime import datetime, date
from html import escape
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse, parse_qs

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ─── Check dependencies ────────────────────────────────────
try:
    import requests
    from bs4 import BeautifulSoup, Tag
except ImportError:
    print("Missing dependencies. Installing...")
    os.system(f"{sys.executable} -m pip install requests beautifulsoup4 lxml -q")
    import requests
    from bs4 import BeautifulSoup, Tag

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

from site_config import REDIRECT_PATH, SITE_NAME, SITE_URL, SOURCE_BASE_URL, SOURCE_HOSTS, SOURCES, STAGING_DIR

# ══════════════════════════════════════════════════════════
# PATHS & CONSTANTS
# ══════════════════════════════════════════════════════════
SITE_ROOT   = Path(__file__).parent.parent
SCRAPER_DIR = Path(__file__).parent
LOG_DIR     = SCRAPER_DIR / 'logs'
SEEN_FILE   = SCRAPER_DIR / 'seen_items.json'
TRACKING_CONFIG_FILE = SITE_ROOT / 'tracking-config.json'

LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_DIR / 'scraper.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger('NaukriDhaba')

# ── Source site ────────────────────────────────────────────
BASE          = SOURCE_BASE_URL
URL_JOBS      = f'{BASE}/latestjob.php'
URL_RESULTS   = f'{BASE}/result.php'
URL_ADMITS    = f'{BASE}/admitcard.php'
URL_HOME      = BASE

# ── Our site ───────────────────────────────────────────────

# ── Request settings ───────────────────────────────────────
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': BASE,
    'Connection': 'keep-alive',
}
DELAY   = 2.5   # seconds between requests (polite)
TIMEOUT = 20

# ── Department → category folder mapping ──────────────────
DEPT_MAP = {
    'UPSC': 'upsc', 'IAS': 'upsc', 'IPS': 'upsc', 'IFS': 'upsc',
    'SSC': 'ssc', 'CHSL': 'ssc', 'CGL': 'ssc', 'MTS': 'ssc',
    'UPSSSC': 'ssc', 'BSSC': 'ssc', 'JSSC': 'ssc', 'HSSC': 'ssc',
    'RRB': 'railway', 'RRC': 'railway', 'RAILWAY': 'railway',
    'IBPS': 'banking', 'SBI': 'banking', 'RBI': 'banking',
    'NABARD': 'banking', 'BANK': 'banking', 'IDBI': 'banking',
    'POLICE': 'police', 'CISF': 'police', 'BSF': 'police',
    'CRPF': 'police', 'ITBP': 'police', 'SSB': 'police',
    'ARMY': 'defence', 'NAVY': 'defence', 'AIRFORCE': 'defence',
    'IAF': 'defence', 'NDA': 'defence', 'CDS': 'defence',
    'DRDO': 'defence', 'HAL': 'defence',
    'NTA': 'government', 'CBSE': 'government', 'CISCE': 'government',
    'JEEMAIN': 'government', 'NEET': 'government', 'CUET': 'government',
    'UGC': 'government', 'GATE': 'government',
    'BIHAR BOARD': 'government', 'UP BOARD': 'government',
    'MPBSE': 'government', 'RSSB': 'government', 'NVS': 'government',
    'MPPSC': 'government', 'JPSC': 'government', 'PPSC': 'government',
    'LIC': 'government', 'AFCAT': 'government',
}

# ── SEO keyword map by dept category ──────────────────────
SEO_KW = {
    'upsc':     'UPSC, Civil Services, IAS, IPS, IFS, Union Public Service Commission',
    'ssc':      'SSC, Staff Selection Commission, CGL, CHSL, MTS, GD Constable',
    'railway':  'Railway Jobs, RRB, NTPC, Group D, ALP, Loco Pilot, Indian Railways',
    'banking':  'Bank Jobs, IBPS, SBI, RBI, PO, Clerk, Banking Vacancy',
    'police':   'Police Jobs, Constable, SI, Sub Inspector, CRPF, BSF, CISF',
    'defence':  'Defence Jobs, Army, Navy, Air Force, NDA, CDS, Agniveer',
    'government': 'Government jobs India, online form updates, result updates, admit card updates, Naukri Dhaba',
}

# ── Official government portals per board / exam body ─────
# Used as a fallback when no specific apply/result/admit URL is extracted from source pages.
# Order matters: more-specific keys first, so 'UPSSSC' matches before 'SSC'.
BOARD_PORTALS: dict[str, str] = {
    # ── Public Service Commissions ──
    'UPSSSC':  'https://upsssc.gov.in',
    'UPSC':    'https://upsc.gov.in',
    'SSC':     'https://ssc.nic.in',
    'BPSC':    'https://bpsc.bih.nic.in',
    'UPPSC':   'https://uppsc.up.nic.in',
    'MPPSC':   'https://mppsc.mp.gov.in',
    'RPSC':    'https://rpsc.rajasthan.gov.in',
    'JPSC':    'https://www.jpsc.gov.in',
    'HSSC':    'https://hssc.gov.in',
    'HPSC':    'https://hpsc.gov.in',
    'JSSC':    'https://jssc.nic.in',
    'PPSC':    'https://ppsc.gov.in',
    # ── Banking / Finance ──
    'SBI':     'https://sbi.co.in/careers',
    'IBPS':    'https://www.ibps.in',
    'RBI':     'https://www.rbi.org.in/Scripts/Vacancies.aspx',
    'NABARD':  'https://www.nabard.org/career.aspx',
    'LIC':     'https://licindia.in/Bottom-Links/Recruitment',
    'ECGC':    'https://www.ecgc.in',
    # ── Railways ──
    'RRB':     'https://www.rrbcdg.gov.in',
    'RRC':     'https://www.rrcb.gov.in',
    # ── Defence / Police ──
    'DRDO':    'https://www.drdo.gov.in/careers',
    'CISF':    'https://cisfrectt.in',
    'BSF':     'https://bsf.gov.in/recruitment.html',
    'CRPF':    'https://www.crpf.gov.in/Recruitment.htm',
    'AFCAT':   'https://afcat.cdac.in',
    'HAL':     'https://hal-india.co.in/Career',
    'ARMY':    'https://joinindianarmy.nic.in',
    'NAVY':    'https://www.joinindiannavy.gov.in',
    'IAF':     'https://airmenselection.cdac.in',
    'NDA':     'https://upsc.gov.in',
    'CDS':     'https://upsc.gov.in',
    'ASSAM RIFLES': 'https://assamrifles.gov.in',
    'DGAFMS':  'https://dgafms.gov.in',
    'MHA':     'https://www.mha.gov.in',
    # ── Education boards ──
    'CBSE':    'https://www.cbse.gov.in',
    'CISCE':   'https://www.cisce.org',
    'ICSE':    'https://www.cisce.org',
    'BSEB':    'https://biharboardonline.bihar.gov.in',
    'BIHAR BOARD': 'https://biharboardonline.bihar.gov.in',
    'BSEH':    'https://bseh.org.in',
    'HARYANA BOARD': 'https://bseh.org.in',
    'HBSE':    'https://bseh.org.in',
    'CGBSE':   'https://cgbse.nic.in',
    'CHHATTISGARH BOARD': 'https://cgbse.nic.in',
    'JAC':     'https://jac.jharkhand.gov.in',
    'JHARKHAND BOARD': 'https://jac.jharkhand.gov.in',
    'MAHARASHTRA BOARD': 'https://mahahsscboard.in',
    'MP BOARD': 'https://mpbse.nic.in',
    'MPBSE':   'https://mpbse.nic.in',
    'RAJASTHAN BOARD': 'https://rajeduboard.rajasthan.gov.in',
    'RBSE':    'https://rajeduboard.rajasthan.gov.in',
    'UP BOARD': 'https://upmsp.edu.in',
    'UPMSP':   'https://upmsp.edu.in',
    'UTTARAKHAND BOARD': 'https://ubse.uk.gov.in',
    'UBSE':    'https://ubse.uk.gov.in',
    'UP MADARSA': 'https://madarsaboard.upsdc.gov.in',
    # ── NTA exams ──
    'NTA':     'https://nta.ac.in',
    'CUET':    'https://cuet.nta.nic.in',
    'JEE':     'https://jeemain.nta.ac.in',
    'NEET':    'https://neet.nta.nic.in',
    'GATE':    'https://gate2025.iitr.ac.in',
    'GPAT':    'https://gpat.nta.nic.in',
    'CTET':    'https://ctet.nic.in',
    'CLAT':    'https://consortiumofnlus.ac.in',
    'IIT JAM': 'https://jam.iitb.ac.in',
    'NCHMJEE': 'https://nchmjee.nta.nic.in',
    'NTET':    'https://nta.ac.in',
    # ── Universities / Institutions ──
    'AIIMS':   'https://aiimsexams.ac.in',
    'NORCET':  'https://aiimsexams.ac.in',
    'BHU':     'https://www.bhu.ac.in',
    'ALLAHABAD UNIVERSITY': 'https://www.allduniv.ac.in',
    'CIPET':   'https://www.cipet.gov.in',
    'DUVASU':  'https://www.duvasu.org',
    'IERT':    'https://iert.ac.in',
    'UPBED':   'https://www.lkouniv.ac.in',
    'UP CNET': 'https://www.lkouniv.ac.in',
    'UP CPET': 'https://www.lkouniv.ac.in',
    'UPCATET': 'https://upcatet.org',
    'JEECUP':  'https://jeecup.admissions.nic.in',
    'UP POLYTECHNIC': 'https://jeecup.admissions.nic.in',
    'UP GNM':  'https://upsmfac.org',
    'UPGET':   'https://upsmfac.org',
    'UP RTE':  'https://rte25.upsdc.gov.in',
    # ── Autonomous bodies ──
    'NVS':     'https://navodaya.gov.in/nvs/en/Recruitment',
    'KVS':     'https://kvsangathan.nic.in',
    'EMRS':    'https://emrs.tribal.gov.in',
    'INDIA POST': 'https://indiapostgdsonline.gov.in',
    'GDS':     'https://indiapostgdsonline.gov.in',
    'IOCL':    'https://iocl.com',
    'NCL':     'https://www.nclcil.in',
    'CIL':     'https://www.coalindia.in',
    'AAI':     'https://www.aai.aero',
    # ── Courts ──
    'SUPREME COURT': 'https://main.sci.gov.in',
    'SCI':     'https://main.sci.gov.in',
    'PATNA HIGH COURT': 'https://patnahighcourt.gov.in',
    # ── State-specific ──
    'BTSC':    'https://btsc.bih.nic.in',
    'OFSS':    'https://ofssbihar.in',
    'BIHAR':   'https://bceceboard.bihar.gov.in',
    'MPESB':   'https://peb.mp.gov.in',
    'RSSB':    'https://rsmssb.rajasthan.gov.in',
    'RAJASTHAN PTET': 'https://ptetdcb.com',
    'BIHAR DELED': 'https://deledbihar.com',
    'BIHAR ITICAT': 'https://bceceboard.bihar.gov.in',
    'SWD UP':  'https://socialwelfare.up.gov.in',
    'JEE ADVANCED': 'https://jeeadv.ac.in',
    # ── CSIR labs ──
    'CSIR-CDRI': 'https://cdri.res.in',
    'CSIR CDRI': 'https://cdri.res.in',
    'CSIR-CRRI': 'https://crridom.gov.in',
    'CSIR CRRI': 'https://crridom.gov.in',
    'CSIR-IITR': 'https://iitr.res.in',
    'CSIR IITR': 'https://iitr.res.in',
    'CSIR':    'https://www.csir.res.in',
}

# Category-level fallback (less specific than BOARD_PORTALS)
OFFICIAL_PORTALS: dict[str, str] = {
    'upsc':       'https://upsc.gov.in',
    'ssc':        'https://ssc.nic.in',
    'railway':    'https://www.rrbcdg.gov.in',
    'banking':    'https://www.ibps.in',
    'police':     'https://www.crpf.gov.in/Recruitment.htm',
    'defence':    'https://joinindianarmy.nic.in',
    'government': '',
}


def official_portal_for(title: str, cat: str) -> str:
    """Return the best known official govt portal URL for this exam/dept, or ''."""
    tu = title.upper()
    for board, url in BOARD_PORTALS.items():
        if board in tu:
            return url
    return OFFICIAL_PORTALS.get(cat, '')


# ══════════════════════════════════════════════════════════
# UTILITY HELPERS
# ══════════════════════════════════════════════════════════

def slugify(text: str) -> str:
    t = str(text).lower().strip()
    t = re.sub(r'[^\w\s-]', '', t)
    t = re.sub(r'[\s_]+', '-', t)
    t = re.sub(r'-{2,}', '-', t).strip('-')
    return t[:80]


# All category folder names used for detail pages
_ALL_CATEGORIES = ('upsc', 'ssc', 'railway', 'banking', 'police', 'defence', 'government')


def remove_cross_category_duplicates(kind_dir: str, cat: str, slug: str):
    """Remove same slug from other category folders to prevent duplicates.

    When a job's category changes between runs (e.g. detail-page parsing
    returns a different dept), the old file lingers in the previous category
    folder.  This helper deletes those stale copies.
    """
    base = SITE_ROOT / kind_dir
    for other_cat in _ALL_CATEGORIES:
        if other_cat == cat:
            continue
        stale = base / other_cat / f'{slug}.html'
        if stale.exists():
            log.info(f'  [dedup] Removing stale cross-category copy: {stale.relative_to(SITE_ROOT)}')
            stale.unlink()


def clean(text: str) -> str:
    """Strip whitespace and collapse spaces."""
    if not text:
        return ''
    return re.sub(r'\s+', ' ', str(text)).strip()


def sanitize(text: str) -> str:
    """Remove/replace all SarkariResult mentions."""
    if not text:
        return ''
    text = str(text)
    text = re.sub(r'(?i)sarkari\s*results?(?:\.(?:com|org|in))?', SITE_NAME, text)
    text = re.sub(r'(?i)www\.sarkariresults?\.(?:com|org|in)', 'www.naukridhaba.in', text)
    text = re.sub(r'(?i)doc\.sarkariresults?\.org\.in', 'doc.naukridhaba.in', text)
    return text


def sanitize_url(url: str) -> str:
    """
    Preserve official govt URLs exactly.
    For sarkariresult.com URLs → replace domain with naukridhaba.in,
    keeping the full path so our pages are reachable at the same slug.
    Relative paths → resolve against naukridhaba.in.
    """
    if not url:
        return '#'
    u = url.strip()

    # Relative path from sarkariresult → prefix our domain
    if u.startswith('/'):
        return f'https://www.naukridhaba.in{u}'

    if not u.startswith('http'):
        return '#'

    # Replace sarkariresult domain, keep full path intact
    u = re.sub(
        r'(?i)https?://(?:www\.)?sarkariresults?\.(?:com|org|in)',
        'https://www.naukridhaba.in',
        u
    )
    return u


def item_id(title: str, dept: str) -> str:
    return hashlib.md5(f"{title.lower().strip()}|{dept.lower().strip()}".encode()).hexdigest()[:14]


def normalize_url(url: str, base_url: str = BASE) -> str:
    """Normalize relative links to absolute URLs without rewriting the host."""
    if not url:
        return '#'
    candidate = url.strip()
    if not candidate or candidate.startswith(('javascript:', 'mailto:', 'tel:', '#')):
        return '#'
    if candidate.startswith('/'):
        return urljoin(base_url, candidate)
    if not candidate.startswith('http'):
        return urljoin(base_url, candidate)
    return candidate


def is_public_redirect(url: str) -> bool:
    if not url or url == '#':
        return False
    candidate = url.strip()
    if candidate.startswith(REDIRECT_PATH):
        return True
    if not candidate.startswith('http'):
        return False
    parsed = urlparse(candidate)
    site_host = urlparse(SITE_URL).netloc.lower()
    return parsed.netloc.lower() == site_host and parsed.path == REDIRECT_PATH


def is_source_url(url: str) -> bool:
    if not url or url == '#':
        return False
    host = urlparse(url).netloc.lower()
    return any(host == sh or host.endswith('.' + sh) for sh in SOURCE_HOSTS)


def is_official_url(url: str) -> bool:
    if not url or url == '#':
        return False
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False
    host = parsed.netloc.lower()
    if any(host == sh or host.endswith('.' + sh) for sh in SOURCE_HOSTS) or host.endswith('naukridhaba.in'):
        return False
    return True


def build_source_redirect(url: str) -> str:
    if not url or url == '#':
        return ''
    return f'{REDIRECT_PATH}?target={quote(url, safe="")}'


def to_public_url(url: str) -> str:
    if is_public_redirect(url):
        return ''
    normalized = normalize_url(url)
    if normalized == '#':
        return ''
    if is_public_redirect(normalized):
        return ''
    official = official_url_or_empty(normalized)
    if official:
        return official
    embedded = _extract_embedded_official_url(normalized)
    if embedded:
        return embedded
    resolved = _resolve_source_redirect(normalized)
    if resolved:
        return resolved
    return ''


def _extract_embedded_official_url(url: str) -> str:
    """Extract embedded official URL from source-site redirect URLs.

    Source sites like sarkariresult.com wrap official links in redirects,
    e.g. sarkariresult.com/redirect.php?url=https://upsc.gov.in/apply.
    This function extracts the embedded target URL if it is an official site.
    """
    if not url:
        return ''
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    for param in ('url', 'target', 'redirect', 'link', 'go', 'u', 'r', 'to'):
        vals = qs.get(param, [])
        for v in vals:
            if is_official_url(v):
                return v
    return ''


# Cache for resolved redirects to avoid repeat HEAD requests
_redirect_cache: dict[str, str] = {}


def _resolve_source_redirect(url: str) -> str:
    """Follow a source-site URL (e.g. sarkariresult.com/xxx) via HEAD request
    to discover the actual official destination URL.

    Source sites wrap official links in their own redirect pages. This follows
    the redirect chain (without downloading the body) to find where it lands.
    Returns the final URL if it's an official site, else ''.
    """
    if not url or not is_source_url(url):
        return ''
    if url in _redirect_cache:
        return _redirect_cache[url]

    try:
        # Use HEAD with allow_redirects to follow the chain cheaply
        r = _session.head(url, timeout=8, allow_redirects=True, proxies=_NO_PROXY)
        final = r.url
        if final and final != url and is_official_url(final):
            _redirect_cache[url] = final
            log.info(f'  [resolve] {url[:60]}... -> {final}')
            return final
        # Some sites use JS redirects — check Location header on 3xx even if
        # allow_redirects followed them already
        if r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get('Location', '')
            if loc and is_official_url(loc):
                _redirect_cache[url] = loc
                return loc
    except Exception as exc:
        log.debug(f'  [resolve] HEAD failed for {url}: {exc}')

    # Also try GET with stream=True (some servers don't support HEAD)
    try:
        r = _session.get(url, timeout=8, allow_redirects=True, stream=True, proxies=_NO_PROXY)
        final = r.url
        r.close()
        if final and final != url and is_official_url(final):
            _redirect_cache[url] = final
            log.info(f'  [resolve] {url[:60]}... -> {final}')
            return final
    except Exception as exc:
        log.debug(f'  [resolve] GET failed for {url}: {exc}')

    _redirect_cache[url] = ''
    return ''


def primary_cta_url(url: str, source_detail_url: str) -> str:
    if is_public_redirect(url):
        return ''
    normalized = normalize_url(url)
    if is_public_redirect(normalized):
        return ''
    # 1. Direct official URL — use as-is
    official = official_url_or_empty(normalized)
    if official:
        return official
    # 2. Extract official URL from query params of source redirect
    embedded = _extract_embedded_official_url(normalized)
    if embedded:
        return embedded
    # 3. Follow the source-site redirect via HTTP to find actual destination
    resolved = _resolve_source_redirect(normalized)
    if resolved:
        return resolved
    return ''


def normalize_title(text: str) -> str:
    title = clean(sanitize(text))
    title = re.sub(rf'\s*\|\s*{re.escape(SITE_NAME)}.*$', '', title, flags=re.I)
    title = re.sub(r'\b(\d{4})\s+\1\b', r'\1', title)
    title = re.sub(r'([A-Za-z0-9])(?=(Apply Online|Result|Admit Card))', r'\1 ', title)
    title = re.sub(r'\b(20\d{2})\s+(Apply Online|Result|Admit Card)\s+\1\b', r'\1 \2', title)
    return clean(title)


def google_search_url(title: str, suffix: str = '') -> str:
    """Return a Google search URL for the given title + optional suffix."""
    q = f'{title} {suffix}'.strip() if suffix else title
    return f'https://www.google.com/search?q={quote(q)}'


def parse_display_date(text: str) -> str:
    return clean(text) or 'Check Notification'


def to_iso_date(text: str) -> str | None:
    value = clean(text)
    if not value:
        return None
    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


DATE_VALUE_RE = re.compile(
    r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|today|tomorrow|declared|released|available|schedule|soon)',
    re.I,
)
FEE_VALUE_RE = re.compile(r'(free|no application|rs\.?|inr|/-|₹|\d)', re.I)


def looks_like_date_value(text: str) -> bool:
    return bool(DATE_VALUE_RE.search(clean(text)))


def looks_like_fee_value(text: str) -> bool:
    return bool(FEE_VALUE_RE.search(clean(text)))


def first_value_cell(cells: list[Tag]) -> str:
    values = []
    for cell in cells[1:]:
        value = clean(cell.get_text(" ", strip=True))
        if value:
            values.append(value)
    return values[0] if values else ''


def official_url_or_empty(url: str) -> str:
    if is_public_redirect(url):
        return ''
    normalized = normalize_url(url)
    if is_official_url(normalized):
        return normalized
    return ''


def summary_sentence(parts: list[str]) -> str:
    return ' '.join(part for part in parts if part)


def build_job_overview(d: dict) -> str:
    title = normalize_title(d.get('title', ''))
    dept = clean(d.get('dept', 'Government'))
    posts = str(d.get('total_posts') or '').strip()
    parts = [
        f"{title} is listed under {dept} recruitment updates on {SITE_NAME}.",
        f"The current application deadline is {d.get('last_date', 'Check Notification')}.",
        f"Total advertised posts: {posts}." if posts else '',
        f"Baseline age range in the extracted notice is {d.get('age_min', 18)} to {d.get('age_max', 35)} years.",
        "Use the official notification and authority portal below to verify the latest eligibility, category relaxation, and document rules before applying.",
    ]
    bullets = [
        f"<li><strong>Department:</strong> {dept}</li>",
        f"<li><strong>Application window:</strong> {d.get('app_begin', 'Check Notification')} to {d.get('last_date', 'Check Notification')}</li>",
        f"<li><strong>Qualification:</strong> {d.get('qualification', 'Check Notification')}</li>",
        f"<li><strong>Selection context:</strong> Track updates here, but submit only on the official authority site.</li>",
    ]
    return (
        '<div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">'
        '<h3 style="color:var(--primary);margin-top:0;">Role Snapshot</h3>'
        f'<p style="line-height:1.9;color:#444;">{summary_sentence(parts)}</p>'
        f'<ul style="line-height:2;margin:0;padding-left:1.2rem;">{"".join(bullets)}</ul>'
        '</div>'
    )


def build_result_overview(d: dict) -> str:
    title = normalize_title(d.get('title', ''))
    dept = clean(d.get('dept', 'Government'))
    parts = [
        f"{title} has been added to the {SITE_NAME} result tracker for {dept}.",
        f"The extracted result update date is {d.get('result_date', 'Check Notification')}.",
        "Use the official result portal or scorecard link below to validate roll number lookup, cutoff, and final selection status.",
    ]
    bullets = [
        f"<li><strong>Authority:</strong> {dept}</li>",
        f"<li><strong>Result date:</strong> {d.get('result_date', 'Check Notification')}</li>",
        f"<li><strong>Best next step:</strong> keep your registration details ready before opening the official result portal.</li>",
    ]
    return (
        '<div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">'
        '<h3 style="color:var(--primary);margin-top:0;">Result Summary</h3>'
        f'<p style="line-height:1.9;color:#444;">{summary_sentence(parts)}</p>'
        f'<ul style="line-height:2;margin:0;padding-left:1.2rem;">{"".join(bullets)}</ul>'
        '</div>'
    )


def build_admit_overview(d: dict) -> str:
    title = normalize_title(d.get('title', ''))
    dept = clean(d.get('dept', 'Government'))
    parts = [
        f"{title} is available in the {SITE_NAME} admit-card tracker for {dept}.",
        f"The extracted release date is {d.get('admit_release', 'Check Notification')}.",
        f"The current exam schedule reference is {d.get('exam_date', 'As per Schedule')}.",
        "Verify reporting time, exam city, and document rules on the official authority page before travelling.",
    ]
    bullets = [
        f"<li><strong>Authority:</strong> {dept}</li>",
        f"<li><strong>Release date:</strong> {d.get('admit_release', 'Check Notification')}</li>",
        f"<li><strong>Exam schedule:</strong> {d.get('exam_date', 'As per Schedule')}</li>",
    ]
    return (
        '<div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">'
        '<h3 style="color:var(--primary);margin-top:0;">Exam Access Summary</h3>'
        f'<p style="line-height:1.9;color:#444;">{summary_sentence(parts)}</p>'
        f'<ul style="line-height:2;margin:0;padding-left:1.2rem;">{"".join(bullets)}</ul>'
        '</div>'
    )


def build_job_faq(d: dict) -> tuple[str, str]:
    """Return (faq_html, faq_json_ld) for a job detail page."""
    title  = normalize_title(d.get('title', ''))
    dept   = clean(d.get('dept', 'Government'))
    last_d = d.get('last_date', 'Check Notification')
    posts  = str(d.get('total_posts') or '').strip()
    age_min = d.get('age_min', 18)
    age_max = d.get('age_max', 35)
    fee_g  = d.get('fee_general', '')
    fee_s  = d.get('fee_sc_st', '')
    qual   = d.get('qualification', 'Check Notification')

    qas = [
        (
            f"What is the last date to apply for {title}?",
            f"The last date to apply for {title} is {last_d}. Candidates should submit their application before this date to avoid rejection."
        ),
        (
            f"How many vacancies are available in {title}?",
            f"{'There are ' + posts + ' total vacancies advertised under ' + title + '.' if posts else 'The total vacancy count for ' + title + ' has not been specified yet. Please check the official notification.'}"
        ),
        (
            f"What is the age limit for {title}?",
            f"The age limit for {title} is {age_min} to {age_max} years as per the official notification. Age relaxation is applicable for SC/ST/OBC/PwD candidates as per government norms."
        ),
        (
            f"What is the application fee for {title}?",
            f"{'Application fee: General/OBC/EWS — ' + fee_g + ('; SC/ST — ' + fee_s if fee_s else '') + '.' if fee_g else 'Application fee details for ' + title + ' are mentioned in the official notification. Please refer to the official site.'}"
        ),
        (
            f"What is the educational qualification required for {title}?",
            f"The required qualification for {title} is: {qual}. Please verify from the official notification as requirements may have been updated."
        ),
    ]

    html_items = '\n'.join(
        f'<div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">'
        f'<h3 itemprop="name" style="color:var(--primary);margin:0 0 .5rem;">{q}</h3>'
        f'<div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">'
        f'<p itemprop="text" style="color:#444;line-height:1.8;margin:0;">{a}</p>'
        f'</div></div>'
        for q, a in qas
    )
    faq_html = (
        '<div itemscope itemtype="https://schema.org/FAQPage" '
        'style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">'
        '<h2 style="color:var(--primary);margin-top:0;">❓ Frequently Asked Questions</h2>'
        + html_items +
        '</div>'
    )

    faq_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in qas
        ]
    }, ensure_ascii=False)
    return faq_html, faq_ld


def build_result_faq(d: dict) -> tuple[str, str]:
    """Return (faq_html, faq_json_ld) for a result detail page."""
    title   = normalize_title(d.get('title', ''))
    dept    = clean(d.get('dept', 'Government'))
    r_date  = d.get('result_date', 'Check Notification')

    date_answer = (
        f"The {title} was declared on {r_date}. Candidates can check the result using the official link provided on this page."
        if r_date not in ('Check Notification', '')
        else f"The {title} has been declared. Visit the official link on this page to check your result."
    )
    qas = [
        (
            f"When was the {title} declared?",
            date_answer
        ),
        (
            f"How can I check the {title}?",
            f"To check the {title}: (1) Click the result link on this page. (2) Enter your roll number or registration ID. (3) Verify your name, category, and marks. (4) Download the result PDF for future reference."
        ),
        (
            f"What documents are needed to check the {title}?",
            "Keep your admit card (roll number/registration number), date of birth, and application number ready before opening the result portal."
        ),
        (
            f"What should I do after checking the {title}?",
            f"After checking the {title}: (1) Download and save the result PDF. (2) If selected, await the official merit list / joining instructions from {dept}. (3) Keep all original documents ready for verification rounds."
        ),
    ]

    html_items = '\n'.join(
        f'<div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">'
        f'<h3 itemprop="name" style="color:var(--primary);margin:0 0 .5rem;">{q}</h3>'
        f'<div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">'
        f'<p itemprop="text" style="color:#444;line-height:1.8;margin:0;">{a}</p>'
        f'</div></div>'
        for q, a in qas
    )
    faq_html = (
        '<div itemscope itemtype="https://schema.org/FAQPage" '
        'style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">'
        '<h2 style="color:var(--primary);margin-top:0;">❓ Frequently Asked Questions</h2>'
        + html_items +
        '</div>'
    )

    faq_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in qas
        ]
    }, ensure_ascii=False)
    return faq_html, faq_ld


def build_admit_faq(d: dict) -> tuple[str, str]:
    """Return (faq_html, faq_json_ld) for an admit card detail page."""
    title    = normalize_title(d.get('title', ''))
    dept     = clean(d.get('dept', 'Government'))
    release  = d.get('admit_release', 'Check Notification')
    exam_dt  = d.get('exam_date', 'As per Schedule')

    qas = [
        (
            f"When was the {title} released?",
            f"The {title} was released on {release}. Download it using the official link provided on this page."
        ),
        (
            f"How to download the {title}?",
            f"To download the {title}: (1) Click the download link on this page. (2) Enter your registration number and date of birth. (3) View and download your admit card. (4) Take a colour printout for the exam."
        ),
        (
            f"What is the exam date for {title}?",
            f"The exam date for {title} is {exam_dt}. Please verify the reporting time and exam centre from your admit card."
        ),
        (
            f"What documents to carry with {title}?",
            f"Carry the printed {title} along with a valid photo ID (Aadhaar / PAN / Passport) to the exam centre. Some exams also require a passport-size photograph — check instructions on the admit card."
        ),
    ]

    html_items = '\n'.join(
        f'<div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">'
        f'<h3 itemprop="name" style="color:var(--primary);margin:0 0 .5rem;">{q}</h3>'
        f'<div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">'
        f'<p itemprop="text" style="color:#444;line-height:1.8;margin:0;">{a}</p>'
        f'</div></div>'
        for q, a in qas
    )
    faq_html = (
        '<div itemscope itemtype="https://schema.org/FAQPage" '
        'style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">'
        '<h2 style="color:var(--primary);margin-top:0;">❓ Frequently Asked Questions</h2>'
        + html_items +
        '</div>'
    )

    faq_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in qas
        ]
    }, ensure_ascii=False)
    return faq_html, faq_ld


def dedupe_keywords(*parts: str) -> str:
    seen = set()
    items = []
    for part in parts:
        if not part:
            continue
        for token in [clean(x) for x in str(part).split(',')]:
            if not token:
                continue
            key = token.lower()
            if key in seen:
                continue
            seen.add(key)
            items.append(token)
    return ', '.join(items)


def get_category(text: str) -> str:
    tu = str(text).upper()
    for key, cat in DEPT_MAP.items():
        if key in tu:
            return cat
    return 'government'


def load_seen() -> set:
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text()))
        except Exception:
            pass
    return set()


def save_seen(seen: set):
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=2))


TRACKING_PLACEHOLDERS = {
    'googleAnalytics4': {'G-XXXXXXXXXX'},
    'googleTagManager': {'GTM-XXXXXXX'},
    'googleSearchConsole': {'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'},
}


def load_tracking_config() -> dict:
    if not TRACKING_CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(TRACKING_CONFIG_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}


TRACKING_CONFIG = load_tracking_config()


def tracking_value(section: str, field: str) -> str:
    return clean((TRACKING_CONFIG.get(section) or {}).get(field, ''))


def tracking_enabled(section: str, field: str) -> bool:
    value = tracking_value(section, field)
    enabled = bool((TRACKING_CONFIG.get(section) or {}).get('enabled'))
    return enabled and value not in TRACKING_PLACEHOLDERS.get(section, set())


def detail_consent_bootstrap_markup() -> str:
    consent = TRACKING_CONFIG.get('consentMode', {})
    if not consent.get('enabled'):
        return ''

    storage_key = escape(clean(consent.get('storageKey', 'nd_consent_v1')), quote=True)
    default_mode = escape(clean(consent.get('defaultMode', 'reject')), quote=True)
    wait_for_update = int(consent.get('waitForUpdateMs', 500) or 500)
    return '\n'.join([
        '    <script>',
        '      (function(w){',
        f'        var consentKey = "{storage_key}";',
        f'        var defaultMode = "{default_mode}";',
        f'        var waitForUpdate = {wait_for_update};',
        '        var denied = {ad_storage: "denied", analytics_storage: "denied", ad_user_data: "denied", ad_personalization: "denied", functionality_storage: "granted", security_storage: "granted", personalization_storage: "denied"};',
        '        var analyticsGranted = {ad_storage: "denied", analytics_storage: "granted", ad_user_data: "denied", ad_personalization: "denied", functionality_storage: "granted", security_storage: "granted", personalization_storage: "denied"};',
        '        var allGranted = {ad_storage: "granted", analytics_storage: "granted", ad_user_data: "granted", ad_personalization: "granted", functionality_storage: "granted", security_storage: "granted", personalization_storage: "granted"};',
        '        function cloneState(state){ return JSON.parse(JSON.stringify(state)); }',
        '        function readStoredMode(){',
        '          try {',
        '            var raw = w.localStorage.getItem(consentKey);',
        '            if (!raw) { return ""; }',
        '            var parsed = JSON.parse(raw);',
        '            return parsed && parsed.mode ? parsed.mode : "";',
        '          } catch (err) {',
        '            return "";',
        '          }',
        '        }',
        '        function modeToState(mode){',
        '          if (mode === "all") return cloneState(allGranted);',
        '          if (mode === "analytics") return cloneState(analyticsGranted);',
        '          return cloneState(denied);',
        '        }',
        '        w.dataLayer = w.dataLayer || [];',
        '        w.gtag = w.gtag || function(){w.dataLayer.push(arguments);};',
        '        var initialMode = readStoredMode() || defaultMode;',
        '        var initialState = modeToState(initialMode);',
        '        initialState.wait_for_update = waitForUpdate;',
        '        w.NAUKRI_DHABA_CONSENT_KEY = consentKey;',
        '        w.NAUKRI_DHABA_CONSENT_STATE = modeToState(initialMode);',
        '        w.gtag("consent", "default", initialState);',
        '        w.gtag("set", "ads_data_redaction", true);',
        '        w.gtag("set", "url_passthrough", true);',
        '      })(window);',
        '    </script>',
    ])


def detail_head_tracking_markup() -> str:
    serialized_config = json.dumps(
        TRACKING_CONFIG,
        separators=(",", ":"),
        ensure_ascii=False,
    ).replace("</", "<\\/")
    lines = [
        f'    <script>window.NAUKRI_DHABA_TRACKING_CONFIG = {serialized_config};</script>'
    ]

    if tracking_enabled('googleSearchConsole', 'verificationCode'):
        lines.append(
            f'    <meta name="google-site-verification" content="{escape(tracking_value("googleSearchConsole", "verificationCode"), quote=True)}">'
        )

    consent_markup = detail_consent_bootstrap_markup()
    if consent_markup:
        lines.append(consent_markup)

    if tracking_enabled('googleTagManager', 'containerId'):
        container_id = escape(tracking_value('googleTagManager', 'containerId'), quote=True)
        lines.extend([
            '    <!-- Google Tag Manager -->',
            '    <script>',
            '      (function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({"gtm.start":',
            '      new Date().getTime(),event:"gtm.js"});var f=d.getElementsByTagName(s)[0],',
            '      j=d.createElement(s),dl=l!="dataLayer"?"&l="+l:"";j.async=true;j.src=',
            '      "https://www.googletagmanager.com/gtm.js?id="+i+dl;f.parentNode.insertBefore(j,f);',
            f'      }})(window,document,"script","dataLayer","{container_id}");',
            '    </script>',
            '    <!-- End Google Tag Manager -->',
        ])
    elif tracking_enabled('googleAnalytics4', 'measurementId'):
        measurement_id = escape(tracking_value('googleAnalytics4', 'measurementId'), quote=True)
        lines.extend([
            f'    <script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>',
            '    <script>',
            '      window.dataLayer = window.dataLayer || [];',
            '      function gtag(){dataLayer.push(arguments);}',
            '      gtag("js", new Date());',
            f'      gtag("config", "{measurement_id}");',
            '    </script>',
        ])

    lines.append('    <script src="../../js/tracking.js"></script>')
    return '\n'.join(lines)


def detail_body_tracking_markup() -> str:
    if not tracking_enabled('googleTagManager', 'containerId'):
        return ''
    container_id = escape(tracking_value('googleTagManager', 'containerId'), quote=True)
    return (
        '    <!-- Google Tag Manager (noscript) -->\n'
        f'    <noscript><iframe src="https://www.googletagmanager.com/ns.html?id={container_id}" '
        'height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>\n'
        '    <!-- End Google Tag Manager (noscript) -->'
    )


# ══════════════════════════════════════════════════════════
# HTTP FETCHER
# ══════════════════════════════════════════════════════════

# Explicitly clear proxy env vars — trust_env=False alone is not enough
# on some GitHub Actions runners that inject proxies at a lower level.
for _pvar in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy',
              'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy'):
    os.environ.pop(_pvar, None)

_NO_PROXY = {'http': None, 'https': None}  # passed to every requests call

_session = requests.Session()
_session.trust_env = False  # ignore HTTP_PROXY/HTTPS_PROXY env vars from GitHub Actions
_session.headers.update(HEADERS)

_cf_session = None
if cloudscraper is not None:
    try:
        _cf_session = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
        )
        _cf_session.trust_env = False  # ignore HTTP_PROXY/HTTPS_PROXY env vars
        _cf_session.headers.update(HEADERS)
    except Exception as exc:
        log.warning(f'Cloudscraper init failed, falling back to requests: {exc}')
        _cf_session = None

# Cloudflare Worker proxy (set CF_WORKER_PROXY_URL env var to enable)
_CF_WORKER_URL    = os.environ.get('CF_WORKER_PROXY_URL', '').rstrip('/')
_CF_WORKER_SECRET = os.environ.get('CF_WORKER_SECRET', '')

if _CF_WORKER_URL:
    log.info(f'CF Worker proxy configured: {_CF_WORKER_URL[:40]}...')
else:
    log.warning('CF_WORKER_PROXY_URL is NOT set — direct requests will be used. '
                'Set this secret in GitHub Actions if scraping fails.')

def _fetch_via_worker(url: str) -> BeautifulSoup | None:
    """Fetch a URL through the Cloudflare Worker proxy."""
    proxy_url = f'{_CF_WORKER_URL}/?url={requests.utils.quote(url, safe="")}'
    headers = {}
    if _CF_WORKER_SECRET:
        headers['X-Proxy-Secret'] = _CF_WORKER_SECRET
    try:
        r = _session.get(proxy_url, headers=headers, timeout=TIMEOUT, proxies=_NO_PROXY)
        if r.status_code == 503 and r.headers.get('X-Challenge-Detected'):
            log.warning(f'CF Worker: Cloudflare challenge page detected for {url} — site is blocking scraper requests')
            return None
        r.raise_for_status()
        origin_status = r.headers.get('X-Origin-Status', '?')
        log.info(f'CF Worker OK for {url} (origin status: {origin_status}, size: {len(r.content)} bytes)')
        return BeautifulSoup(r.content, 'lxml')
    except Exception as exc:
        log.warning(f'CF Worker fetch failed for {url}: {exc}')
        return None

def fetch(url: str, retries: int = 3) -> BeautifulSoup | None:
    # Try Cloudflare Worker first if configured
    if _CF_WORKER_URL:
        log.info(f'GET {url} via CF Worker')
        result = _fetch_via_worker(url)
        if result is not None:
            time.sleep(DELAY)
            return result
        log.warning(f'CF Worker failed for {url}, falling back to direct fetch')

    sessions = [_session]
    if _cf_session is not None:
        sessions.insert(0, _cf_session)

    for attempt in range(1, retries + 1):
        for idx, session in enumerate(sessions):
            client_name = 'cloudscraper' if idx == 0 and _cf_session is not None else 'requests'
            try:
                log.debug(f'GET {url} via {client_name}')
                r = session.get(url, timeout=TIMEOUT, proxies=_NO_PROXY)
                r.raise_for_status()
                time.sleep(DELAY)
                return BeautifulSoup(r.content, 'lxml')
            except Exception as exc:
                log.warning(f'Attempt {attempt}/{retries} via {client_name} failed for {url}: {exc}')
        if attempt < retries:
            time.sleep(DELAY * attempt)
    log.error(f'Giving up on {url}')
    return None


# ══════════════════════════════════════════════════════════
# SARKARIRESULT.COM — LISTING PAGE PARSER
# ══════════════════════════════════════════════════════════
# sarkariresult.com listing table structure:
#
#   <div id="post-list"> or <div class="TableLi">
#     <table>
#       <tr>
#         <td>                               ← col 0: "New" badge + title link
#           <b style="color:red">New</b>
#           <a href="/path/to/detail/">Post Title Here</a>
#         </td>
#         <td>28/02/2026</td>               ← col 1: date
#       </tr>
#     </table>
#   </div>
#
# Sometimes there is a 3-column layout with dept in col 0,
# title+link in col 1, date in col 2.

def parse_listing(soup: BeautifulSoup, page_type: str, source_base: str = BASE) -> list[dict]:
    """Extract all rows from a listing page. Works across all supported sources."""
    items = []

    # Try several known wrapper selectors in priority order.
    # Covers sarkariresult (TableLi/post-list) table-based layout.
    containers = (
        soup.select('#post-list table tr') or
        soup.select('.TableLi table tr') or
        soup.select('div.latestnews table tr') or
        soup.select('table.latestnews tr') or
        soup.select('article table tr') or
        soup.select('.entry-content table tr') or
        soup.select('.post-content table tr') or
        soup.select('table tr')
    )

    for tr in containers:
        tds = tr.find_all('td')
        if not tds:
            continue

        link_tag = None
        title    = ''
        date_str = ''
        dept     = ''

        # 3-col: dept | title+link | date
        if len(tds) >= 3:
            dept     = clean(tds[0].get_text())
            link_tag = tds[1].find('a')
            title    = clean(link_tag.get_text()) if link_tag else clean(tds[1].get_text())
            date_str = clean(tds[2].get_text())

        # 2-col: title+link | date
        elif len(tds) == 2:
            link_tag = tds[0].find('a')
            title    = clean(link_tag.get_text()) if link_tag else clean(tds[0].get_text())
            date_str = clean(tds[1].get_text())
            dept     = infer_dept(title)

        # 1-col: title+link (date embedded or missing)
        elif len(tds) == 1:
            link_tag = tds[0].find('a')
            if not link_tag:
                continue
            title    = clean(link_tag.get_text())
            dept     = infer_dept(title)
            # Try to find a date in the cell text
            m = re.search(r'\d{1,2}/\d{1,2}/\d{4}', tds[0].get_text())
            date_str = m.group(0) if m else ''

        if not title or len(title) < 8:
            continue
        if not link_tag or not link_tag.get('href'):
            continue

        detail_url = urljoin(source_base, link_tag['href'])

        # Skip header rows / navigation rows
        if title.lower() in ('post name', 'latest jobs', 'results', 'admit card', '#', ''):
            continue

        if not kind_matches_title(title, page_type):
            continue

        items.append({
            'title':      normalize_title(title),
            'dept':       sanitize(dept) if dept else infer_dept(title),
            'date_str':   parse_display_date(date_str),
            'detail_url': detail_url,
            'source_detail_url': detail_url,
            'page_type':  page_type,
        })

    log.info(f'  Listing parser found {len(items)} raw rows')
    if len(items) <= 3:
        items = parse_listing_from_anchors(soup, page_type)
        log.info(f'  Anchor fallback found {len(items)} raw rows')
    return items


def listing_text_matches(title: str, page_type: str) -> bool:
    text = title.lower()
    if page_type == 'job':
        return bool(re.search(r'online form|recruitment|vacancy|admission|registration|apply|correction|edit form', text))
    if page_type == 'result':
        return bool(re.search(r'result|merit|score\s*card|marks|cutoff|selection list', text))
    if page_type == 'admit':
        return bool(re.search(r'admit card|exam city|hall ticket|call letter|exam date', text))
    return False


def kind_matches_title(title: str, kind: str) -> bool:
    text = normalize_title(title)
    if kind == 'job':
        return (
            listing_text_matches(text, 'job')
            and not listing_text_matches(text, 'result')
            and not listing_text_matches(text, 'admit')
        )
    if kind == 'result':
        return listing_text_matches(text, 'result')
    if kind == 'admit':
        return listing_text_matches(text, 'admit')
    return True


def parse_listing_from_anchors(soup: BeautifulSoup, page_type: str) -> list[dict]:
    items = []
    seen = set()
    max_items = 150
    skip_paths = {
        'latestjob', 'result', 'admitcard', 'syllabus', 'answerkey', 'admission',
        'boardall', 'contactus', 'search', 'videozone', 'archive', 'top10',
    }

    for anchor in soup.find_all('a', href=True):
        title = clean(anchor.get_text(" ", strip=True))
        if len(title) < 8 or not listing_text_matches(title, page_type):
            continue

        detail_url = normalize_url(anchor.get('href', ''))
        if detail_url == '#':
            continue

        parsed = urlparse(detail_url)
        path_parts = [part for part in parsed.path.split('/') if part]
        if parsed.netloc.lower() not in SOURCE_HOSTS or len(path_parts) < 1:
            continue
        if path_parts[0].lower() in skip_paths:
            continue

        dedupe_key = (title.lower(), detail_url.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        items.append({
            'title': normalize_title(title),
            'dept': infer_dept(title),
            'date_str': 'Check Notification',
            'detail_url': detail_url,
            'source_detail_url': detail_url,
            'page_type': page_type,
        })
        if len(items) >= max_items:
            break

    return items


def infer_dept(title: str) -> str:
    """Guess department from post title."""
    tu = title.upper()
    matches = []
    for key in DEPT_MAP:
        pos = tu.find(key)
        if pos >= 0:
            matches.append((pos, -len(key), key))
    if matches:
        matches.sort()
        return matches[0][2]
    return 'Government'


# ══════════════════════════════════════════════════════════
# SARKARIRESULT.COM — DETAIL PAGE PARSER
# ══════════════════════════════════════════════════════════
# Detail page table structure (orange-theme boxes):
#
#   <table>
#     <tr><td colspan="2"><b>Post Name</b></td></tr>
#     <!-- Important Dates -->
#     <tr><td>Application Begin</td><td>DD/MM/YYYY</td></tr>
#     <tr><td>Last Date for Apply Online</td><td>DD/MM/YYYY</td></tr>
#     <tr><td>Last Date Fee Payment</td><td>DD/MM/YYYY</td></tr>
#     <tr><td>Correction Date</td><td>DD/MM/YYYY</td></tr>
#     <tr><td>Exam Date</td><td>DD/MM/YYYY</td></tr>
#     <tr><td>Admit Card</td><td>DD/MM/YYYY</td></tr>
#     <tr><td>Result Date</td><td>DD/MM/YYYY</td></tr>
#     <!-- Application Fee -->
#     <tr><td>General / OBC / EWS</td><td>₹XXX/-</td></tr>
#     <tr><td>SC / ST</td><td>₹XXX/-</td></tr>
#     <!-- Age Limit -->
#     <tr><td>Minimum Age</td><td>XX Years</td></tr>
#     <tr><td>Maximum Age</td><td>XX Years</td></tr>
#     <!-- Vacancy Details -->
#     <tr><td>Total Post</td><td>XXXX</td></tr>
#     <!-- Important Links -->
#     <tr><td bgcolor="#FF6600">Apply Online</td><td><a href="...">Click Here</a></td></tr>
#     <tr><td bgcolor="#FF6600">Download Notification</td><td><a href="...">Click Here</a></td></tr>
#     <tr><td bgcolor="#FF6600">Check Result</td><td><a href="...">Click Here</a></td></tr>
#     <tr><td bgcolor="#FF6600">Download Admit Card</td><td><a href="...">Click Here</a></td></tr>
#   </table>

def parse_detail(soup: BeautifulSoup, item: dict) -> dict:
    """
    Scrape full detail from a sarkariresult.com detail page.
    Returns enriched item dict.
    """
    d = dict(item)   # copy base item
    d.setdefault('apply_url',         '#')
    d.setdefault('notification_url',  '#')
    d.setdefault('result_url',        '#')
    d.setdefault('scorecard_url',     '#')
    d.setdefault('admit_url',         '#')
    d.setdefault('source_detail_url', d.get('detail_url', ''))
    d.setdefault('app_begin',         'Check Notification')
    d.setdefault('last_date',         d.get('date_str', 'Check Notification'))
    d.setdefault('exam_date',         'As per Schedule')
    d.setdefault('result_date',       d.get('date_str', date.today().strftime('%d/%m/%Y')))
    d.setdefault('admit_release',     d.get('date_str', date.today().strftime('%d/%m/%Y')))
    d.setdefault('total_posts',       '')
    d.setdefault('age_min',           18)
    d.setdefault('age_max',           35)
    d.setdefault('fee_general',       '')
    d.setdefault('fee_sc_st',         '')
    d.setdefault('qualification',     'Check Notification')
    d.setdefault('salary',            'As per Government Norms')
    d.setdefault('extra_links',       [])    # [{label, url}]

    if not soup:
        return d

    # ── Extract all tables ─────────────────────────────────
    tables = soup.find_all('table')
    all_rows = []
    for tbl in tables:
        for tr in tbl.find_all('tr'):
            cells = tr.find_all(['td', 'th'])
            all_rows.append(cells)

    # ── Walk all rows and parse key-value pairs ────────────
    for cells in all_rows:
        if len(cells) < 1:
            continue

        label = clean(cells[0].get_text()).lower()
        val = first_value_cell(cells)

        # ── Important Dates ──────────────────────────────
        if re.search(r'application\s*begin|apply\s*start', label) and looks_like_date_value(val):
            d['app_begin'] = sanitize(val) or d['app_begin']

        elif re.search(r'last\s*date|closing\s*date', label) and looks_like_date_value(val):
            d['last_date'] = sanitize(val) or d['last_date']

        elif re.search(r'exam\s*date|examination\s*date', label) and looks_like_date_value(val):
            d['exam_date'] = sanitize(val) or d['exam_date']

        elif re.search(r'result\s*date|declaration\s*date', label) and looks_like_date_value(val):
            d['result_date'] = sanitize(val) or d['result_date']

        elif re.search(r'admit\s*card\s*date|hall\s*ticket\s*date', label) and looks_like_date_value(val):
            d['admit_release'] = sanitize(val) or d['admit_release']

        # ── Application Fee ──────────────────────────────
        elif re.search(r'general|obc|ews|unreserved', label) and looks_like_fee_value(val):
            d['fee_general'] = sanitize(val)

        elif re.search(r'sc\s*/\s*st|scheduled', label) and looks_like_fee_value(val):
            d['fee_sc_st'] = sanitize(val)

        # ── Age Limit ────────────────────────────────────
        elif re.search(r'minimum\s*age|min\.\s*age', label):
            m = re.search(r'\d+', val)
            if m:
                d['age_min'] = int(m.group())

        elif re.search(r'maximum\s*age|max\.\s*age', label):
            m = re.search(r'\d+', val)
            if m:
                d['age_max'] = int(m.group())

        elif re.search(r'age\s*limit', label) and re.search(r'\d+', val):
            nums = re.findall(r'\d+', val)
            if len(nums) >= 2:
                d['age_min'] = int(nums[0])
                d['age_max'] = int(nums[1])
            elif len(nums) == 1:
                d['age_max'] = int(nums[0])

        # ── Vacancy / Posts ──────────────────────────────
        elif re.search(r'total\s*post|vacancy|vacancies|total\s*vacancy', label):
            m = re.search(r'[\d,]+', val)
            if m:
                d['total_posts'] = m.group().replace(',', '')

        # ── Qualification ────────────────────────────────
        elif re.search(r'qualification|education|eligibility', label):
            d['qualification'] = sanitize(val) or d['qualification']

        # ── Salary / Pay ─────────────────────────────────
        elif re.search(r'salary|pay\s*scale|pay\s*band|ctc|stipend', label):
            d['salary'] = sanitize(val) or d['salary']

        # ── Important Links (orange cells) ───────────────
        # SarkariResult marks link rows with bgcolor="#FF6600" or background orange
        bg = cells[0].get('bgcolor', '').lower() if hasattr(cells[0], 'get') else ''
        style_str = cells[0].get('style', '').lower() if hasattr(cells[0], 'get') else ''
        is_link_row = (
            '#ff6600' in bg or 'ff6600' in style_str or
            'orange' in style_str or
            re.search(r'apply\s*online|download\s*notif|check\s*result|admit\s*card|score\s*card|merit\s*list', label)
        )

        if is_link_row and len(cells) > 1:
            # Extract all anchor tags from the value cell
            link_cell = cells[1]
            anchors = link_cell.find_all('a')
            for a in anchors:
                href = normalize_url(a.get('href', ''))
                link_text = clean(a.get_text())

                if re.search(r'apply\s*online|register', label + ' ' + link_text, re.I):
                    d['apply_url'] = href
                elif re.search(r'notification|official\s*notice|advt', label + ' ' + link_text, re.I):
                    d['notification_url'] = href
                elif re.search(r'result|merit\s*list', label + ' ' + link_text, re.I):
                    d['result_url'] = href
                elif re.search(r'score\s*card|scorecard|mark\s*sheet', label + ' ' + link_text, re.I):
                    d['scorecard_url'] = href
                elif re.search(r'admit\s*card|hall\s*ticket|call\s*letter', label + ' ' + link_text, re.I):
                    d['admit_url'] = href

                # Collect as extra link
                if href and href != '#':
                    lbl = sanitize(label or link_text) or 'Official Link'
                    d['extra_links'].append({'label': lbl.title(), 'url': href})

    # ── Resolve & deduplicate extra_links ─────────────────
    seen_urls = set()
    unique_links = []
    for lnk in d['extra_links']:
        raw = lnk['url']
        # Resolve source-site URLs to their official destinations
        resolved = official_url_or_empty(raw)
        if not resolved:
            resolved = _extract_embedded_official_url(raw)
        if not resolved:
            resolved = _resolve_source_redirect(raw)
        url = resolved or raw
        if url and url != '#' and url not in seen_urls and not is_source_url(url):
            seen_urls.add(url)
            unique_links.append({'label': lnk['label'], 'url': url})
    d['extra_links'] = unique_links

    # ── Full-page anchor scan as fallback ─────────────────
    # Catches Apply / Notification links that are not in orange rows,
    # plus all PDF / .gov.in documents anywhere on the page.
    for a in soup.find_all('a', href=True):
        raw_href = a.get('href', '')
        if not raw_href:
            continue
        href_clean = normalize_url(raw_href)
        if href_clean == '#':
            continue
        link_text = clean(a.get_text())

        # Fill missing primary buttons from any <a> on the page
        if d['apply_url'] == '#' and re.search(r'apply\s*(online|now|here)', link_text, re.I):
            d['apply_url'] = href_clean
        if d['notification_url'] == '#' and re.search(r'notif|advt|official\s*notice', link_text, re.I):
            d['notification_url'] = href_clean
        if d['result_url'] == '#' and re.search(r'result|merit\s*list', link_text, re.I):
            d['result_url'] = href_clean
        if d['admit_url'] == '#' and re.search(r'admit\s*card|hall\s*ticket', link_text, re.I):
            d['admit_url'] = href_clean

        # Collect all external official / PDF links
        if re.search(r'\.(pdf|PDF)$', raw_href) or re.search(r'\.gov\.in|\.nic\.in', raw_href):
            lbl = sanitize(link_text) or 'Official Document'
            if href_clean not in seen_urls:
                seen_urls.add(href_clean)
                d['extra_links'].append({'label': lbl, 'url': href_clean})

    d['title'] = normalize_title(d.get('title', ''))
    d['last_date'] = parse_display_date(d.get('last_date'))
    d['result_date'] = parse_display_date(d.get('result_date'))
    d['admit_release'] = parse_display_date(d.get('admit_release'))
    d['apply_url'] = primary_cta_url(d.get('apply_url'), d.get('source_detail_url', ''))
    d['result_url'] = primary_cta_url(d.get('result_url'), d.get('source_detail_url', ''))
    d['admit_url'] = primary_cta_url(d.get('admit_url'), d.get('source_detail_url', ''))
    d['notification_url'] = to_public_url(d.get('notification_url'))
    d['scorecard_url'] = to_public_url(d.get('scorecard_url'))

    public_links = []
    public_seen = set()
    for lnk in d['extra_links']:
        public_url = to_public_url(lnk.get('url', ''))
        if public_url == '#':
            continue
        key = (lnk.get('label', ''), public_url)
        if key in public_seen:
            continue
        public_seen.add(key)
        public_links.append({'label': lnk.get('label', 'Official Link'), 'url': public_url})
    d['extra_links'] = public_links

    return d


# ══════════════════════════════════════════════════════════
# HTML PAGE BUILDERS
# ══════════════════════════════════════════════════════════

def _header(active: str) -> str:
    # Bilingual nav labels: English + Hindi for SEO across both language queries
    tabs = [
        ('latest-jobs.html', '💼 <span class="lang-en">Latest Jobs</span><span class="lang-hi">नवीनतम नौकरियां</span>', 'jobs'),
        ('results.html',     '📊 <span class="lang-en">Results</span><span class="lang-hi">परिणाम</span>',               'results'),
        ('admit-cards.html', '🎫 <span class="lang-en">Admit Cards</span><span class="lang-hi">प्रवेश पत्र</span>',     'admit-cards'),
        ('resources.html',   '📚 <span class="lang-en">Resources</span><span class="lang-hi">संसाधन</span>',             'resources'),
    ]
    desktop = '\n      '.join(
        f'<a href="/{u}" class="{"active" if k == active else ""}">{lbl}</a>'
        for u, lbl, k in tabs
    )
    mobile_home = '🏠 <span class="lang-en">Home</span><span class="lang-hi">होम</span>'
    mobile = '\n    '.join(f'<a href="/{u}">{lbl}</a>' for u, lbl, _ in tabs)
    return f'''<header class="header">
  <div class="container header__container">
    <a href="/" class="logo">📋 {SITE_NAME}</a>
    <nav class="nav nav--desktop">
      {desktop}
    </nav>
    <div style="display:flex;gap:1rem;align-items:center;">
      <button class="btn--icon" onclick="toggleDarkMode()" title="Toggle Dark Mode">🌓</button>
      <button class="btn--icon menu-toggle" onclick="toggleMobileMenu()" aria-label="Open menu" style="display:none;font-size:1.5rem;cursor:pointer;background:none;border:none;">☰</button>
    </div>
  </div>
  <div id="menu-overlay" onclick="closeMobileMenu()" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:1000;"></div>
  <nav class="nav--mobile">
    <button onclick="closeMobileMenu()" style="position:absolute;top:1rem;right:1rem;font-size:1.5rem;cursor:pointer;background:none;border:none;color:var(--text);">✕</button>
    <a href="/">{mobile_home}</a>
    {mobile}
  </nav>
  <style>.menu-toggle{{display:none!important}}@media(max-width:768px){{.nav--desktop{{display:none}}.menu-toggle{{display:block!important}}}}</style>
</header>'''


def _sidebar() -> str:
    return '''<aside class="sidebar">
  <div class="widget">
    <h3 class="widget__title">🔗 Quick Links</h3>
    <div class="footer__links">
      <a href="/latest-jobs">💼 Latest Jobs</a>
      <a href="/results">📊 Results</a>
      <a href="/admit-cards">🎫 Admit Cards</a>
      <a href="/eligibility-calculator.html">🎯 Eligibility Check</a>
    </div>
  </div>
  <div class="nd-ad ad-slot" data-ad-slot="sidebar-top" style="min-height:250px;">
    <p>Advertisement</p><p style="font-size:.75rem">300×250</p>
  </div>
</aside>'''


def _footer() -> str:
    y = date.today().year
    return f'''<footer class="footer">
  <div class="container">
    <div class="footer__grid">
      <div>
        <h3 class="footer__title">📋 {SITE_NAME}</h3>
        <p style="color:#ccc;font-size:.9rem;line-height:1.6;">Independent government job updates, result tracking, and admit card alerts for India.</p>
        <p style="color:#ccc;font-size:.85rem;margin-top:.5rem;">Share job alerts with friends &amp; help them find government jobs.</p>
      </div>
      <div>
        <h3 class="footer__title">Quick Links</h3>
        <div class="footer__links">
          <a href="/latest-jobs">Latest Jobs</a>
          <a href="/results">Results</a>
          <a href="/admit-cards">Admit Cards</a>
          <a href="/resources">Resources</a>
        </div>
      </div>
      <div>
        <h3 class="footer__title">Categories</h3>
        <div class="footer__links">
          <a href="/latest-jobs">UPSC Jobs</a>
          <a href="/latest-jobs">SSC Jobs</a>
          <a href="/latest-jobs">Railway Jobs</a>
          <a href="/latest-jobs">Banking Jobs</a>
          <a href="/latest-jobs">Defence Jobs</a>
          <a href="/latest-jobs">Police Jobs</a>
        </div>
      </div>
      <div>
        <h3 class="footer__title">State Jobs</h3>
        <div class="state-list">
          <a href="/state/uttar-pradesh.html">Uttar Pradesh</a>
          <a href="/state/bihar.html">Bihar</a>
          <a href="/state/rajasthan.html">Rajasthan</a>
          <a href="/state/madhya-pradesh.html">Madhya Pradesh</a>
          <a href="/state/delhi.html">Delhi</a>
          <a href="/state/maharashtra.html">Maharashtra</a>
        </div>
      </div>
    </div>
    <div class="footer__bottom">
      <p>&copy; {y} {SITE_NAME}. All rights reserved.</p>
      <p>Disclaimer: We are not affiliated with any government body. Information only.</p>
    </div>
  </div>
</footer>
<script src="/js/app.js"></script>
<script src="/js/ads-manager.js" defer></script>
<div id="lang-popup" class="lang-popup">
  <div class="lang-popup__box">
    <div style="font-size:2.5rem;margin-bottom:.75rem;">🇮🇳</div>
    <h2 style="color:var(--primary);margin:0 0 .5rem;font-size:1.3rem;">Choose Language / भाषा चुनें</h2>
    <p style="color:#666;font-size:.9rem;margin-bottom:1.5rem;">Select your preferred language</p>
    <div style="display:flex;gap:1rem;justify-content:center;">
      <button onclick="setLang(\'en\')" class="btn btn--primary btn--large" style="flex:1;min-width:120px;">English</button>
      <button onclick="setLang(\'hi\')" class="btn btn--secondary btn--large" style="flex:1;min-width:120px;">हिंदी</button>
    </div>
  </div>
</div>'''


def _seo_head(title: str, desc: str, canonical: str, dept: str, keywords_extra: str = '') -> str:
    title = normalize_title(title)
    cat = get_category(dept)
    base_kw = SEO_KW.get(cat, SEO_KW['government'])
    kw = dedupe_keywords(base_kw, title, f'{dept} Jobs', 'Government Jobs India', keywords_extra, SITE_NAME)
    og_title = f"{title} | {SITE_NAME}"
    desc_safe = clean(desc or og_title)[:160]
    return f'''    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | {SITE_NAME}</title>
    <meta name="description" content="{desc_safe}">
    <meta name="keywords" content="{kw}">
    <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
    <meta name="author" content="{SITE_NAME}">
    <link rel="canonical" href="{canonical}">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{og_title}">
    <meta property="og:description" content="{desc_safe}">
    <meta property="og:url" content="{canonical}">
    <meta property="og:site_name" content="{SITE_NAME}">
    <meta property="og:locale" content="hi_IN">
    <meta property="og:image" content="{SITE_URL}/img/og-default.png">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:image" content="{SITE_URL}/img/og-default.png">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{og_title}">
    <meta name="twitter:description" content="{desc_safe}">
    <meta name="geo.region" content="IN">
    <meta name="geo.placename" content="India">
    <link rel="stylesheet" href="../../css/style.css">
{detail_head_tracking_markup()}'''


# ── Job Page ───────────────────────────────────────────────
def build_job_page(d: dict) -> tuple[str, str]:
    title  = normalize_title(d['title'])
    dept   = d.get('dept', 'Government')
    cat    = get_category(dept)
    slug   = slugify(title)
    rel    = f'jobs/{cat}/{slug}.html'
    canon  = f'{SITE_URL}/{rel}'
    year   = date.today().year

    posts_disp = str(d['total_posts']) if d.get('total_posts') else 'Check Notification'
    desc_parts = [f"{title} — official recruitment notification from {dept}."]
    if d.get('total_posts'):
        desc_parts.append(f"Total vacancies: {d['total_posts']}.")
    if d.get('qualification') and d['qualification'] != 'Check Notification':
        desc_parts.append(f"Qualification: {d['qualification']}.")
    if d.get('age_min') and d.get('age_max'):
        desc_parts.append(f"Age limit: {d['age_min']} to {d['age_max']} years.")
    if d.get('app_begin') and d['app_begin'] != 'Check Notification':
        desc_parts.append(f"Application start: {d['app_begin']}.")
    if d.get('last_date') and d['last_date'] != 'Check Notification':
        desc_parts.append(f"Last date to apply: {d['last_date']}.")
    desc_parts.append(f"Apply online at {SITE_NAME}.")
    desc = ' '.join(desc_parts)
    _portal = official_portal_for(title, cat)
    apply_href = d.get('apply_url') or _portal or google_search_url(title, 'apply online official site')
    notification_href = d.get('notification_url') or google_search_url(title, 'notification PDF')
    _apply_is_portal = not d.get('apply_url') and bool(_portal)

    apply_btn = (
        f'<a href="{apply_href}" target="_blank" rel="nofollow noopener noreferrer" '
        f'class="btn btn--primary btn--large">🚀 Apply Online / आवेदन करें</a>'
        + (f'<p style="font-size:.8rem;color:#888;margin:.4rem 0 0;text-align:center;">'
           f'Opens the official portal — check the Apply / Recruitment section there.</p>'
           if _apply_is_portal else '')
    )
    notif_btn = (
        f'<a href="{notification_href}" target="_blank" rel="nofollow noopener noreferrer" '
        f'class="btn btn--secondary btn--large">📄 Download Notification</a>'
        if notification_href and notification_href != '#'
        else ''
    )

    # Extra links section
    extra_html = ''
    if d.get('extra_links'):
        rows = '\n'.join(
            f'<li><a href="{lnk["url"] if lnk.get("url") and lnk["url"] != "#" else google_search_url(title, lnk.get("label", ""))}" target="_blank" rel="noopener">'
            f'{clean(lnk["label"])}</a></li>'
            for lnk in d['extra_links'] if lnk.get('label')
        )
        if rows:
            extra_html = f'''<div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
          <h3 style="color:var(--primary);margin-top:0;">📎 Important Links / महत्वपूर्ण लिंक</h3>
          <ul style="line-height:2.4;">{rows}</ul>
        </div>'''

    # Fee info
    fee_rows = ''
    if d.get('fee_general'):
        fee_rows += f'<tr><td style="padding:8px 0;color:#666;">General / OBC / EWS</td><td style="padding:8px 0;font-weight:bold;">{d["fee_general"]}</td></tr>'
    if d.get('fee_sc_st'):
        fee_rows += f'<tr><td style="padding:8px 0;color:#666;">SC / ST / PH</td><td style="padding:8px 0;font-weight:bold;">{d["fee_sc_st"]}</td></tr>'
    fee_section = ''
    if fee_rows:
        fee_section = f'''<div style="border-left:4px solid var(--warning);background:#fff8e1;padding:1.5rem;border-radius:0 8px 8px 0;margin:1.5rem 0;">
          <h3 style="color:var(--primary);margin-top:0;">💳 Application Fee</h3>
          <table style="width:100%;">{fee_rows}</table>
        </div>'''

    # JSON-LD
    _valid_through = to_iso_date(d['last_date'])
    _org_name = cat.title() + ' Recruitment' if cat != 'government' else dept or 'Government of India'
    _org_url = official_portal_for(title, cat) or SITE_URL
    ld_job_dict = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": title,
        "description": desc,
        "datePosted": date.today().isoformat(),
        "employmentType": "FULL_TIME",
        "hiringOrganization": {"@type": "Organization", "name": _org_name, "sameAs": _org_url},
        "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": "India", "addressRegion": "India", "addressCountry": "IN"}},
        "url": canon,
        "directApply": bool(d.get('apply_url'))
    }
    if _valid_through and _valid_through >= date.today().isoformat():
        ld_job_dict["validThrough"] = _valid_through
    if d.get('salary') and d['salary'] != 'Check Notification':
        ld_job_dict["baseSalary"] = {"@type": "MonetaryAmount", "currency": "INR", "value": {"@type": "QuantitativeValue", "value": d['salary']}}
    if d.get('vacancy') and d['vacancy'] != 'Check Notification':
        ld_job_dict["totalJobOpenings"] = d['vacancy']
    ld_job = json.dumps(ld_job_dict, ensure_ascii=False)

    ld_bc = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": SITE_URL + '/'},
            {"@type": "ListItem", "position": 2, "name": "Jobs", "item": SITE_URL + '/latest-jobs'},
            {"@type": "ListItem", "position": 3, "name": dept, "item": SITE_URL + '/latest-jobs'},
            {"@type": "ListItem", "position": 4, "name": title, "item": canon},
        ]
    }, ensure_ascii=False)

    faq_html, faq_ld = build_job_faq(d)

    html = f'''<!DOCTYPE html>
<html lang="hi">
<head>
{_seo_head(title, desc, canon, dept)}
    <script type="application/ld+json">{ld_job}</script>
    <script type="application/ld+json">{ld_bc}</script>
    <script type="application/ld+json">{faq_ld}</script>
    <script src="../../js/ads-manager.js" defer></script>
</head>
<body>
{detail_body_tracking_markup()}
{_header('jobs')}

<div class="content-wrapper container" style="margin-top:2rem;">
  <main>
    <article class="job-detail">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/">Home</a> &gt; <a href="/latest-jobs">Jobs</a> &gt; <span>{title}</span>
      </nav>

      <h1 style="color:var(--primary);margin-bottom:.5rem;">
        {title} <span style="background:var(--secondary);color:#fff;padding:4px 12px;border-radius:4px;font-size:1rem;">{year}</span>
      </h1>

      <div class="nd-ad ad-slot" data-ad-slot="content-top"></div>

      <div class="info-grid">
        <div class="info-item">
          <span class="info-item__label">📅 Last Date</span>
          <span class="info-item__value" style="color:var(--danger);">{d["last_date"]}</span>
        </div>
        <div class="info-item">
          <span class="info-item__label">🏢 Department</span>
          <span class="info-item__value">{dept}</span>
        </div>
        <div class="info-item">
          <span class="info-item__label">📊 Total Posts</span>
          <span class="info-item__value">{posts_disp}</span>
        </div>
        <div class="info-item">
          <span class="info-item__label">👤 Age Limit</span>
          <span class="info-item__value">{d["age_min"]}–{d["age_max"]} Years</span>
        </div>
        <div class="info-item">
          <span class="info-item__label">🎓 Qualification</span>
          <span class="info-item__value" style="font-size:.95rem;">{d["qualification"]}</span>
        </div>
        <div class="info-item">
          <span class="info-item__label">💰 Salary / Pay Scale</span>
          <span class="info-item__value" style="font-size:.95rem;">{d["salary"]}</span>
        </div>
      </div>

      <div class="action-bar">
        {apply_btn}
        {notif_btn}
      </div>

      <div style="border-left:4px solid var(--primary);background:var(--surface);padding:1.5rem;margin:1.5rem 0;">
        <h2 style="color:var(--primary);margin-top:0;">📋 Important Dates / महत्वपूर्ण तिथियां</h2>
        <table style="width:100%;border-collapse:collapse;">
          <tr style="border-bottom:1px solid #eee;"><td style="padding:10px 0;color:#666;width:55%;">Application Begin</td><td style="font-weight:bold;">{d["app_begin"]}</td></tr>
          <tr style="border-bottom:1px solid #eee;"><td style="padding:10px 0;color:#666;">Last Date to Apply Online</td><td style="font-weight:bold;color:var(--danger);">{d["last_date"]}</td></tr>
          <tr style="border-bottom:1px solid #eee;"><td style="padding:10px 0;color:#666;">Exam Date</td><td style="font-weight:bold;">{d["exam_date"]}</td></tr>
        </table>
      </div>

      {fee_section}

      {build_job_overview(d)}

      <div class="nd-ad ad-slot" data-ad-slot="content-mid"></div>

      <div class="calculator">
        <h3 style="margin-top:0;">🎯 Age Eligibility Calculator / आयु कैलकुलेटर</h3>
        <p style="color:#666;font-size:.875rem;">Age limit: {d["age_min"]}–{d["age_max"]} years. OBC +3 yrs, SC/ST +5 yrs relaxation.</p>
        <div class="form-group">
          <label>Date of Birth / जन्म तिथि:</label>
          <input type="date" id="dob-input">
        </div>
        <div class="form-group">
          <label>Category / वर्ग:</label>
          <select id="category-select">
            <option value="general">General / सामान्य</option>
            <option value="obc">OBC (+3 years)</option>
            <option value="sc">SC (+5 years)</option>
            <option value="st">ST (+5 years)</option>
          </select>
        </div>
        <button onclick="checkEligibility({d['age_min']}, {d['age_max']})" class="btn btn--primary">Check Eligibility / योग्यता जांचें</button>
        <div id="eligibility-result" style="display:none;margin-top:1rem;padding:1rem;border-radius:4px;"></div>
      </div>

      {extra_html}

      <div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
        <h3 style="color:var(--primary);margin-top:0;">📝 How to Apply / आवेदन कैसे करें</h3>
        <ol style="line-height:2.2;">
          <li>Use the official authority portal linked above, not third-party mirrors.</li>
          <li>Verify district, category, and document rules before you create an account.</li>
          <li>Fill the application form carefully / फॉर्म ध्यानपूर्वक भरें</li>
          <li>Upload only the files and dimensions allowed in the official notice.</li>
          <li>Pay the fee only after you confirm the form preview and eligibility details.</li>
          <li>Save the final application number, preview, and receipt for later stages.</li>
        </ol>
      </div>

      {faq_html}

      <div class="share-section">
        <h3>📢 Share this Job</h3>
        <button onclick="sharePost(window.location.href,'{title.replace(chr(39),chr(96))}')" class="share-btn">Share</button>
      </div>

      <div class="nd-ad ad-slot" data-ad-slot="content-bottom"></div>
    </article>
  </main>
  {_sidebar()}
</div>

{_footer()}
</body>
</html>'''

    return rel, html


# ── Result Page ────────────────────────────────────────────
def build_result_page(d: dict) -> tuple[str, str]:
    title = normalize_title(d['title'])
    dept  = d.get('dept', 'Government')
    cat   = get_category(dept)
    slug  = slugify(title)
    if 'result' not in slug:
        slug += '-result'
    rel   = f'results/{cat}/{slug}.html'
    canon = f'{SITE_URL}/{rel}'
    desc  = f"{title}: Result declared. Check your result at {SITE_NAME}. Result date: {d['result_date']}."
    _rportal = official_portal_for(title, cat)
    result_href = d.get('result_url') or _rportal or google_search_url(title, 'result')
    scorecard_href = d.get('scorecard_url') or google_search_url(title, 'scorecard marks')
    _result_is_portal = not d.get('result_url') and bool(_rportal)

    check_btn = (
        f'<a href="{result_href}" target="_blank" rel="nofollow noopener noreferrer" '
        f'class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;">'
        f'🎯 Check Result / परिणाम देखें</a>'
        + (f'<p style="font-size:.8rem;color:#888;margin:.4rem 0 1rem;text-align:center;">'
           f'Opens the official portal — check the Latest Results section there.</p>'
           if _result_is_portal else '')
    )
    scorecard_btn = (
        f'<a href="{scorecard_href}" target="_blank" rel="nofollow noopener noreferrer" '
        f'class="btn btn--secondary btn--large" style="display:inline-block;margin-bottom:1rem;">📄 Download Scorecard</a>'
        if scorecard_href and scorecard_href != '#'
        else ''
    )

    extra_html = ''
    if d.get('extra_links'):
        rows = '\n'.join(
            f'<li><a href="{lnk["url"]}" target="_blank" rel="noopener">{clean(lnk["label"])}</a></li>'
            for lnk in d['extra_links'] if lnk.get('url') and lnk['url'] != '#'
        )
        if rows:
            extra_html = f'''<div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
          <h3 style="color:var(--primary);margin-top:0;">📎 Important Links</h3>
          <ul style="line-height:2.4;">{rows}</ul>
        </div>'''

    ld_ev = json.dumps({
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": desc,
        "url": canon,
        "about": {"@type": "Organization", "name": dept}
    }, ensure_ascii=False)

    ld_bc = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": SITE_URL + '/'},
            {"@type": "ListItem", "position": 2, "name": "Results", "item": SITE_URL + '/results'},
            {"@type": "ListItem", "position": 3, "name": dept, "item": SITE_URL + '/results'},
            {"@type": "ListItem", "position": 4, "name": title, "item": canon},
        ]
    }, ensure_ascii=False)

    faq_html, faq_ld = build_result_faq(d)

    html = f'''<!DOCTYPE html>
<html lang="hi">
<head>
{_seo_head(title + ' - Result', desc, canon, dept)}
    <script type="application/ld+json">{ld_ev}</script>
    <script type="application/ld+json">{ld_bc}</script>
    <script type="application/ld+json">{faq_ld}</script>
    <script src="../../js/ads-manager.js" defer></script>
</head>
<body>
{detail_body_tracking_markup()}
{_header('results')}

<div class="content-wrapper container" style="margin-top:2rem;">
  <main>
    <article class="result-detail">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/">Home</a> &gt; <a href="/results">Results</a> &gt; <span>{title}</span>
      </nav>

      <h1 style="color:var(--primary);">📊 {title}</h1>

      <div class="nd-ad ad-slot" data-ad-slot="content-top"></div>

      <div style="background:#e8f5e9;padding:1.5rem;border-radius:8px;text-align:center;margin:1.5rem 0;">
        <div style="display:inline-block;background:var(--success);color:#fff;padding:.5rem 1rem;border-radius:4px;font-weight:bold;margin-bottom:1rem;">✅ Declared / घोषित</div>
        {'<p style="color:#666;margin-bottom:1.5rem;">Result Date: ' + d["result_date"] + '</p>' if d["result_date"] not in ("Check Notification", "") else ''}
        {check_btn}
        {scorecard_btn}
        <div style="margin-top:1rem;">
          <a href="/latest-jobs" class="btn btn--secondary">🔍 Browse Latest Jobs</a>
        </div>
      </div>

      {extra_html}

      <div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
        <h3 style="color:var(--primary);margin-top:0;">📋 How to Check Result / परिणाम कैसे देखें</h3>
        <ol style="line-height:2.2;">
          <li>Open the official result portal linked above.</li>
          <li>Keep your roll number or registration number ready before loading the page.</li>
          <li>Match your name, category, and stage of exam carefully after login.</li>
          <li>Download the result or scorecard PDF from the authority site when available.</li>
          <li>Keep a saved copy for document verification, counselling, or joining steps.</li>
        </ol>
      </div>

      <div class="nd-ad ad-slot" data-ad-slot="content-bottom"></div>

      {faq_html}

      <div class="share-section">
        <h3>📢 Share this Result</h3>
        <button onclick="sharePost(window.location.href,'{title.replace(chr(39),chr(96))} Result Declared')" class="share-btn">Share</button>
      </div>
    </article>
  </main>
  {_sidebar()}
</div>

{_footer()}
</body>
</html>'''

    return rel, html


# ── Admit Card Page ────────────────────────────────────────
def build_admit_page(d: dict) -> tuple[str, str]:
    title = normalize_title(d['title'])
    dept  = d.get('dept', 'Government')
    cat   = get_category(dept)
    slug  = slugify(title)
    if 'admit' not in slug and 'hall' not in slug:
        slug += '-admit-card'
    rel   = f'admit-cards/{cat}/{slug}.html'
    canon = f'{SITE_URL}/{rel}'
    desc  = f"Download {title} admit card / hall ticket at {SITE_NAME}. Exam date: {d['exam_date']}."
    _aportal = official_portal_for(title, cat)
    admit_href = d.get('admit_url') or _aportal or google_search_url(title, 'admit card download')
    _admit_is_portal = not d.get('admit_url') and bool(_aportal)

    dl_btn = (
        f'<a href="{admit_href}" target="_blank" rel="nofollow noopener noreferrer" '
        f'class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;">'
        f'📥 Download Admit Card / हॉल टिकट डाउनलोड करें</a>'
        + (f'<p style="font-size:.8rem;color:#888;margin:.4rem 0 1rem;text-align:center;">'
           f'Opens the official portal — check the Admit Card / Hall Ticket section there.</p>'
           if _admit_is_portal else '')
    )

    extra_html = ''
    if d.get('extra_links'):
        rows = '\n'.join(
            f'<li><a href="{lnk["url"]}" target="_blank" rel="noopener">{clean(lnk["label"])}</a></li>'
            for lnk in d['extra_links'] if lnk.get('url') and lnk['url'] != '#'
        )
        if rows:
            extra_html = f'''<div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
          <h3 style="color:var(--primary);margin-top:0;">📎 Important Links</h3>
          <ul style="line-height:2.4;">{rows}</ul>
        </div>'''

    ld_ev = json.dumps({
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": desc,
        "url": canon,
        "about": {"@type": "Organization", "name": dept}
    }, ensure_ascii=False)

    ld_bc = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": SITE_URL + '/'},
            {"@type": "ListItem", "position": 2, "name": "Admit Cards", "item": SITE_URL + '/admit-cards'},
            {"@type": "ListItem", "position": 3, "name": dept, "item": SITE_URL + '/admit-cards'},
            {"@type": "ListItem", "position": 4, "name": title, "item": canon},
        ]
    }, ensure_ascii=False)

    faq_html, faq_ld = build_admit_faq(d)

    html = f'''<!DOCTYPE html>
<html lang="hi">
<head>
{_seo_head(title + ' - Admit Card', desc, canon, dept)}
    <script type="application/ld+json">{ld_ev}</script>
    <script type="application/ld+json">{ld_bc}</script>
    <script type="application/ld+json">{faq_ld}</script>
    <script src="../../js/ads-manager.js" defer></script>
</head>
<body>
{detail_body_tracking_markup()}
{_header('admit-cards')}

<div class="content-wrapper container" style="margin-top:2rem;">
  <main>
    <article class="admit-detail">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/">Home</a> &gt; <a href="/admit-cards">Admit Cards</a> &gt; <span>{title}</span>
      </nav>

      <h1 style="color:var(--primary);">🎫 {title}</h1>

      <div class="nd-ad ad-slot" data-ad-slot="content-top"></div>

      <div style="background:#e8f5e9;padding:1.5rem;border-radius:8px;text-align:center;margin:1.5rem 0;">
        <div style="display:inline-block;background:var(--success);color:#fff;padding:.5rem 1rem;border-radius:4px;font-weight:bold;margin-bottom:1rem;">✅ Available / उपलब्ध</div>
        <p style="color:#666;margin-bottom:.5rem;">Released: {d["admit_release"]}</p>
        <p style="color:#666;font-weight:bold;margin-bottom:1.5rem;">📅 Exam Date: {d["exam_date"]}</p>
        {dl_btn}
        <div style="margin-top:1rem;">
          <a href="/results" class="btn btn--secondary">📊 Check Results</a>
        </div>
      </div>

      {extra_html}

      <div style="border-left:4px solid var(--danger);background:#fff3e0;padding:1.5rem;border-radius:0 8px 8px 0;margin:1.5rem 0;">
        <h3 style="color:var(--danger);margin-top:0;">⚠️ Important Instructions / महत्वपूर्ण निर्देश</h3>
        <ul style="line-height:1.8;">
          <li>Carry a printed admit card exactly as required in the official instructions.</li>
          <li>Bring a valid photo ID that matches the admit-card identity details.</li>
          <li>Check reporting time, gate closing time, and city or centre code before travel.</li>
          <li>Verify exam date, shift timing, and venue address one more time on the official page.</li>
          <li>Avoid restricted items such as phones, smartwatches, calculators, or loose papers.</li>
        </ul>
      </div>

      <div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
        <h3 style="color:var(--primary);margin-top:0;">📋 Exam Day Checklist</h3>
        <ul style="list-style:none;padding:0;">
          <li style="padding:.4rem 0;">✅ Printed Admit Card (colour)</li>
          <li style="padding:.4rem 0;">✅ Valid Photo ID Proof</li>
          <li style="padding:.4rem 0;">✅ 2–3 Passport Size Photos</li>
          <li style="padding:.4rem 0;">✅ Black Ball Point Pen (2 pens)</li>
          <li style="padding:.4rem 0;">✅ Water Bottle (transparent, no label)</li>
        </ul>
      </div>

      <div class="nd-ad ad-slot" data-ad-slot="content-bottom"></div>

      {faq_html}

      <div class="share-section">
        <h3>📢 Share this Admit Card</h3>
        <button onclick="sharePost(window.location.href,'{title.replace(chr(39),chr(96))} Admit Card Available')" class="share-btn">Share</button>
      </div>
    </article>
  </main>
  {_sidebar()}
</div>

{_footer()}
</body>
</html>'''

    return rel, html


# ══════════════════════════════════════════════════════════
# LISTING PAGE UPDATER  (latest-jobs.html / results.html / admit-cards.html)
# ══════════════════════════════════════════════════════════

def prepend_to_listing(listing_file: Path, entries: list[dict], kind: str):
    """
    Legacy helper for prepend-style updates.
    Prefer replace_listing_sections() for deterministic full rebuilds.
    """
    if not entries or not listing_file.exists():
        return

    with open(listing_file, encoding='utf-8') as f:
        content = f.read()

    new_rows   = []
    new_cards  = []

    for e in entries[:30]:   # max 30 new entries per run
        title = e.get('title', '')
        dept  = e.get('dept', 'Government').upper()

        if kind == 'job':
            cat  = get_category(e.get('dept', ''))
            path = f"/jobs/{cat}/{slugify(title)}.html"
            date_label = e.get('last_date', '')
            btn  = 'Apply'
        elif kind == 'result':
            cat  = get_category(e.get('dept', ''))
            s    = slugify(title)
            if 'result' not in s:
                s += '-result'
            path = f"/results/{cat}/{s}.html"
            date_label = e.get('result_date', '')
            btn  = 'View'
        else:
            cat  = get_category(e.get('dept', ''))
            s    = slugify(title)
            if 'admit' not in s and 'hall' not in s:
                s += '-admit-card'
            path = f"/admit-cards/{cat}/{s}.html"
            date_label = e.get('exam_date', '') or e.get('admit_release', '')
            btn  = 'Download'

        new_rows.append(
            f'<tr><td>{dept}</td>'
            f'<td><a href="{path}" style="color:var(--primary);font-weight:600;">{title}</a></td>'
            f'<td>{date_label}</td>'
            f'<td><a href="{path}" class="btn btn--small btn--primary">{btn}</a></td></tr>'
        )
        new_cards.append(
            f'<div class="card">'
            f'<div class="card__header"><span class="badge">{dept}</span></div>'
            f'<h3 class="card__title">{title}</h3>'
            f'<p style="color:#666;font-size:.875rem;">📅 {date_label}</p>'
            f'<a href="{path}" class="btn btn--primary btn--block" style="margin-top:1rem;">{btn}</a>'
            f'</div>'
        )

    rows_str  = '\n'.join(new_rows)
    cards_str = '\n'.join(new_cards)

    # Insert rows right after <tbody>
    content = re.sub(r'(<tbody>)', r'\1\n' + rows_str, content, count=1)
    # Insert cards right after <div class="cards">
    content = re.sub(r'(<div class="cards">)', r'\1\n' + cards_str, content, count=1)

    with open(listing_file, 'w', encoding='utf-8') as f:
        f.write(content)

    log.info(f'  Updated {listing_file.name} with {len(entries)} new entries')


def build_listing_markup(entries: list[dict], kind: str, limit: int | None = None) -> tuple[str, str]:
    entries = prepare_listing_entries(entries, kind, limit)
    rows = []
    cards = []
    iterable = entries

    for e in iterable:
        title = normalize_title(e.get('title', ''))
        dept = e.get('dept', 'Government').upper()

        if kind == 'job':
            cat = get_category(e.get('dept', ''))
            path = e.get('url') or f"/jobs/{cat}/{slugify(title)}.html"
            date_label = e.get('last_date', '') or e.get('date_str', '')
            button = 'Apply'
        elif kind == 'result':
            cat = get_category(e.get('dept', ''))
            slug = slugify(title)
            if 'result' not in slug:
                slug += '-result'
            path = e.get('url') or f"/results/{cat}/{slug}.html"
            date_label = e.get('result_date', '') or e.get('date_str', '')
            button = 'View'
        else:
            cat = get_category(e.get('dept', ''))
            slug = slugify(title)
            if 'admit' not in slug and 'hall' not in slug:
                slug += '-admit-card'
            path = e.get('url') or f"/admit-cards/{cat}/{slug}.html"
            date_label = e.get('exam_date', '') or e.get('admit_release', '') or e.get('date_str', '')
            button = 'Download'

        rows.append(
            f'<tr><td>{dept}</td>'
            f'<td><a href="{path}" style="color:var(--primary);font-weight:600;">{title}</a></td>'
            f'<td>{date_label}</td>'
            f'<td><a href="{path}" class="btn btn--small btn--primary">{button}</a></td></tr>'
        )
        cards.append(
            f'<div class="card">'
            f'<div class="card__header"><span class="badge">{dept}</span></div>'
            f'<h3 class="card__title">{title}</h3>'
            f'<p style="color:#666;font-size:.875rem;">{date_label}</p>'
            f'<a href="{path}" class="btn btn--primary btn--block" style="margin-top:1rem;">{button}</a>'
            f'</div>'
        )

    return '\n'.join(rows), '\n'.join(cards)


def prepare_listing_entries(entries: list[dict], kind: str, limit: int | None = None) -> list[dict]:
    cleaned = []
    seen = set()
    for entry in entries:
        title = normalize_title(entry.get('title', ''))
        if not title or not kind_matches_title(title, kind):
            continue

        dept = clean(entry.get('dept', 'Government')) or 'Government'
        key = (title.lower(), dept.lower())
        if key in seen:
            continue
        seen.add(key)

        normalized = dict(entry)
        normalized['title'] = title
        normalized['dept'] = dept
        cleaned.append(normalized)
        if limit and len(cleaned) >= limit:
            break
    return cleaned


_LISTING_META = {
    'latest-jobs.html':  ('Latest Government Jobs',  SITE_URL + '/latest-jobs'),
    'results.html':      ('Government Exam Results',  SITE_URL + '/results'),
    'admit-cards.html':  ('Government Admit Cards',   SITE_URL + '/admit-cards'),
}


def replace_listing_sections(listing_file: Path, entries: list[dict], kind: str, limit: int | None = None):
    if not listing_file.exists():
        return

    rows_str, cards_str = build_listing_markup(entries, kind, limit=limit)
    with open(listing_file, encoding='utf-8') as f:
        content = f.read()

    content, tbody_count = re.subn(
        r'(<tbody>).*?(</tbody>)',
        rf'\1{rows_str}\2',
        content,
        count=1,
        flags=re.DOTALL,
    )
    content, cards_count = re.subn(
        r'(<div class="cards">).*?(</div>\s*<div class="ad-slot")',
        rf'\1{cards_str}\2',
        content,
        count=1,
        flags=re.DOTALL,
    )

    # Rebuild ItemList JSON-LD from current entries
    meta = _LISTING_META.get(listing_file.name)
    if meta:
        list_name, list_url = meta
        prepared = prepare_listing_entries(entries, kind, limit)
        items = []
        for i, e in enumerate(prepared):
            title = normalize_title(e.get('title', ''))
            cat = get_category(e.get('dept', ''))
            if kind == 'job':
                path = e.get('url') or f'/jobs/{cat}/{slugify(title)}.html'
            elif kind == 'result':
                slug = slugify(title)
                path = e.get('url') or f'/results/{cat}/{slug if "result" in slug else slug + "-result"}.html'
            else:
                slug = slugify(title)
                path = e.get('url') or f'/admit-cards/{cat}/{slug if "admit" in slug else slug + "-admit-card"}.html'
            items.append({'@type': 'ListItem', 'position': i + 1, 'name': title, 'url': SITE_URL + path})
        schema = json.dumps({'@context': 'https://schema.org', '@type': 'ItemList', 'name': list_name, 'url': list_url, 'itemListElement': items}, ensure_ascii=False)
        new_tag = f'<script type="application/ld+json">{schema}</script>'
        if 'application/ld+json' in content:
            content = re.sub(r'<script type="application/ld\+json">.*?</script>', new_tag, content, count=1, flags=re.DOTALL)
        else:
            content = content.replace('</head>', f'    {new_tag}\n</head>', 1)

    with open(listing_file, 'w', encoding='utf-8') as f:
        f.write(content)

    log.info(
        f'  Rebuilt {listing_file.name} '
        f'(tbody={"yes" if tbody_count else "no"}, cards={"yes" if cards_count else "no"})'
    )


def replace_home_jobs_section(index_file: Path, entries: list[dict], limit: int = 10):
    if not index_file.exists():
        return

    cleaned = prepare_listing_entries(entries, 'job', limit)
    rows_str, cards_str = build_listing_markup(cleaned, 'job')
    section = f'''<!-- Latest Jobs -->
<div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin-bottom:2rem;">
<h2 style="color:var(--primary);margin-top:0;display:flex;align-items:center;gap:0.5rem;">
<span>📋</span> Latest Jobs
                </h2>
<div class="table-wrapper">
<table class="table">
<thead>
<tr>
<th>Department</th>
<th>Exam/Post Name</th>
<th>Last Date</th>
<th>Action</th>
</tr>
</thead>
<tbody>{rows_str}</tbody>
</table>
</div>
<div class="cards">{cards_str}</div>
<div style="text-align:center;margin-top:1.5rem;">
<a class="btn btn--primary" href="/latest-jobs">View All Jobs →</a>
</div>
</div>'''

    content = index_file.read_text(encoding='utf-8')
    content, count = re.subn(
        r'<!-- Latest Jobs -->.*?<!-- Results & Admit Cards Grid -->',
        section + '\n<!-- Results & Admit Cards Grid -->',
        content,
        count=1,
        flags=re.DOTALL,
    )
    if count:
        index_file.write_text(content, encoding='utf-8')
        log.info('  Rebuilt index.html latest jobs section cleanly')


def load_existing_detail_entries(kind: str) -> list[dict]:
    if kind == 'job':
        base = SITE_ROOT / 'jobs'
    elif kind == 'result':
        base = SITE_ROOT / 'results'
    else:
        base = SITE_ROOT / 'admit-cards'

    entries = []
    seen_slugs: set[str] = set()   # deduplicate by filename slug
    for path in sorted(base.rglob('*.html'), key=lambda p: p.stat().st_mtime, reverse=True):
        slug = path.stem  # e.g. 'up-police-constable-edit-correction-form-2026'
        if slug in seen_slugs:
            # Same slug already loaded from a newer file — skip this stale copy
            log.debug(f'  [dedup] Skipping duplicate slug in listings: {path.relative_to(SITE_ROOT)}')
            continue
        seen_slugs.add(slug)

        rel = path.relative_to(SITE_ROOT).as_posix()
        html = path.read_text(encoding='utf-8', errors='replace')
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.I | re.S)
        title = clean(re.sub(r'<[^>]+>', '', title_match.group(1))) if title_match else normalize_title(path.stem.replace('-', ' '))
        dept_match = re.search(r'info-item__label">[^<]*Department</span>\s*<span class="info-item__value">([^<]+)', html, re.I)
        dept = clean(dept_match.group(1)) if dept_match else infer_dept(title)
        # Override dept using URL path category when stored value is unreliable.
        # e.g. results/railway/... → RAILWAY, jobs/ssc/... → SSC
        _path_cat = path.parent.name.upper()
        _cat_to_dept = {
            'RAILWAY': 'RAILWAY', 'SSC': 'SSC', 'UPSC': 'UPSC',
            'BANKING': 'BANKING', 'POLICE': 'POLICE', 'DEFENCE': 'DEFENCE',
        }
        if _path_cat in _cat_to_dept:
            dept = _cat_to_dept[_path_cat]
        # If stored dept is NTA (scraper bug from old runs), try title inference.
        # If title also doesn't give a proper category, fall back to GOVERNMENT.
        elif dept.upper() == 'NTA':
            inferred = infer_dept(title)
            dept = inferred if inferred.upper() not in ('NTA', 'GOVERNMENT') else 'GOVERNMENT'
        date_label = 'Check Notification'

        actual_url = '/' + rel  # actual on-disk path, used to avoid slug mismatch
        if kind == 'job':
            match = re.search(r'Last Date to Apply Online</td><td[^>]*>([^<]+)</td>', html, re.I)
            date_label = clean(match.group(1)) if match else 'Check Notification'
            entries.append({'title': title, 'dept': dept, 'last_date': date_label, 'url': actual_url})
        elif kind == 'result':
            match = re.search(r'Result Date:\s*([^<]+)</p>', html, re.I)
            date_label = clean(match.group(1)) if match else 'Check Notification'
            entries.append({'title': title, 'dept': dept, 'result_date': date_label, 'url': actual_url})
        else:
            match = re.search(r'Exam Date:\s*([^<]+)</p>', html, re.I)
            date_label = clean(match.group(1)) if match else 'Check Notification'
            entries.append({'title': title, 'dept': dept, 'exam_date': date_label, 'url': actual_url})

    return entries


# ══════════════════════════════════════════════════════════
# RESOURCES — PREVIOUS PAPERS PAGE UPDATER
# ══════════════════════════════════════════════════════════

# Category badge colours matching previous-papers.html
_CAT_BADGE = {
    'upsc':     ('#e8eaf6', '#1a237e', 'UPSC'),
    'ssc':      ('#e8f5e9', '#2e7d32', 'SSC'),
    'railway':  ('#fff3e0', '#e65100', 'Railway'),
    'banking':  ('#e3f2fd', '#0d47a1', 'Banking'),
    'police':   ('#fce4ec', '#880e4f', 'Police'),
    'defence':  ('#fce4ec', '#880e4f', 'Defence'),
    'state':    ('#f3e5f5', '#4a148c', 'State PSC'),
    'government': ('#e8eaf6', '#1a237e', 'Govt'),
}

def _build_paper_card(title: str, cat: str) -> str:
    bg, tc, label = _CAT_BADGE.get(cat, ('#e8eaf6', '#1a237e', 'Govt'))
    q = quote(title + ' previous year question papers PDF download')
    url = f'https://www.google.com/search?q={q}'
    return (
        f'<div class="card paper-card" data-cat="{cat}" data-scraped="1">'
        f'<div style="display:flex;justify-content:space-between;align-items:start;margin-bottom:.5rem;">'
        f'<span style="background:{bg};color:{tc};padding:.2rem .6rem;border-radius:4px;font-size:.8rem;font-weight:600;">{label}</span>'
        f'</div>'
        f'<h3 style="color:var(--primary);margin:.5rem 0;">{escape(title)}</h3>'
        f'<p style="color:#666;font-size:.875rem;margin-bottom:1rem;">Previous year question papers with answer keys.</p>'
        f'<a href="{url}" target="_blank" rel="nofollow noopener" class="btn btn--primary btn--small">Find Papers</a>'
        f'</div>'
    )


def update_previous_papers(site_root: Path) -> None:
    """Scan scraped job/result/admit pages and inject new exam cards into previous-papers.html."""
    pp_file = site_root / 'previous-papers.html'
    if not pp_file.exists():
        return

    html = pp_file.read_text(encoding='utf-8')

    # Collect titles already in the page (avoid duplicates)
    existing_titles: set[str] = set()
    for m in re.finditer(r'<h3 [^>]*>([^<]+)</h3>', html):
        existing_titles.add(m.group(1).strip().lower())

    # Gather exam titles from scraped detail pages (h1 tag)
    h1_re = re.compile(r'<h1[^>]*>\s*([^<]+)</h1>', re.I)
    new_cards: list[str] = []
    added_titles: set[str] = set()

    for folder in ['jobs', 'results', 'admit-cards']:
        for page in sorted((site_root / folder).rglob('*.html')):
            try:
                content = page.read_text(encoding='utf-8')
            except Exception:
                continue
            m = h1_re.search(content)
            if not m:
                continue
            title = m.group(1).strip()
            tl = title.lower()
            if tl in existing_titles or tl in added_titles:
                continue
            if len(title) < 10 or len(title) > 120:
                continue
            cat = get_category(title)
            new_cards.append(_build_paper_card(title, cat))
            added_titles.add(tl)

    if not new_cards:
        log.info('previous-papers: no new exams to add')
        return

    # Inject before closing </div><!-- #papers-grid -->
    inject_marker = '</div><!-- #papers-grid -->'
    if inject_marker not in html:
        # Fallback: inject before the <script> block at bottom of grid
        inject_marker = '<script>\n        function filterPapers'
        if inject_marker not in html:
            log.warning('previous-papers: could not find injection point')
            return
        html = html.replace(inject_marker, '\n' + '\n'.join(new_cards) + '\n\n        ' + inject_marker.lstrip(), 1)
    else:
        html = html.replace(inject_marker, '\n' + '\n'.join(new_cards) + '\n\n        ' + inject_marker, 1)

    pp_file.write_text(html, encoding='utf-8')
    log.info(f'previous-papers: added {len(new_cards)} new exam paper cards')


# ══════════════════════════════════════════════════════════
# DYNAMIC RESOURCES PAGE
# ══════════════════════════════════════════════════════════

_EXAM_RESOURCES: dict[str, dict] = {
    'upsc': {
        'icon': '🏛️', 'label': 'UPSC Civil Services',
        'color': '#1a237e',
        'topics': 'History · Polity · Geography · Economy · Environment · Current Affairs',
        'links': [
            ('Official Syllabus', 'https://upsc.gov.in/examinations/syllabus-materials'),
            ('Previous Year Papers', 'https://upsc.gov.in/examinations/previous-year-question-papers'),
            ('Laxmikant — Polity (free preview)', 'https://archive.org/search?query=laxmikant+indian+polity'),
            ('IGNOU Study Material', 'https://egyankosh.ac.in/'),
        ],
    },
    'ssc': {
        'icon': '📝', 'label': 'SSC (CGL / CHSL / MTS)',
        'color': '#b71c1c',
        'topics': 'Quantitative Aptitude · Reasoning · English · General Awareness',
        'links': [
            ('SSC Official Syllabus', 'https://ssc.nic.in/Portal/Syllabus'),
            ('Previous Papers', 'https://ssc.nic.in/Portal/QuestionPapers'),
            ('Jagran Josh Free SSC Material', 'https://www.jagranjosh.com/ssc'),
        ],
    },
    'railway': {
        'icon': '🚂', 'label': 'Railway (RRB / RRC)',
        'color': '#004d40',
        'topics': 'General Science · Maths · Reasoning · General Awareness · Technical (for ALP/JE)',
        'links': [
            ('RRB Official Portal', 'https://www.rrbcdg.gov.in'),
            ('RRB Syllabus & Pattern', 'https://www.rrcb.gov.in'),
            ('Testbook Free Railway Tests', 'https://testbook.com/free-mock-tests/rrb-ntpc'),
        ],
    },
    'banking': {
        'icon': '🏦', 'label': 'Banking (IBPS / SBI / RBI)',
        'color': '#1b5e20',
        'topics': 'Quantitative Aptitude · Reasoning · English · Banking Awareness · Computer',
        'links': [
            ('IBPS Official Syllabus', 'https://www.ibps.in'),
            ('RBI Opportunities', 'https://www.rbi.org.in/Scripts/Vacancies.aspx'),
            ('Bankersadda Free Tests', 'https://www.bankersadda.com/quiz'),
        ],
    },
    'defence': {
        'icon': '🪖', 'label': 'Defence (NDA / CDS / AFCAT)',
        'color': '#3e2723',
        'topics': 'Mathematics · English · General Knowledge · Physics (NDA) · Current Affairs',
        'links': [
            ('UPSC NDA Syllabus', 'https://upsc.gov.in/examinations/syllabus-materials'),
            ('AFCAT Official', 'https://afcat.cdac.in'),
            ('Join Indian Army', 'https://joinindianarmy.nic.in'),
            ('Join Indian Navy', 'https://www.joinindiannavy.gov.in'),
        ],
    },
    'police': {
        'icon': '👮', 'label': 'Police / Paramilitary',
        'color': '#212121',
        'topics': 'General Awareness · Reasoning · Physical Standards · Hindi/English',
        'links': [
            ('CISF Recruitment', 'https://cisfrectt.in'),
            ('CRPF Recruitment', 'https://www.crpf.gov.in/Recruitment.htm'),
            ('SSC CPO Syllabus', 'https://ssc.nic.in/Portal/Syllabus'),
        ],
    },
    'government': {
        'icon': '🏢', 'label': 'State PSC / Other Govt',
        'color': '#4a148c',
        'topics': 'State GK · Polity · History · Reasoning · Subject-specific (per exam)',
        'links': [
            ('UPPSC', 'https://uppsc.up.nic.in'),
            ('BPSC', 'https://bpsc.bih.nic.in'),
            ('MPPSC', 'https://mppsc.mp.gov.in'),
            ('RPSC', 'https://rpsc.rajasthan.gov.in'),
            ('Scholarships.gov.in', 'https://scholarships.gov.in'),
        ],
    },
}


def update_resources_section(site_root: Path) -> None:
    """Scan scraped pages to find active categories and inject exam-specific resources into resources.html."""
    res_file = site_root / 'resources.html'
    if not res_file.exists():
        return

    # Count pages per category
    cat_counts: dict[str, int] = {}
    for folder in ['jobs', 'results', 'admit-cards']:
        for subdir in (site_root / folder).iterdir():
            if subdir.is_dir():
                cat = subdir.name
                count = sum(1 for _ in subdir.glob('*.html'))
                if count:
                    cat_counts[cat] = cat_counts.get(cat, 0) + count

    active_cats = [c for c in _EXAM_RESOURCES if cat_counts.get(c, 0) > 0]
    if not active_cats:
        log.info('resources: no active categories found, skipping')
        return

    # Build HTML cards
    cards_html = []
    for cat in active_cats:
        r = _EXAM_RESOURCES[cat]
        count = cat_counts.get(cat, 0)
        links_html = ' &nbsp;·&nbsp; '.join(
            f'<a href="{url}" target="_blank" rel="noopener" style="color:{r["color"]};text-decoration:underline;font-size:.85rem;">{label} ↗</a>'
            for label, url in r['links']
        )
        cards_html.append(f'''        <div class="card" style="border-left:4px solid {r["color"]};">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.5rem;">
                <h3 style="color:{r["color"]};margin:0;font-size:1rem;">{r["icon"]} {r["label"]}</h3>
                <span class="badge" style="background:{r["color"]}1a;color:{r["color"]};white-space:nowrap;">{count} posts</span>
            </div>
            <p style="color:#555;font-size:.82rem;margin-bottom:.75rem;line-height:1.5;"><strong>Key topics:</strong> {r["topics"]}</p>
            <div style="line-height:2;">{links_html}</div>
        </div>''')

    section_html = (
        '<!-- #exam-resources-start -->\n'
        '        <h2 style="color:var(--primary);margin-bottom:.5rem;font-size:1.2rem;">🎯 Exam-Specific Preparation</h2>\n'
        '        <p style="color:#666;margin-bottom:1rem;font-size:.9rem;">Resources matched to exams currently active on this site — syllabus, official papers, and practice material.</p>\n'
        '        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1.25rem;margin-bottom:2.5rem;">\n'
        + '\n'.join(cards_html) + '\n'
        '        </div>\n'
        '        <!-- #exam-resources-end -->'
    )

    html = res_file.read_text(encoding='utf-8')

    # Replace between markers if they exist, else inject before NCERT section
    start_marker = '<!-- #exam-resources-start -->'
    end_marker = '<!-- #exam-resources-end -->'
    if start_marker in html and end_marker in html:
        html = re.sub(
            re.escape(start_marker) + r'.*?' + re.escape(end_marker),
            section_html,
            html,
            flags=re.DOTALL,
        )
    else:
        inject_before = '<!-- Free NCERT Books -->'
        if inject_before not in html:
            inject_before = '<h2 style="color:var(--primary);margin-bottom:.5rem;font-size:1.2rem;">📖 Free NCERT'
        if inject_before in html:
            html = html.replace(inject_before, section_html + '\n\n        ' + inject_before, 1)
        else:
            log.warning('resources: could not find injection point')
            return

    res_file.write_text(html, encoding='utf-8')
    log.info(f'resources: updated exam-specific section with {len(active_cats)} active categories')


# ══════════════════════════════════════════════════════════
# DISTRIBUTION & OFF-PAGE SEO
# ══════════════════════════════════════════════════════════

from email.utils import formatdate as _rfc822

def _rss_item(item: dict, kind: str) -> str:
    cat    = get_category(item.get('dept', ''))
    slug   = slugify(item.get('title', ''))
    url    = f'{SITE_URL}/{kind}s/{cat}/{slug}.html'
    title  = escape(item.get('title', ''))
    dept   = escape(item.get('dept', ''))
    date   = item.get('last_date') or item.get('result_date') or item.get('admit_release') or ''
    pub    = _rfc822(localtime=True)
    desc   = f'{title} — {dept}. Date: {date}. More details at {SITE_URL}.'
    return (
        f'<item>'
        f'<title>{title}</title>'
        f'<link>{url}</link>'
        f'<guid isPermaLink="true">{url}</guid>'
        f'<description>{escape(desc)}</description>'
        f'<category>{escape(dept)}</category>'
        f'<pubDate>{pub}</pubDate>'
        f'</item>'
    )


def generate_rss_feed(site_root: Path, jobs: list, results: list, admits: list) -> None:
    """Generate RSS 2.0 feeds: combined feed.xml + type-specific feeds."""
    feed_dir = site_root / 'feed'
    feed_dir.mkdir(exist_ok=True)

    def _channel(title: str, desc: str, items_xml: str) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">'
            '<channel>'
            f'<title>{escape(title)}</title>'
            f'<link>{SITE_URL}</link>'
            f'<description>{escape(desc)}</description>'
            '<language>en-IN</language>'
            f'<atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>'
            f'{items_xml}'
            '</channel></rss>'
        )

    jobs_xml    = ''.join(_rss_item(i, 'job')    for i in jobs[:50])
    results_xml = ''.join(_rss_item(i, 'result') for i in results[:50])
    admits_xml  = ''.join(_rss_item(i, 'admit')  for i in admits[:50])
    all_xml     = ''.join(
        _rss_item(i, k)
        for k, lst in [('job', jobs), ('result', results), ('admit', admits)]
        for i in lst[:25]
    )

    (site_root / 'feed.xml').write_text(
        _channel(f'{SITE_NAME} — All Updates', f'Latest government jobs, results, and admit cards from {SITE_URL}', all_xml),
        encoding='utf-8'
    )
    (feed_dir / 'jobs.xml').write_text(
        _channel(f'{SITE_NAME} — Latest Jobs', f'Latest government job notifications from {SITE_URL}', jobs_xml),
        encoding='utf-8'
    )
    (feed_dir / 'results.xml').write_text(
        _channel(f'{SITE_NAME} — Results', f'Latest exam results from {SITE_URL}', results_xml),
        encoding='utf-8'
    )
    (feed_dir / 'admit-cards.xml').write_text(
        _channel(f'{SITE_NAME} — Admit Cards', f'Latest admit card releases from {SITE_URL}', admits_xml),
        encoding='utf-8'
    )
    log.info(f'RSS feeds generated: feed.xml + feed/jobs|results|admit-cards.xml')


def generate_api_json(site_root: Path, jobs: list, results: list, admits: list) -> None:
    """Generate /api/latest.json — a public JSON endpoint for developers."""
    api_dir = site_root / 'api'
    api_dir.mkdir(exist_ok=True)

    def _entry(item: dict, kind: str) -> dict:
        cat  = get_category(item.get('dept', ''))
        slug = slugify(item.get('title', ''))
        return {
            'title':    item.get('title', ''),
            'dept':     item.get('dept', ''),
            'type':     kind,
            'category': cat,
            'date':     item.get('last_date') or item.get('result_date') or item.get('admit_release') or '',
            'url':      f'{SITE_URL}/{kind}s/{cat}/{slug}.html',
        }

    payload = {
        'updated': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'source':  SITE_URL,
        'attribution': f'Data from {SITE_NAME} ({SITE_URL}). Please link back when using.',
        'jobs':    [_entry(i, 'job')    for i in jobs[:20]],
        'results': [_entry(i, 'result') for i in results[:20]],
        'admits':  [_entry(i, 'admit')  for i in admits[:20]],
    }
    (api_dir / 'latest.json').write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    log.info('API JSON generated: api/latest.json')


def notify_telegram(new_items: list) -> None:
    """Post each newly scraped item to the Telegram channel via Bot API."""
    token   = os.getenv('TELEGRAM_BOT_TOKEN', '')
    channel = os.getenv('TELEGRAM_CHANNEL_ID', '')  # e.g. @naukridhaba
    if not token or not channel:
        log.info('Telegram: TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set — skipping')
        return
    import urllib.request, urllib.parse
    posted = 0
    for item in new_items[:8]:   # cap at 8 to avoid spam
        kind  = item.get('page_type', 'job')
        cat   = get_category(item.get('dept', ''))
        slug  = slugify(item.get('title', ''))
        url   = f'{SITE_URL}/{kind}s/{cat}/{slug}.html'
        date  = item.get('last_date') or item.get('result_date') or item.get('admit_release') or 'Check page'
        emoji = {'job': '💼', 'result': '📊', 'admit': '🎫'}.get(kind, '🔔')
        msg   = (
            f'{emoji} *{item["title"]}*\n'
            f'📅 {date}\n'
            f'🏛 {item.get("dept", "")}\n\n'
            f'👉 {url}'
        )
        try:
            data = urllib.parse.urlencode({
                'chat_id':    channel,
                'text':       msg,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': 'false',
            }).encode()
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{token}/sendMessage',
                data=data, method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.status == 200:
                    posted += 1
        except Exception as e:
            log.warning(f'Telegram post failed: {e}')
    if posted:
        log.info(f'Telegram: posted {posted} items to {channel}')


def ping_indexnow(new_urls: list) -> None:
    """Notify Bing/Yandex instantly about new pages via IndexNow API."""
    key = os.getenv('INDEXNOW_KEY', '')
    if not key or not new_urls:
        log.info('IndexNow: INDEXNOW_KEY not set or no new URLs — skipping')
        return
    import urllib.request
    payload = json.dumps({
        'host':        'naukridhaba.in',
        'key':         key,
        'keyLocation': f'{SITE_URL}/{key}.txt',
        'urlList':     new_urls[:100],
    }).encode()
    try:
        req = urllib.request.Request(
            'https://api.indexnow.org/indexnow',
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            log.info(f'IndexNow: pinged {len(new_urls)} URLs — HTTP {r.status}')
    except Exception as e:
        log.warning(f'IndexNow ping failed: {e}')


# ══════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════

def run(refresh_existing: bool = False, rebuild_only: bool = False) -> int:
    start = datetime.now()
    log.info('=' * 60)
    log.info(f'NAUKRI DHABA SCRAPER  started {start:%Y-%m-%d %H:%M:%S IST}')
    log.info('Source: sarkariresult.com')
    log.info('=' * 60)

    seen = load_seen()

    if rebuild_only:
        log.info('Rebuild-only mode: skipping source fetch and rebuilding listings from local detail pages.')
        existing_jobs = load_existing_detail_entries('job')
        existing_results = load_existing_detail_entries('result')
        existing_admits = load_existing_detail_entries('admit')

        replace_listing_sections(SITE_ROOT / 'latest-jobs.html', existing_jobs, 'job')
        replace_home_jobs_section(SITE_ROOT / 'index.html', existing_jobs, limit=10)
        replace_listing_sections(SITE_ROOT / 'results.html', existing_results, 'result')
        replace_listing_sections(SITE_ROOT / 'admit-cards.html', existing_admits, 'admit')

        try:
            generate_rss_feed(SITE_ROOT, existing_jobs, existing_results, existing_admits)
        except Exception as e:
            log.warning(f'RSS generation failed: {e}')
        try:
            generate_api_json(SITE_ROOT, existing_jobs, existing_results, existing_admits)
        except Exception as e:
            log.warning(f'API JSON generation failed: {e}')
        try:
            update_resources_section(SITE_ROOT)
        except Exception as e:
            log.warning(f'resources section update failed: {e}')

        elapsed = (datetime.now() - start).seconds
        log.info('\n' + '=' * 60)
        log.info(f'DONE in {elapsed}s  |  Rebuilt listings only')
        log.info('=' * 60 + '\n')
        return 0

    # ── 1. Scrape listing pages from all sources ───────────
    all_items: dict[str, list[dict]] = {'job': [], 'result': [], 'admit': []}
    successful_listings = 0
    # per-source counters: {src_name: {kind: count}}
    source_counts: dict[str, dict[str, int]] = {}

    for source in SOURCES:
        src_name = source['name']
        src_base = source['base']
        source_counts[src_name] = {'job': 0, 'result': 0, 'admit': 0}
        log.info(f'\n{"─"*40}')
        log.info(f'SOURCE: {src_name}  ({src_base})')
        log.info(f'{"─"*40}')

        for kind, url in source['urls'].items():
            log.info(f'\nFetching {kind.upper()} listing: {url}')
            soup = fetch(url)
            if not soup:
                log.warning(f'  [{src_name}] Could not fetch {kind} listing — skipping')
                continue
            successful_listings += 1
            raw = parse_listing(soup, kind, source_base=src_base)
            log.info(f'  Raw items from {src_name}: {len(raw)}')

            accepted = 0
            for item in raw:
                if not kind_matches_title(item.get('title', ''), kind):
                    continue
                # Skip items older than 2025
                iso = to_iso_date(item.get('date_str', ''))
                if iso and int(iso[:4]) < 2025:
                    log.debug(f'  [skip] pre-2025 item: {item["title"][:50]} ({iso})')
                    continue
                iid = item_id(item['title'], item['dept'])
                if not refresh_existing and iid in seen:
                    log.debug(f'  [skip] already seen: {item["title"][:50]}')
                    continue
                seen.add(iid)
                item['source'] = src_name
                all_items[kind].append(item)
                source_counts[src_name][kind] += 1
                accepted += 1
            log.info(f'  Accepted new {kind}s from {src_name}: {accepted}')

    if successful_listings == 0:
        log.error('All source listings failed. Aborting instead of reporting a false success.')
        return 2

    # Per-source summary table
    log.info('\n' + '─' * 60)
    log.info('SCRAPE SUMMARY — new posts per source:')
    log.info(f'  {"Source":<20} {"Jobs":>6} {"Results":>9} {"Admits":>8} {"Total":>7}')
    log.info(f'  {"─"*20} {"─"*6} {"─"*9} {"─"*8} {"─"*7}')
    for src_name, counts in source_counts.items():
        src_total = sum(counts.values())
        src_base = next(s['base'] for s in SOURCES if s['name'] == src_name)
        log.info(f'  {src_name:<20} {counts["job"]:>6} {counts["result"]:>9} {counts["admit"]:>8} {src_total:>7}   ({src_base})')
    log.info(f'  {"─"*20} {"─"*6} {"─"*9} {"─"*8} {"─"*7}')
    total_new = sum(len(v) for v in all_items.values())
    log.info(f'  {"TOTAL":<20} {len(all_items["job"]):>6} {len(all_items["result"]):>9} {len(all_items["admit"]):>8} {total_new:>7}')
    log.info('─' * 60)

    # ── 2. Scrape detail pages & generate HTML ─────────────
    generated: dict[str, list[dict]] = {'job': [], 'result': [], 'admit': []}
    staged: dict[str, list[dict]] = {'job': [], 'result': [], 'admit': []}
    staging_root = SITE_ROOT / STAGING_DIR
    staging_manifest: list[dict] = []

    # Build a lookup of primary-source sources for dedup
    primary_sources = {s['name'] for s in SOURCES if s.get('primary', False)}

    for kind, items in all_items.items():
        for item in items:
            src_name = item.get('source', 'unknown')
            is_primary = src_name in primary_sources
            log.info(f'\n[{kind.upper()}] {item["title"][:60]}  (source: {src_name})')
            log.info(f'  Detail URL: {item["detail_url"]}')

            detail_soup = fetch(item['detail_url'])
            if not detail_soup:
                log.warning(f'  Detail page unavailable — generating from listing data: {item["detail_url"]}')
            rich = parse_detail(detail_soup, item)
            rich['dept'] = rich.get('dept') or infer_dept(rich['title'])

            # Re-validate kind after detail parse (title may have changed)
            if not kind_matches_title(rich.get('title', ''), kind):
                log.info(f'  [skip] Title no longer matches kind={kind} after detail parse: {rich["title"][:60]}')
                continue

            try:
                if kind == 'job':
                    rel, html = build_job_page(rich)
                elif kind == 'result':
                    rel, html = build_result_page(rich)
                else:
                    rel, html = build_admit_page(rich)

                # For secondary sources: skip if the page already exists from a primary source
                if not is_primary and (SITE_ROOT / rel).exists():
                    log.info(f'  [skip] Already exists from primary source: {rel}')
                    continue

                if is_primary:
                    # Primary source → write directly to live site
                    # Remove stale copies from other category folders
                    parts = rel.split('/')  # e.g. 'jobs/police/slug.html'
                    if len(parts) == 3:
                        kind_dir, cat, fname = parts
                        remove_cross_category_duplicates(kind_dir, cat, fname.removesuffix('.html'))

                    out = SITE_ROOT / rel
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(html, encoding='utf-8')
                    log.info(f'  Written (LIVE): {rel}')
                    generated[kind].append(rich)
                else:
                    # Secondary source → write to staging/ for manual review
                    out = staging_root / rel
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(html, encoding='utf-8')
                    log.info(f'  Written (STAGING): {STAGING_DIR}/{rel}')
                    staged[kind].append(rich)
                    staging_manifest.append({
                        'source': src_name,
                        'kind': kind,
                        'title': rich.get('title', ''),
                        'dept': rich.get('dept', ''),
                        'rel_path': rel,
                        'detail_url': item.get('detail_url', ''),
                        'scraped_at': datetime.now().isoformat(),
                    })

            except Exception as exc:
                log.error(f'  Page build failed: {exc}', exc_info=True)

    # ── 2b. Save staging manifest ──────────────────────────
    if staging_manifest:
        manifest_file = staging_root / 'manifest.json'
        existing_manifest = []
        if manifest_file.exists():
            try:
                existing_manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, OSError):
                pass
        existing_manifest.extend(staging_manifest)
        staging_root.mkdir(parents=True, exist_ok=True)
        manifest_file.write_text(json.dumps(existing_manifest, indent=2, ensure_ascii=False), encoding='utf-8')
        log.info(f'\nStaging manifest updated: {len(staging_manifest)} new items ({manifest_file})')
        total_staged = sum(len(v) for v in staged.values())
        log.info(f'  Staged: Jobs={len(staged["job"])}, Results={len(staged["result"])}, AdmitCards={len(staged["admit"])} (total={total_staged})')
        log.info(f'  These items require manual review before going live.')

    # ── 3. Rebuild listing pages from canonical detail pages ───────────
    # This prevents list drift, missing items, and mixed-category bleed.
    log.info('\nRebuilding listing pages from detail pages...')
    existing_jobs = load_existing_detail_entries('job')
    existing_results = load_existing_detail_entries('result')
    existing_admits = load_existing_detail_entries('admit')

    replace_listing_sections(SITE_ROOT / 'latest-jobs.html', existing_jobs, 'job')
    replace_home_jobs_section(SITE_ROOT / 'index.html', existing_jobs, limit=10)
    replace_listing_sections(SITE_ROOT / 'results.html', existing_results, 'result')
    replace_listing_sections(SITE_ROOT / 'admit-cards.html', existing_admits, 'admit')

    # ── 4. Save seen set ───────────────────────────────────
    save_seen(seen)

    # ── 4b. Update previous-papers page with newly scraped exams ──
    try:
        update_previous_papers(SITE_ROOT)
    except Exception as e:
        log.warning(f'previous-papers update failed: {e}')

    # ── 4b2. Update resources page with active exam categories ──
    try:
        update_resources_section(SITE_ROOT)
    except Exception as e:
        log.warning(f'resources section update failed: {e}')

    # ── 4c. RSS feeds + JSON API ───────────────────────────
    all_jobs    = existing_jobs    + generated.get('job', [])
    all_results = existing_results + generated.get('result', [])
    all_admits  = existing_admits  + generated.get('admit', [])
    try:
        generate_rss_feed(SITE_ROOT, all_jobs, all_results, all_admits)
    except Exception as e:
        log.warning(f'RSS feed generation failed: {e}')
    try:
        generate_api_json(SITE_ROOT, all_jobs, all_results, all_admits)
    except Exception as e:
        log.warning(f'API JSON generation failed: {e}')

    # ── 4d. Telegram notification for new pages ────────────
    new_all = generated.get('job', []) + generated.get('result', []) + generated.get('admit', [])
    if new_all:
        try:
            notify_telegram(new_all)
        except Exception as e:
            log.warning(f'Telegram notification failed: {e}')

    # ── 4e. IndexNow ping for new pages ───────────────────
    if new_all:
        new_urls = []
        for item in new_all:
            kind = item.get('page_type', 'job')
            cat  = get_category(item.get('dept', ''))
            slug = slugify(item.get('title', ''))
            new_urls.append(f'{SITE_URL}/{kind}s/{cat}/{slug}.html')
        try:
            ping_indexnow(new_urls)
        except Exception as e:
            log.warning(f'IndexNow ping failed: {e}')

    # ── 5. Regenerate sitemap ──────────────────────────────
    import subprocess
    sitemap_py = SITE_ROOT / 'generate-sitemap.py'
    if sitemap_py.exists():
        try:
            subprocess.run([sys.executable, str(sitemap_py)], check=True, capture_output=True)
            log.info('Sitemap regenerated')
        except Exception as e:
            log.warning(f'Sitemap generation failed: {e}')

    # ── Done ───────────────────────────────────────────────
    elapsed = (datetime.now() - start).seconds
    total_gen = sum(len(v) for v in generated.values())

    # Per-source generated breakdown
    gen_by_source: dict[str, dict[str, int]] = {}
    for kind, items in generated.items():
        for item in items:
            src = item.get('source', 'unknown')
            gen_by_source.setdefault(src, {'job': 0, 'result': 0, 'admit': 0})
            gen_by_source[src][kind] += 1

    log.info('\n' + '=' * 60)
    log.info(f'DONE in {elapsed}s  |  Pages generated: {total_gen}')
    log.info(f'  Jobs={len(generated["job"])}, Results={len(generated["result"])}, AdmitCards={len(generated["admit"])}')
    if gen_by_source:
        log.info('  Pages generated per source:')
        for src, counts in gen_by_source.items():
            src_base = next((s['base'] for s in SOURCES if s['name'] == src), src)
            log.info(f'    {src:<20} Jobs={counts["job"]} Results={counts["result"]} Admits={counts["admit"]}   ({src_base})')
    log.info('=' * 60 + '\n')
    return 0


# ══════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Naukri Dhaba – sarkariresult.com scraper')
    parser.add_argument('--once', action='store_true', default=True,
                        help='Run once and exit (default)')
    parser.add_argument('--refresh-existing', action='store_true',
                        help='Rebuild pages for items currently present on the source listings')
    parser.add_argument('--rebuild-only', action='store_true',
                        help='Skip source scraping and rebuild listing pages from local detail pages')
    args = parser.parse_args()
    raise SystemExit(run(refresh_existing=args.refresh_existing, rebuild_only=args.rebuild_only))

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
from urllib.parse import quote, urljoin, urlparse

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

from site_config import REDIRECT_PATH, SITE_NAME, SITE_URL, SOURCE_BASE_URL, SOURCE_HOSTS, SOURCES

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
    'NABARD': 'banking', 'BANK': 'banking',
    'POLICE': 'police', 'CISF': 'police', 'BSF': 'police',
    'CRPF': 'police', 'ITBP': 'police', 'SSB': 'police',
    'ARMY': 'defence', 'NAVY': 'defence', 'AIRFORCE': 'defence',
    'IAF': 'defence', 'NDA': 'defence', 'CDS': 'defence',
    'DRDO': 'defence', 'HAL': 'defence',
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


# ══════════════════════════════════════════════════════════
# UTILITY HELPERS
# ══════════════════════════════════════════════════════════

def slugify(text: str) -> str:
    t = str(text).lower().strip()
    t = re.sub(r'[^\w\s-]', '', t)
    t = re.sub(r'[\s_]+', '-', t)
    t = re.sub(r'-{2,}', '-', t).strip('-')
    return t[:80]


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
    return official_url_or_empty(normalized)


def primary_cta_url(url: str, source_detail_url: str) -> str:
    if is_public_redirect(url):
        return ''
    normalized = normalize_url(url)
    if is_public_redirect(normalized):
        return ''
    return official_url_or_empty(normalized)


def normalize_title(text: str) -> str:
    title = clean(sanitize(text))
    title = re.sub(rf'\s*\|\s*{re.escape(SITE_NAME)}.*$', '', title, flags=re.I)
    title = re.sub(r'\b(\d{4})\s+\1\b', r'\1', title)
    title = re.sub(r'([A-Za-z0-9])(?=(Apply Online|Result|Admit Card))', r'\1 ', title)
    title = re.sub(r'\b(20\d{2})\s+(Apply Online|Result|Admit Card)\s+\1\b', r'\1 \2', title)
    return clean(title)


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

_session = requests.Session()
_session.headers.update(HEADERS)

_cf_session = None
if cloudscraper is not None:
    try:
        _cf_session = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
        )
        _cf_session.headers.update(HEADERS)
    except Exception as exc:
        log.warning(f'Cloudscraper init failed, falling back to requests: {exc}')
        _cf_session = None

def fetch(url: str, retries: int = 3) -> BeautifulSoup | None:
    sessions = [_session]
    if _cf_session is not None:
        sessions.insert(0, _cf_session)

    for attempt in range(1, retries + 1):
        for idx, session in enumerate(sessions):
            client_name = 'cloudscraper' if idx == 0 and _cf_session is not None else 'requests'
            try:
                log.debug(f'GET {url} via {client_name}')
                r = session.get(url, timeout=TIMEOUT)
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
    # Covers sarkariresult (TableLi/post-list), freejobalert (entry-content tables),
    # rojgarresult/sarkariexam (similar table-based layouts).
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
        if parsed.netloc.lower() not in SOURCE_HOSTS or len(path_parts) < 2:
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

    # ── Deduplicate extra_links ────────────────────────────
    seen_urls = set()
    unique_links = []
    for lnk in d['extra_links']:
        if lnk['url'] not in seen_urls:
            seen_urls.add(lnk['url'])
            unique_links.append(lnk)
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
    tabs = [
        ('latest-jobs.html', '💼 Latest Jobs', 'jobs'),
        ('results.html',     '📊 Results',      'results'),
        ('admit-cards.html', '🎫 Admit Cards',  'admit-cards'),
        ('resources.html',   '📚 Resources',    'resources'),
    ]
    desktop = '\n      '.join(
        f'<a href="/{u}" class="{"active" if k == active else ""}">{lbl}</a>'
        for u, lbl, k in tabs
    )
    mobile = '\n    '.join(f'<a href="/{u}">{lbl}</a>' for u, lbl, _ in tabs)
    return f'''<header class="header">
  <div class="container header__container">
    <a href="/" class="logo">📋 {SITE_NAME}</a>
    <nav class="nav nav--desktop">
      {desktop}
    </nav>
    <div style="display:flex;gap:1rem;align-items:center;">
      <button class="btn--icon" onclick="toggleDarkMode()" title="Toggle Dark Mode">🌓</button>
      <input type="checkbox" id="menu-toggle" style="display:none;">
      <label for="menu-toggle" class="btn--icon menu-toggle" style="display:none;font-size:1.5rem;cursor:pointer;">☰</label>
    </div>
  </div>
  <nav class="nav--mobile">
    <label for="menu-toggle" style="position:absolute;top:1rem;right:1rem;font-size:1.5rem;cursor:pointer;">✕</label>
    <a href="/">🏠 Home</a>
    {mobile}
  </nav>
  <style>.menu-toggle{{display:none!important}}@media(max-width:768px){{.nav--desktop{{display:none}}.menu-toggle{{display:block!important}}}}</style>
</header>'''


def _sidebar() -> str:
    return '''<aside class="sidebar">
  <div class="widget widget--telegram">
    <h3 class="widget__title">📢 Join Telegram</h3>
    <p style="margin-bottom:1rem;">Get instant job alerts on your phone!</p>
    <a href="https://t.me/naukridhaba" target="_blank" class="btn" style="background:#fff;color:#0088cc;width:100%;">Join Channel</a>
  </div>
  <div class="widget">
    <h3 class="widget__title">🔗 Quick Links</h3>
    <div class="footer__links">
      <a href="/latest-jobs.html">💼 Latest Jobs</a>
      <a href="/results.html">📊 Results</a>
      <a href="/admit-cards.html">🎫 Admit Cards</a>
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
        <a href="https://t.me/naukridhaba" class="share-btn share-btn--telegram" style="margin-top:1rem;display:inline-block;">Join Telegram</a>
      </div>
      <div>
        <h3 class="footer__title">Quick Links</h3>
        <div class="footer__links">
          <a href="/latest-jobs.html">Latest Jobs</a>
          <a href="/results.html">Results</a>
          <a href="/admit-cards.html">Admit Cards</a>
          <a href="/resources.html">Resources</a>
        </div>
      </div>
      <div>
        <h3 class="footer__title">Categories</h3>
        <div class="footer__links">
          <a href="/latest-jobs.html">UPSC Jobs</a>
          <a href="/latest-jobs.html">SSC Jobs</a>
          <a href="/latest-jobs.html">Railway Jobs</a>
          <a href="/latest-jobs.html">Banking Jobs</a>
          <a href="/latest-jobs.html">Defence Jobs</a>
          <a href="/latest-jobs.html">Police Jobs</a>
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
<script src="/js/ads-manager.js" defer></script>'''


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
    desc = (
        f"{title}: {dept} has released notification. "
        f"Last date: {d['last_date']}. Apply online at {SITE_NAME}."
    )
    apply_href = d.get('apply_url') or ''
    notification_href = d.get('notification_url') or ''

    apply_btn = (
        f'<a href="{apply_href}" target="_blank" rel="nofollow noopener noreferrer" '
        f'class="btn btn--primary btn--large">🚀 Apply Online / आवेदन करें</a>'
        if apply_href
        else '<span class="btn btn--primary btn--large" style="opacity:.6;cursor:default;">🚀 Apply Link Coming Soon</span>'
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
            f'<li><a href="{lnk["url"]}" target="_blank" rel="noopener">'
            f'{clean(lnk["label"])}</a></li>'
            for lnk in d['extra_links'] if lnk.get('url') and lnk['url'] != '#'
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
    ld_job = json.dumps({
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": title,
        "description": desc,
        "datePosted": date.today().isoformat(),
        "validThrough": to_iso_date(d['last_date']) or date.today().isoformat(),
        "employmentType": "FULL_TIME",
        "hiringOrganization": {"@type": "Organization", "name": dept},
        "jobLocation": {"@type": "Place", "address": {"@type": "PostalAddress", "addressCountry": "IN"}},
        "url": canon
    }, ensure_ascii=False)

    ld_bc = json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": SITE_NAME, "item": SITE_URL + '/'},
            {"@type": "ListItem", "position": 2, "name": "Jobs", "item": SITE_URL + '/latest-jobs.html'},
            {"@type": "ListItem", "position": 3, "name": dept, "item": SITE_URL + '/latest-jobs.html'},
            {"@type": "ListItem", "position": 4, "name": title, "item": canon},
        ]
    }, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="hi">
<head>
{_seo_head(title, desc, canon, dept)}
    <script type="application/ld+json">{ld_job}</script>
    <script type="application/ld+json">{ld_bc}</script>
    <script src="../../js/ads-manager.js" defer></script>
</head>
<body>
{detail_body_tracking_markup()}
{_header('jobs')}

<div class="content-wrapper container" style="margin-top:2rem;">
  <main>
    <article class="job-detail">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/">Home</a> &gt; <a href="/latest-jobs.html">Jobs</a> &gt; <span>{title}</span>
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

      <div class="share-section">
        <h3>📢 Share with Friends / दोस्तों को शेयर करें</h3>
        <button onclick="shareWhatsApp(window.location.href,'{title.replace(chr(39),'')}') " class="share-btn share-btn--whatsapp">WhatsApp</button>
        <button onclick="shareTelegram(window.location.href,'{title.replace(chr(39),'')}') " class="share-btn share-btn--telegram">Telegram</button>
        <button onclick="copyLink(window.location.href)" class="share-btn share-btn--copy">Copy Link</button>
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
    result_href = d.get('result_url') or ''
    scorecard_href = d.get('scorecard_url') or ''

    check_btn = (
        f'<a href="{result_href}" target="_blank" rel="nofollow noopener noreferrer" '
        f'class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;">'
        f'🎯 Check Result / परिणाम देखें</a>'
        if result_href
        else '<span class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;opacity:.7;cursor:default;">🎯 Result Link Coming Soon</span>'
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
            {"@type": "ListItem", "position": 2, "name": "Results", "item": SITE_URL + '/results.html'},
            {"@type": "ListItem", "position": 3, "name": dept, "item": SITE_URL + '/results.html'},
            {"@type": "ListItem", "position": 4, "name": title, "item": canon},
        ]
    }, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="hi">
<head>
{_seo_head(title + ' - Result', desc, canon, dept)}
    <script type="application/ld+json">{ld_ev}</script>
    <script type="application/ld+json">{ld_bc}</script>
    <script src="../../js/ads-manager.js" defer></script>
</head>
<body>
{detail_body_tracking_markup()}
{_header('results')}

<div class="content-wrapper container" style="margin-top:2rem;">
  <main>
    <article class="result-detail">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/">Home</a> &gt; <a href="/results.html">Results</a> &gt; <span>{title}</span>
      </nav>

      <h1 style="color:var(--primary);">📊 {title}</h1>

      <div class="nd-ad ad-slot" data-ad-slot="content-top"></div>

      <div style="background:#e8f5e9;padding:1.5rem;border-radius:8px;text-align:center;margin:1.5rem 0;">
        <div style="display:inline-block;background:var(--success);color:#fff;padding:.5rem 1rem;border-radius:4px;font-weight:bold;margin-bottom:1rem;">✅ Declared / घोषित</div>
        <p style="color:#666;margin-bottom:1.5rem;">Result Date: {d["result_date"]}</p>
        {check_btn}
        {scorecard_btn}
        <div style="margin-top:1rem;">
          <a href="/latest-jobs.html" class="btn btn--secondary">🔍 Browse Latest Jobs</a>
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

      <div class="share-section">
        <h3>📢 Share with Friends</h3>
        <button onclick="shareWhatsApp(window.location.href,'{title.replace(chr(39),'')} Result Declared')" class="share-btn share-btn--whatsapp">WhatsApp</button>
        <button onclick="shareTelegram(window.location.href,'{title.replace(chr(39),'')} Result')" class="share-btn share-btn--telegram">Telegram</button>
        <button onclick="copyLink(window.location.href)" class="share-btn share-btn--copy">Copy Link</button>
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
    admit_href = d.get('admit_url') or ''

    dl_btn = (
        f'<a href="{admit_href}" target="_blank" rel="nofollow noopener noreferrer" '
        f'class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;">'
        f'📥 Download Admit Card / हॉल टिकट डाउनलोड करें</a>'
        if admit_href
        else '<span class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;opacity:.7;cursor:default;">📥 Admit Card Link Coming Soon</span>'
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
            {"@type": "ListItem", "position": 2, "name": "Admit Cards", "item": SITE_URL + '/admit-cards.html'},
            {"@type": "ListItem", "position": 3, "name": dept, "item": SITE_URL + '/admit-cards.html'},
            {"@type": "ListItem", "position": 4, "name": title, "item": canon},
        ]
    }, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="hi">
<head>
{_seo_head(title + ' - Admit Card', desc, canon, dept)}
    <script type="application/ld+json">{ld_ev}</script>
    <script type="application/ld+json">{ld_bc}</script>
    <script src="../../js/ads-manager.js" defer></script>
</head>
<body>
{detail_body_tracking_markup()}
{_header('admit-cards')}

<div class="content-wrapper container" style="margin-top:2rem;">
  <main>
    <article class="admit-detail">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/">Home</a> &gt; <a href="/admit-cards.html">Admit Cards</a> &gt; <span>{title}</span>
      </nav>

      <h1 style="color:var(--primary);">🎫 {title}</h1>

      <div class="nd-ad ad-slot" data-ad-slot="content-top"></div>

      <div style="background:#e8f5e9;padding:1.5rem;border-radius:8px;text-align:center;margin:1.5rem 0;">
        <div style="display:inline-block;background:var(--success);color:#fff;padding:.5rem 1rem;border-radius:4px;font-weight:bold;margin-bottom:1rem;">✅ Available / उपलब्ध</div>
        <p style="color:#666;margin-bottom:.5rem;">Released: {d["admit_release"]}</p>
        <p style="color:#666;font-weight:bold;margin-bottom:1.5rem;">📅 Exam Date: {d["exam_date"]}</p>
        {dl_btn}
        <div style="margin-top:1rem;">
          <a href="/results.html" class="btn btn--secondary">📊 Check Results</a>
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

      <div class="share-section">
        <h3>📢 Share with Friends</h3>
        <button onclick="shareWhatsApp(window.location.href,'{title.replace(chr(39),'')} Admit Card Available')" class="share-btn share-btn--whatsapp">WhatsApp</button>
        <button onclick="shareTelegram(window.location.href,'{title.replace(chr(39),'')} Admit Card')" class="share-btn share-btn--telegram">Telegram</button>
        <button onclick="copyLink(window.location.href)" class="share-btn share-btn--copy">Copy Link</button>
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
            path = f"jobs/{cat}/{slugify(title)}.html"
            date_label = e.get('last_date', '')
            btn  = 'Apply'
        elif kind == 'result':
            cat  = get_category(e.get('dept', ''))
            s    = slugify(title)
            if 'result' not in s:
                s += '-result'
            path = f"results/{cat}/{s}.html"
            date_label = e.get('result_date', '')
            btn  = 'View'
        else:
            cat  = get_category(e.get('dept', ''))
            s    = slugify(title)
            if 'admit' not in s and 'hall' not in s:
                s += '-admit-card'
            path = f"admit-cards/{cat}/{s}.html"
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
            path = f"jobs/{cat}/{slugify(title)}.html"
            date_label = e.get('last_date', '') or e.get('date_str', '')
            button = 'Apply'
        elif kind == 'result':
            cat = get_category(e.get('dept', ''))
            slug = slugify(title)
            if 'result' not in slug:
                slug += '-result'
            path = f"results/{cat}/{slug}.html"
            date_label = e.get('result_date', '') or e.get('date_str', '')
            button = 'View'
        else:
            cat = get_category(e.get('dept', ''))
            slug = slugify(title)
            if 'admit' not in slug and 'hall' not in slug:
                slug += '-admit-card'
            path = f"admit-cards/{cat}/{slug}.html"
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
    for path in sorted(base.rglob('*.html'), key=lambda p: p.stat().st_mtime, reverse=True):
        rel = path.relative_to(SITE_ROOT).as_posix()
        html = path.read_text(encoding='utf-8', errors='replace')
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.I | re.S)
        title = clean(re.sub(r'<[^>]+>', '', title_match.group(1))) if title_match else normalize_title(path.stem.replace('-', ' '))
        dept_match = re.search(r'info-item__label">[^<]*Department</span>\s*<span class="info-item__value">([^<]+)', html, re.I)
        dept = clean(dept_match.group(1)) if dept_match else infer_dept(title)
        date_label = 'Check Notification'

        if kind == 'job':
            match = re.search(r'Last Date to Apply Online</td><td[^>]*>([^<]+)</td>', html, re.I)
            date_label = clean(match.group(1)) if match else 'Check Notification'
            entries.append({'title': title, 'dept': dept, 'last_date': date_label})
        elif kind == 'result':
            match = re.search(r'Result Date:\s*([^<]+)</p>', html, re.I)
            date_label = clean(match.group(1)) if match else 'Check Notification'
            entries.append({'title': title, 'dept': dept, 'result_date': date_label})
        else:
            match = re.search(r'Exam Date:\s*([^<]+)</p>', html, re.I)
            date_label = clean(match.group(1)) if match else 'Check Notification'
            entries.append({'title': title, 'dept': dept, 'exam_date': date_label})

    return entries


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

        elapsed = (datetime.now() - start).seconds
        log.info('\n' + '=' * 60)
        log.info(f'DONE in {elapsed}s  |  Rebuilt listings only')
        log.info('=' * 60 + '\n')
        return 0

    # ── 1. Scrape listing pages from all sources ───────────
    all_items: dict[str, list[dict]] = {'job': [], 'result': [], 'admit': []}
    successful_listings = 0

    for source in SOURCES:
        src_name = source['name']
        src_base = source['base']
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
            log.info(f'  Raw items: {len(raw)}')

            for item in raw:
                if not kind_matches_title(item.get('title', ''), kind):
                    continue
                iid = item_id(item['title'], item['dept'])
                if not refresh_existing and iid in seen:
                    log.debug(f'  [skip] already seen: {item["title"][:50]}')
                    continue
                seen.add(iid)
                item['source'] = src_name
                all_items[kind].append(item)

    if successful_listings == 0:
        log.error('All source listings failed. Aborting instead of reporting a false success.')
        return 2

    total_new = sum(len(v) for v in all_items.values())
    log.info(f'\nNew items to process: {total_new}  '
             f'(jobs={len(all_items["job"])}, '
             f'results={len(all_items["result"])}, '
             f'admits={len(all_items["admit"])})')

    # ── 2. Scrape detail pages & generate HTML ─────────────
    generated: dict[str, list[dict]] = {'job': [], 'result': [], 'admit': []}

    for kind, items in all_items.items():
        for item in items:
            log.info(f'\n[{kind.upper()}] {item["title"][:60]}')
            log.info(f'  Detail URL: {item["detail_url"]}')

            detail_soup = fetch(item['detail_url'])
            rich = parse_detail(detail_soup, item) if detail_soup else item
            rich['dept'] = rich.get('dept') or infer_dept(rich['title'])

            try:
                if kind == 'job':
                    rel, html = build_job_page(rich)
                elif kind == 'result':
                    rel, html = build_result_page(rich)
                else:
                    rel, html = build_admit_page(rich)

                out = SITE_ROOT / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(html, encoding='utf-8')
                log.info(f'  Written: {rel}')
                generated[kind].append(rich)

            except Exception as exc:
                log.error(f'  Page build failed: {exc}', exc_info=True)

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
    log.info('\n' + '=' * 60)
    log.info(f'DONE in {elapsed}s  |  Generated {total_gen} pages  |  '
             f'Jobs={len(generated["job"])}, Results={len(generated["result"])}, '
             f'AdmitCards={len(generated["admit"])}')
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

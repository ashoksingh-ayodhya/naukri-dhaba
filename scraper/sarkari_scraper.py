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
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ─── Check dependencies ────────────────────────────────────
try:
    import requests
    from bs4 import BeautifulSoup, Tag
except ImportError:
    print("Missing dependencies. Installing...")
    os.system(f"{sys.executable} -m pip install requests beautifulsoup4 lxml -q")
    import requests
    from bs4 import BeautifulSoup, Tag

# ══════════════════════════════════════════════════════════
# PATHS & CONSTANTS
# ══════════════════════════════════════════════════════════
SITE_ROOT   = Path(__file__).parent.parent
SCRAPER_DIR = Path(__file__).parent
LOG_DIR     = SCRAPER_DIR / 'logs'
SEEN_FILE   = SCRAPER_DIR / 'seen_items.json'

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
BASE          = 'https://www.sarkariresult.com'
URL_JOBS      = f'{BASE}/latestjob.php'
URL_RESULTS   = f'{BASE}/result.php'
URL_ADMITS    = f'{BASE}/admitcard.php'
URL_HOME      = BASE

# ── Our site ───────────────────────────────────────────────
SITE_URL  = 'https://www.naukridhaba.in'
SITE_NAME = 'Naukri Dhaba'

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
    'government': 'Sarkari Naukri 2026, Govt Jobs India, Online Form 2026',
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
    """Keep official govt URLs; replace any SarkariResult URL with '#'."""
    if not url:
        return '#'
    u = url.strip()
    if re.search(r'(?i)sarkariresult', u):
        return '#'
    if u.startswith('/'):
        return '#'                 # Relative SR links → drop
    if not u.startswith('http'):
        return '#'
    return u


def item_id(title: str, dept: str) -> str:
    return hashlib.md5(f"{title.lower().strip()}|{dept.lower().strip()}".encode()).hexdigest()[:14]


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


# ══════════════════════════════════════════════════════════
# HTTP FETCHER
# ══════════════════════════════════════════════════════════

_session = requests.Session()
_session.headers.update(HEADERS)

def fetch(url: str, retries: int = 3) -> BeautifulSoup | None:
    for attempt in range(1, retries + 1):
        try:
            log.debug(f'GET {url}')
            r = _session.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            time.sleep(DELAY)
            return BeautifulSoup(r.content, 'lxml')
        except Exception as exc:
            log.warning(f'Attempt {attempt}/{retries} failed for {url}: {exc}')
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

def parse_listing(soup: BeautifulSoup, page_type: str) -> list[dict]:
    """Extract all rows from a sarkariresult listing page."""
    items = []

    # Try several known wrapper selectors in priority order
    containers = (
        soup.select('#post-list table tr') or
        soup.select('.TableLi table tr') or
        soup.select('div.latestnews table tr') or
        soup.select('table.latestnews tr') or
        soup.select('table tr')          # Fallback: all tables
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

        detail_url = urljoin(BASE, link_tag['href'])

        # Skip header rows / navigation rows
        if title.lower() in ('post name', 'latest jobs', 'results', 'admit card', '#', ''):
            continue

        items.append({
            'title':      sanitize(title),
            'dept':       sanitize(dept) if dept else infer_dept(title),
            'date_str':   sanitize(date_str),
            'detail_url': detail_url,
            'page_type':  page_type,
        })

    log.info(f'  Listing parser found {len(items)} raw rows')
    return items


def infer_dept(title: str) -> str:
    """Guess department from post title."""
    tu = title.upper()
    for key, cat in DEPT_MAP.items():
        if key in tu:
            return key
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
        val   = clean(cells[1].get_text()) if len(cells) > 1 else ''

        # ── Important Dates ──────────────────────────────
        if re.search(r'application\s*begin|apply\s*start', label):
            d['app_begin'] = sanitize(val) or d['app_begin']

        elif re.search(r'last\s*date|closing\s*date', label):
            d['last_date'] = sanitize(val) or d['last_date']

        elif re.search(r'exam\s*date|examination\s*date', label):
            d['exam_date'] = sanitize(val) or d['exam_date']

        elif re.search(r'result\s*date|declaration\s*date', label):
            d['result_date'] = sanitize(val) or d['result_date']

        elif re.search(r'admit\s*card\s*date|hall\s*ticket\s*date', label):
            d['admit_release'] = sanitize(val) or d['admit_release']

        # ── Application Fee ──────────────────────────────
        elif re.search(r'general|obc|ews|unreserved', label) and re.search(r'\d', val):
            d['fee_general'] = sanitize(val)

        elif re.search(r'sc\s*/\s*st|scheduled', label) and re.search(r'\d', val):
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
                href = sanitize_url(a.get('href', ''))
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

    # ── Also scrape any PDF / document links anywhere ─────
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href and not re.search(r'(?i)sarkariresult', href):
            if re.search(r'\.(pdf|PDF)$', href) or re.search(r'\.gov\.in', href):
                href_clean = sanitize_url(urljoin(BASE, href))
                if href_clean != '#':
                    lbl = sanitize(clean(a.get_text())) or 'Official Document'
                    if href_clean not in seen_urls:
                        seen_urls.add(href_clean)
                        d['extra_links'].append({'label': lbl, 'url': href_clean})

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
        <p style="color:#ccc;font-size:.9rem;line-height:1.6;">Your gateway to Sarkari Naukri. Latest govt jobs, results and admit cards.</p>
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
    cat  = get_category(dept)
    base_kw = SEO_KW.get(cat, SEO_KW['government'])
    kw = f"{base_kw}, {title}, {dept} 2026, Sarkari Naukri, {SITE_NAME}"
    if keywords_extra:
        kw += ', ' + keywords_extra
    og_title = f"{title} | {SITE_NAME}"
    desc_safe = (desc or og_title)[:160]
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
    <script src="../../js/tracking.js"></script>'''


# ── Job Page ───────────────────────────────────────────────
def build_job_page(d: dict) -> tuple[str, str]:
    title  = d['title']
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

    apply_btn = (
        f'<a href="{d["apply_url"]}" target="_blank" rel="noopener" '
        f'class="btn btn--primary btn--large">🚀 Apply Online / आवेदन करें</a>'
        if d.get('apply_url') and d['apply_url'] != '#'
        else '<span class="btn btn--primary btn--large" style="opacity:.6;cursor:default;">🚀 Apply Link Coming Soon</span>'
    )
    notif_btn = (
        f'<a href="{d["notification_url"]}" target="_blank" rel="noopener" '
        f'class="btn btn--secondary btn--large">📄 Download Notification</a>'
        if d.get('notification_url') and d['notification_url'] != '#'
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
        "validThrough": d['last_date'],
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
          <li>Click on <strong>"Apply Online"</strong> button above</li>
          <li>Register on official website with email and mobile number</li>
          <li>Fill the application form carefully / फॉर्म ध्यानपूर्वक भरें</li>
          <li>Upload required documents (Photo, Signature, Certificates)</li>
          <li>Pay application fee online (if applicable)</li>
          <li>Submit and save/print the confirmation page</li>
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
    title = d['title']
    dept  = d.get('dept', 'Government')
    cat   = get_category(dept)
    slug  = slugify(title)
    if 'result' not in slug:
        slug += '-result'
    rel   = f'results/{cat}/{slug}.html'
    canon = f'{SITE_URL}/{rel}'
    desc  = f"{title}: Result declared. Check your result at {SITE_NAME}. Result date: {d['result_date']}."

    check_btn = (
        f'<a href="{d["result_url"]}" target="_blank" rel="noopener" '
        f'class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;">'
        f'🎯 Check Result / परिणाम देखें</a>'
        if d.get('result_url') and d['result_url'] != '#'
        else '<a href="#" class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;opacity:.7;">🎯 Result Link Coming Soon</a>'
    )
    scorecard_btn = (
        f'<a href="{d["scorecard_url"]}" target="_blank" rel="noopener" '
        f'class="btn btn--secondary btn--large" style="display:inline-block;margin-bottom:1rem;">📄 Download Scorecard</a>'
        if d.get('scorecard_url') and d['scorecard_url'] != '#'
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
        "@type": "Event",
        "name": title,
        "description": desc,
        "startDate": date.today().isoformat(),
        "organizer": {"@type": "Organization", "name": dept},
        "location": {"@type": "VirtualLocation", "url": canon}
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
          <li>Click on <strong>"Check Result"</strong> button above</li>
          <li>Enter your Roll Number / Registration ID</li>
          <li>Enter Date of Birth if required</li>
          <li>View your result and download / save it</li>
          <li>Take a printout for future reference</li>
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
    title = d['title']
    dept  = d.get('dept', 'Government')
    cat   = get_category(dept)
    slug  = slugify(title)
    if 'admit' not in slug and 'hall' not in slug:
        slug += '-admit-card'
    rel   = f'admit-cards/{cat}/{slug}.html'
    canon = f'{SITE_URL}/{rel}'
    desc  = f"Download {title} admit card / hall ticket at {SITE_NAME}. Exam date: {d['exam_date']}."

    dl_btn = (
        f'<a href="{d["admit_url"]}" target="_blank" rel="noopener" '
        f'class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;">'
        f'📥 Download Admit Card / हॉल टिकट डाउनलोड करें</a>'
        if d.get('admit_url') and d['admit_url'] != '#'
        else '<a href="#" class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;opacity:.7;">📥 Admit Card Link Coming Soon</a>'
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
        "@type": "Event",
        "name": title,
        "description": desc,
        "startDate": date.today().isoformat(),
        "organizer": {"@type": "Organization", "name": dept},
        "location": {"@type": "VirtualLocation", "url": canon}
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
          <li>Carry <strong>printed admit card</strong> (colour preferred)</li>
          <li>Bring valid <strong>photo ID</strong> (Aadhar / PAN / Voter ID)</li>
          <li>Reach centre <strong>1 hour before</strong> reporting time</li>
          <li>Verify exam date, time and centre address carefully</li>
          <li>No electronic devices allowed (mobile, smartwatch, calculator)</li>
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
    Add new rows to the top of a listing HTML page.
    kind: 'job' | 'result' | 'admit'
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


# ══════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════

def run():
    start = datetime.now()
    log.info('=' * 60)
    log.info(f'NAUKRI DHABA SCRAPER  started {start:%Y-%m-%d %H:%M:%S IST}')
    log.info('Source: sarkariresult.com')
    log.info('=' * 60)

    seen = load_seen()

    # ── 1. Scrape listing pages ────────────────────────────
    listing_data = [
        (URL_JOBS,    'job'),
        (URL_RESULTS, 'result'),
        (URL_ADMITS,  'admit'),
    ]

    all_items: dict[str, list[dict]] = {'job': [], 'result': [], 'admit': []}

    for url, kind in listing_data:
        log.info(f'\nFetching {kind.upper()} listing: {url}')
        soup = fetch(url)
        if not soup:
            continue
        raw = parse_listing(soup, kind)
        log.info(f'  Raw items: {len(raw)}')

        for item in raw:
            iid = item_id(item['title'], item['dept'])
            if iid in seen:
                log.debug(f'  [skip] already seen: {item["title"][:50]}')
                continue
            seen.add(iid)
            all_items[kind].append(item)

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
                log.info(f'  ✅ Written: {rel}')
                generated[kind].append(rich)

            except Exception as exc:
                log.error(f'  ❌ Page build failed: {exc}', exc_info=True)

    # ── 3. Update listing pages ────────────────────────────
    log.info('\nUpdating listing pages…')
    if generated['job']:
        prepend_to_listing(SITE_ROOT / 'latest-jobs.html', generated['job'], 'job')
        prepend_to_listing(SITE_ROOT / 'index.html',       generated['job'][:5], 'job')

    if generated['result']:
        prepend_to_listing(SITE_ROOT / 'results.html', generated['result'], 'result')

    if generated['admit']:
        prepend_to_listing(SITE_ROOT / 'admit-cards.html', generated['admit'], 'admit')

    # ── 4. Save seen set ───────────────────────────────────
    save_seen(seen)

    # ── 5. Regenerate sitemap ──────────────────────────────
    import subprocess
    sitemap_py = SITE_ROOT / 'generate-sitemap.py'
    if sitemap_py.exists():
        try:
            subprocess.run([sys.executable, str(sitemap_py)], check=True, capture_output=True)
            log.info('Sitemap regenerated ✅')
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


# ══════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Naukri Dhaba – sarkariresult.com scraper')
    parser.add_argument('--once', action='store_true', default=True,
                        help='Run once and exit (default)')
    args = parser.parse_args()
    run()

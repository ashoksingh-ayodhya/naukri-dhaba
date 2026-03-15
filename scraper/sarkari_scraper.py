#!/usr/bin/env python3
"""
============================================================
NAUKRI DHABA - DAILY SCRAPER BOT
File: scraper/sarkari_scraper.py
============================================================

Scrapes official Indian government job portals daily and
generates HTML pages for Naukri Dhaba website.

SOURCES SCRAPED:
  - Employment News India (employmentnews.gov.in)
  - UPSC (upsc.gov.in)
  - SSC (ssc.gov.in)
  - IBPS (ibps.in)
  - NTA (nta.ac.in)
  - RRB / Indian Railways (indianrailways.gov.in)

FEATURES:
  - Removes all SarkariResult references, replaces with Naukri Dhaba
  - Generates proper SEO-optimised HTML pages
  - Adds Rich JSON-LD structured data
  - Updates listing pages (latest-jobs.html, results.html, admit-cards.html)
  - Regenerates sitemap after scraping
  - Logs all activity to scraper/logs/scraper.log

USAGE:
  python3 scraper/sarkari_scraper.py          # Run once
  python3 scraper/sarkari_scraper.py --daemon  # Run as scheduler (daily)

SETUP CRON (alternative):
  0 6 * * * cd /path/to/naukri-dhaba && python3 scraper/sarkari_scraper.py >> scraper/logs/cron.log 2>&1
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
import schedule
from datetime import datetime, date, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse, quote

try:
    import requests
    from bs4 import BeautifulSoup
    from dateutil import parser as dateparser
except ImportError:
    print("ERROR: Missing dependencies. Run: pip3 install -r scraper/requirements.txt")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════
SITE_ROOT = Path(__file__).parent.parent
SITE_URL = 'https://www.naukridhaba.in'
SITE_NAME = 'Naukri Dhaba'
SCRAPER_DIR = Path(__file__).parent
LOG_DIR = SCRAPER_DIR / 'logs'
SEEN_JOBS_FILE = SCRAPER_DIR / 'seen_jobs.json'

LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'scraper.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger('NaukriScraper')

# Request headers - polite browser-like headers
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/121.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
}

REQUEST_DELAY = 3  # Seconds between requests (polite crawling)
REQUEST_TIMEOUT = 15

# Banned terms to replace in all content
BANNED_TERMS = [
    'sarkariresult', 'sarkari result', 'SarkariResult',
    'SarkariResults', 'sarkariresults',
    'www.sarkariresult.com', 'sarkariresult.com',
    'doc.sarkariresults.org.in', 'sarkariresults.org.in',
]

# Department category mappings
DEPT_CATEGORY = {
    'UPSC': 'upsc', 'SSC': 'ssc', 'RAILWAY': 'railway', 'RRB': 'railway',
    'RRC': 'railway', 'IBPS': 'banking', 'SBI': 'banking', 'RBI': 'banking',
    'POLICE': 'police', 'CISF': 'police', 'BSF': 'police', 'CRPF': 'police',
    'ARMY': 'defence', 'NAVY': 'defence', 'AIR FORCE': 'defence', 'NDA': 'defence',
    'CDS': 'defence', 'DRDO': 'defence', 'NTA': 'government', 'NEET': 'government',
    'JEE': 'government', 'CUET': 'government',
}

# SEO Keywords for government jobs in India
SEO_KEYWORDS = {
    'upsc': ['UPSC', 'Civil Services', 'IAS', 'IPS', 'IFS', 'UPSC exam 2026'],
    'ssc': ['SSC', 'Staff Selection Commission', 'CGL', 'CHSL', 'MTS', 'GD Constable'],
    'railway': ['Railway Jobs', 'RRB', 'Group D', 'NTPC', 'ALP', 'Loco Pilot', 'Indian Railways'],
    'banking': ['Bank Jobs', 'IBPS', 'SBI', 'RBI', 'PO', 'Clerk', 'Bank Bharti'],
    'police': ['Police Jobs', 'Constable', 'SI', 'Inspector', 'CRPF', 'BSF', 'CISF'],
    'defence': ['Defence Jobs', 'Army', 'Navy', 'Air Force', 'NDA', 'CDS'],
    'government': ['Sarkari Naukri', 'Govt Jobs', 'Government Jobs India 2026', 'Online Form'],
}


# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def clean_text(text):
    """Clean and normalize text."""
    if not text:
        return ''
    text = str(text).strip()
    text = re.sub(r'\s+', ' ', text)
    # Replace banned terms
    for term in BANNED_TERMS:
        text = re.sub(re.escape(term), SITE_NAME, text, flags=re.IGNORECASE)
    return text


def clean_url(url):
    """Remove/replace sarkariresult URLs."""
    if not url:
        return '#'
    for term in BANNED_TERMS:
        if term.lower() in url.lower():
            return '#'
    return url


def slugify(text):
    """Convert text to URL-friendly slug."""
    text = str(text).lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text[:80]  # Max 80 chars for URL


def get_dept_category(dept_name):
    """Get category folder for a department."""
    dept_upper = str(dept_name).upper()
    for key, cat in DEPT_CATEGORY.items():
        if key in dept_upper:
            return cat
    return 'government'


def get_job_id(title, dept):
    """Generate unique ID for deduplication."""
    return hashlib.md5(f"{title}|{dept}".encode()).hexdigest()[:12]


def load_seen_jobs():
    """Load set of already processed job IDs."""
    if SEEN_JOBS_FILE.exists():
        try:
            with open(SEEN_JOBS_FILE, 'r') as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def save_seen_jobs(seen):
    """Save set of processed job IDs."""
    with open(SEEN_JOBS_FILE, 'w') as f:
        json.dump(list(seen), f)


def fetch_page(url, retries=3):
    """Fetch a URL with retries and polite delay."""
    for attempt in range(retries):
        try:
            log.info(f"Fetching: {url}")
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return resp.text
        except requests.RequestException as e:
            log.warning(f"Attempt {attempt+1} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(REQUEST_DELAY * (attempt + 1))
    log.error(f"Failed to fetch {url} after {retries} attempts")
    return None


# ══════════════════════════════════════════════════════════════
# HTML PAGE GENERATORS
# ══════════════════════════════════════════════════════════════

def build_seo_meta(page_type, title, dept, location, description, canonical_url, date_str='', keywords_extra=''):
    """Build comprehensive SEO meta tags for a page."""
    # Auto-generate keywords from job title + dept + location
    dept_kws = SEO_KEYWORDS.get(get_dept_category(dept), SEO_KEYWORDS['government'])
    base_keywords = [
        title, dept, location,
        f"{dept} Jobs 2026", f"{title} 2026",
        f"Sarkari Naukri {dept}", f"{dept} {page_type} 2026",
        "Government Jobs India", "Sarkari Result 2026",
        "Naukri Dhaba"
    ] + dept_kws[:3]
    if keywords_extra:
        base_keywords.extend(keywords_extra.split(','))

    keywords_str = ', '.join([k for k in base_keywords if k and k != 'nan'])

    og_title = f"{title} | {SITE_NAME}"
    og_description = description[:160] if description else f"{title} - Apply online at {SITE_NAME}"

    return f'''    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {page_type.replace('-', ' ').title()} | {SITE_NAME}</title>
    <meta name="description" content="{og_description}">
    <meta name="keywords" content="{keywords_str}">
    <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
    <meta name="author" content="{SITE_NAME}">
    <link rel="canonical" href="{canonical_url}">
    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="{og_title}">
    <meta property="og:description" content="{og_description}">
    <meta property="og:url" content="{canonical_url}">
    <meta property="og:site_name" content="{SITE_NAME}">
    <meta property="og:locale" content="hi_IN">
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{og_title}">
    <meta name="twitter:description" content="{og_description}">
    <!-- Geo Tags for India -->
    <meta name="geo.region" content="IN">
    <meta name="geo.placename" content="{location if location and location != 'nan' else 'India'}">
    <link rel="stylesheet" href="{'/css/style.css' if '/' not in canonical_url.replace(SITE_URL+'/', '') else '../../css/style.css'}">
    <script src="{'/js/tracking.js' if '/' not in canonical_url.replace(SITE_URL+'/', '') else '../../js/tracking.js'}"></script>'''


def build_header(active_nav='jobs'):
    """Build common site header."""
    nav_items = [
        ('latest-jobs.html', '💼 Latest Jobs', 'jobs'),
        ('results.html', '📊 Results', 'results'),
        ('admit-cards.html', '🎫 Admit Cards', 'admit-cards'),
        ('resources.html', '📚 Resources', 'resources'),
    ]
    desktop_nav = '\n      '.join([
        f'<a href="/{url}" class="{"active" if key == active_nav else ""}">{label}</a>'
        for url, label, key in nav_items
    ])
    mobile_nav = '\n'.join([
        f'<a href="/{url}">{label}</a>'
        for url, label, key in nav_items
    ])
    return f'''<header class="header">
  <div class="container header__container">
    <a href="/" class="logo">📋 {SITE_NAME}</a>
    <nav class="nav nav--desktop">
      {desktop_nav}
    </nav>
    <div style="display:flex;gap:1rem;align-items:center;">
      <button class="btn--icon" onclick="toggleDarkMode()" title="Toggle Dark Mode">🌓</button>
      <input type="checkbox" id="menu-toggle" style="display:none;">
      <label for="menu-toggle" class="btn--icon menu-toggle" style="display:none;font-size:1.5rem;cursor:pointer;">☰</label>
    </div>
  </div>
  <nav class="nav--mobile">
    <label for="menu-toggle" style="position:absolute;top:1rem;right:1rem;font-size:1.5rem;cursor:pointer;">✕</label>
    <a href="/index.html">🏠 Home</a>
    {mobile_nav}
  </nav>
  <style>.menu-toggle{{display:none!important}}@media(max-width:768px){{.nav--desktop{{display:none}}.menu-toggle{{display:block!important}}}}</style>
</header>'''


def build_sidebar():
    """Build common sidebar widget."""
    return '''<aside class="sidebar">
  <div class="widget widget--telegram">
    <h3 class="widget__title">📢 Join Telegram</h3>
    <p style="margin-bottom:1rem;">Get instant job alerts on your phone!</p>
    <a href="https://t.me/naukridhaba" target="_blank" class="btn" style="background:#fff;color:#0088cc;width:100%;">Join Channel</a>
  </div>
  <div class="widget">
    <h3 class="widget__title">🛠️ Quick Tools</h3>
    <div class="footer__links">
      <a href="/eligibility-calculator.html">🎯 Eligibility Calculator</a>
      <a href="/latest-jobs.html">💼 Latest Jobs</a>
      <a href="/results.html">📊 Results</a>
      <a href="/admit-cards.html">🎫 Admit Cards</a>
    </div>
  </div>
  <div class="nd-ad ad-slot" data-ad-slot="sidebar-top" style="min-height:250px;">
    <p>Advertisement</p><p style="font-size:0.75rem;">300x250</p>
  </div>
</aside>'''


def build_footer():
    """Build common site footer."""
    year = date.today().year
    return f'''<footer class="footer">
  <div class="container">
    <div class="footer__grid">
      <div>
        <h3 class="footer__title">📋 {SITE_NAME}</h3>
        <p style="color:#ccc;font-size:0.9rem;line-height:1.6;">Your gateway to Sarkari Naukri. Latest government jobs, results, and admit cards.</p>
        <div style="margin-top:1rem;">
          <a href="https://t.me/naukridhaba" class="share-btn share-btn--telegram" style="margin:0;">Join Telegram</a>
        </div>
      </div>
      <div>
        <h3 class="footer__title">Quick Links</h3>
        <div class="footer__links">
          <a href="/latest-jobs.html">Latest Jobs</a>
          <a href="/results.html">Results</a>
          <a href="/admit-cards.html">Admit Cards</a>
          <a href="/resources.html">Resources &amp; Tools</a>
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
      <p>&copy; {year} {SITE_NAME}. All rights reserved.</p>
      <p>Disclaimer: We are not affiliated with any government organization. We only provide information.</p>
    </div>
  </div>
</footer>
<script src="/js/app.js"></script>
<script src="/js/ads-manager.js"></script>'''


def build_job_json_ld(job):
    """Build JobPosting schema.org structured data."""
    title = clean_text(job.get('title', ''))
    dept = clean_text(job.get('dept', ''))
    last_date = job.get('last_date', '')
    date_posted = job.get('date_posted', date.today().isoformat())
    location = clean_text(job.get('location', 'India'))
    posts = job.get('total_posts', '')
    apply_url = clean_url(job.get('apply_url', ''))
    notification_url = clean_url(job.get('notification_url', ''))

    schema = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": title,
        "description": f"{title} - {dept} - Apply online at {SITE_NAME}. Last date: {last_date}",
        "datePosted": date_posted,
        "validThrough": last_date,
        "employmentType": "FULL_TIME",
        "hiringOrganization": {
            "@type": "Organization",
            "name": dept,
            "sameAs": f"https://www.naukridhaba.in/latest-jobs.html"
        },
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressCountry": "IN",
                "addressLocality": location if location != 'India' else None
            }
        },
        "identifier": {
            "@type": "PropertyValue",
            "name": dept,
            "value": job.get('job_id', slugify(title))
        },
        "url": f"{SITE_URL}/jobs/{get_dept_category(dept)}/{slugify(title)}.html"
    }

    if posts and posts != 'nan' and posts != '':
        try:
            schema["totalJobOpenings"] = int(re.sub(r'[^\d]', '', str(posts)) or 0)
        except ValueError:
            pass

    if apply_url and apply_url != '#':
        schema["applicationContact"] = {
            "@type": "ContactPoint",
            "contactType": "Apply Online",
            "url": apply_url
        }

    # Remove None values
    def remove_none(obj):
        if isinstance(obj, dict):
            return {k: remove_none(v) for k, v in obj.items() if v is not None}
        return obj

    return json.dumps(remove_none(schema), ensure_ascii=False, indent=2)


def build_result_json_ld(result):
    """Build structured data for result pages."""
    title = clean_text(result.get('title', ''))
    dept = clean_text(result.get('dept', ''))
    result_date = result.get('result_date', date.today().isoformat())

    schema = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": title,
        "description": f"{title} result declared. Check your result at {SITE_NAME}.",
        "startDate": result_date,
        "endDate": result_date,
        "eventStatus": "https://schema.org/EventScheduled",
        "organizer": {
            "@type": "Organization",
            "name": dept,
        },
        "location": {
            "@type": "VirtualLocation",
            "url": f"{SITE_URL}/results.html"
        }
    }
    return json.dumps(schema, ensure_ascii=False, indent=2)


def build_admit_card_json_ld(admit):
    """Build structured data for admit card pages."""
    title = clean_text(admit.get('title', ''))
    dept = clean_text(admit.get('dept', ''))
    exam_date = admit.get('exam_date', '')
    release_date = admit.get('release_date', date.today().isoformat())

    schema = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": f"{title} - Exam",
        "description": f"Download {title} admit card at {SITE_NAME}.",
        "startDate": exam_date or release_date,
        "organizer": {
            "@type": "Organization",
            "name": dept
        },
        "location": {
            "@type": "VirtualLocation",
            "url": f"{SITE_URL}/admit-cards.html"
        },
        "offers": {
            "@type": "Offer",
            "name": "Admit Card Download",
            "url": f"{SITE_URL}/admit-cards.html",
            "price": "0",
            "priceCurrency": "INR"
        }
    }
    return json.dumps(schema, ensure_ascii=False, indent=2)


def build_breadcrumb_json_ld(items):
    """Build BreadcrumbList structured data."""
    elements = []
    for i, (name, url) in enumerate(items, 1):
        elements.append({
            "@type": "ListItem",
            "position": i,
            "name": name,
            "item": url
        })
    schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": elements
    }
    return json.dumps(schema, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════
# JOB PAGE GENERATOR
# ══════════════════════════════════════════════════════════════

def generate_job_page(job):
    """Generate complete HTML page for a job posting."""
    title = clean_text(job.get('title', ''))
    dept = clean_text(job.get('dept', ''))
    last_date = job.get('last_date', 'Check Notification')
    date_posted = job.get('date_posted', date.today().strftime('%d/%m/%Y'))
    total_posts = job.get('total_posts', '')
    age_min = job.get('age_min', 18)
    age_max = job.get('age_max', 35)
    location = clean_text(job.get('location', 'India'))
    qualification = clean_text(job.get('qualification', 'Check Notification'))
    apply_url = clean_url(job.get('apply_url', ''))
    notification_url = clean_url(job.get('notification_url', ''))
    exam_date = job.get('exam_date', 'As per Schedule')
    salary = clean_text(job.get('salary', 'As per Government Norms'))
    additional_links = job.get('additional_links', [])

    category = get_dept_category(dept)
    filename = slugify(title) + '.html'
    rel_path = f'jobs/{category}/{filename}'
    canonical = f'{SITE_URL}/{rel_path}'

    # SEO description
    posts_str = f"{total_posts} Posts" if total_posts and str(total_posts) not in ('nan', '', '0') else ''
    description = (
        f"{title}: {dept} has released notification for {posts_str}. "
        f"Last date to apply: {last_date}. "
        f"Apply online at {SITE_NAME}."
    ).strip(' .')

    # Build page
    year = date.today().year

    posts_display = str(total_posts) if total_posts and str(total_posts) not in ('nan', '', 'None') else 'Check Notification'
    apply_btn = (
        f'<a href="{apply_url}" target="_blank" rel="noopener" class="btn btn--primary btn--large">🚀 Apply Online / आवेदन करें</a>'
        if apply_url and apply_url != '#'
        else '<span class="btn btn--primary btn--large" style="opacity:0.6;cursor:default;">🚀 Apply Link Coming Soon</span>'
    )
    notif_btn = (
        f'<a href="{notification_url}" target="_blank" rel="noopener" class="btn btn--secondary btn--large">📄 Download Notification</a>'
        if notification_url and notification_url != '#'
        else ''
    )

    # Additional resources/links from scraper
    extra_links_html = ''
    if additional_links:
        links_items = '\n'.join([
            f'<li><a href="{clean_url(lnk.get("url","#"))}" target="_blank" rel="noopener">{clean_text(lnk.get("label","Link"))}</a></li>'
            for lnk in additional_links if lnk.get('url')
        ])
        extra_links_html = f'''
        <div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
          <h3 style="color:var(--primary);margin-top:0;">📎 Important Links / महत्वपूर्ण लिंक</h3>
          <ul style="line-height:2.2;">
            {links_items}
          </ul>
        </div>'''

    html = f'''<!DOCTYPE html>
<html lang="hi">
<head>
{build_seo_meta('Apply Online', title, dept, location, description, canonical, last_date)}
    <script type="application/ld+json">
{build_job_json_ld(job)}
    </script>
    <script type="application/ld+json">
{build_breadcrumb_json_ld([
    (SITE_NAME, SITE_URL + '/'),
    ('Latest Jobs', SITE_URL + '/latest-jobs.html'),
    (dept.upper(), SITE_URL + '/latest-jobs.html'),
    (title, canonical)
])}
    </script>
</head>
<body>
{build_header('jobs')}
    <div class="content-wrapper container" style="margin-top:2rem;">
        <main>
            <article class="job-detail">
                <nav class="breadcrumb" aria-label="Breadcrumb">
                    <a href="/">Home</a> &gt;
                    <a href="/latest-jobs.html">Jobs</a> &gt;
                    <a href="/latest-jobs.html">{dept}</a> &gt;
                    <span>{title}</span>
                </nav>

                <h1 style="color:var(--primary);margin-bottom:0.5rem;">
                    {title}
                    <span style="background:var(--secondary);color:#fff;padding:4px 12px;border-radius:4px;font-size:1rem;">{year}</span>
                </h1>

                <!-- Ad: content-top -->
                <div class="nd-ad ad-slot" data-ad-slot="content-top"></div>

                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-item__label">📅 Last Date</span>
                        <span class="info-item__value">{last_date}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-item__label">🏢 Department</span>
                        <span class="info-item__value">{dept}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-item__label">📊 Total Posts</span>
                        <span class="info-item__value">{posts_display}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-item__label">👤 Age Limit</span>
                        <span class="info-item__value">{age_min}-{age_max} Years</span>
                    </div>
                    <div class="info-item">
                        <span class="info-item__label">🎓 Qualification</span>
                        <span class="info-item__value" style="font-size:1rem;">{qualification}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-item__label">💰 Salary/Pay Scale</span>
                        <span class="info-item__value" style="font-size:1rem;">{salary}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-item__label">📍 Location</span>
                        <span class="info-item__value">{location}</span>
                    </div>
                </div>

                <div class="action-bar">
                    {apply_btn}
                    {notif_btn}
                </div>

                <div style="border-left:4px solid var(--primary);background:var(--surface);padding:1.5rem;margin:1.5rem 0;">
                    <h2 style="color:var(--primary);margin-top:0;">📋 Important Dates / महत्वपूर्ण तिथियां</h2>
                    <table style="width:100%;margin-top:1rem;border-collapse:collapse;">
                        <tr style="border-bottom:1px solid #eee;"><td style="padding:10px 0;color:#666;width:50%;">Notification Released</td><td style="padding:10px 0;font-weight:bold;">{date_posted}</td></tr>
                        <tr style="border-bottom:1px solid #eee;"><td style="padding:10px 0;color:#666;">Last Date to Apply</td><td style="padding:10px 0;font-weight:bold;color:var(--danger);">{last_date}</td></tr>
                        <tr style="border-bottom:1px solid #eee;"><td style="padding:10px 0;color:#666;">Exam Date</td><td style="padding:10px 0;font-weight:bold;">{exam_date}</td></tr>
                    </table>
                </div>

                <!-- Ad: content-mid -->
                <div class="nd-ad ad-slot" data-ad-slot="content-mid"></div>

                <div class="calculator">
                    <h3 style="margin-top:0;">🎯 Age Eligibility Calculator / आयु कैलकुलेटर</h3>
                    <p style="color:#666;font-size:0.875rem;">Age limit: {age_min}-{age_max} years (as on cutoff date). OBC: +3 yrs, SC/ST: +5 yrs relaxation.</p>
                    <div class="form-group">
                        <label>Date of Birth / जन्म तिथि:</label>
                        <input type="date" id="dob-input">
                    </div>
                    <div class="form-group">
                        <label>Category / वर्ग:</label>
                        <select id="category-select">
                            <option value="general">General / सामान्य</option>
                            <option value="obc">OBC / अन्य पिछड़ा वर्ग (+3 years)</option>
                            <option value="sc">SC / अनुसूचित जाति (+5 years)</option>
                            <option value="st">ST / अनुसूचित जनजाति (+5 years)</option>
                        </select>
                    </div>
                    <button onclick="checkEligibility({age_min}, {age_max})" class="btn btn--primary">Check Eligibility / योग्यता जांचें</button>
                    <div id="eligibility-result" style="display:none;margin-top:1rem;padding:1rem;border-radius:4px;"></div>
                </div>

                <div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
                    <h3 style="color:var(--primary);margin-top:0;">📝 How to Apply / आवेदन कैसे करें</h3>
                    <ol style="line-height:2.2;">
                        <li>Click on <strong>"Apply Online"</strong> button above</li>
                        <li>Register on official website with email and mobile number</li>
                        <li>Fill the application form carefully / फॉर्म ध्यानपूर्वक भरें</li>
                        <li>Upload required documents (Photo, Signature, Certificates)</li>
                        <li>Pay application fee (if applicable) online</li>
                        <li>Submit form and save/print confirmation page</li>
                    </ol>
                </div>

                {extra_links_html}

                <div class="share-section">
                    <h3>📢 Share with Friends / दोस्तों को शेयर करें</h3>
                    <button onclick="shareWhatsApp(window.location.href, '{title.replace(chr(39), '')}')" class="share-btn share-btn--whatsapp">WhatsApp</button>
                    <button onclick="shareTelegram(window.location.href, '{title.replace(chr(39), '')}')" class="share-btn share-btn--telegram">Telegram</button>
                    <button onclick="copyLink(window.location.href)" class="share-btn share-btn--copy">Copy Link</button>
                </div>

                <!-- Ad: content-bottom -->
                <div class="nd-ad ad-slot" data-ad-slot="content-bottom"></div>
            </article>
        </main>
        {build_sidebar()}
    </div>
{build_footer()}
</body>
</html>'''

    return rel_path, html


# ══════════════════════════════════════════════════════════════
# RESULT PAGE GENERATOR
# ══════════════════════════════════════════════════════════════

def generate_result_page(result):
    """Generate HTML page for a result."""
    title = clean_text(result.get('title', ''))
    dept = clean_text(result.get('dept', ''))
    result_date = result.get('result_date', date.today().strftime('%d/%m/%Y'))
    result_url = clean_url(result.get('result_url', ''))
    scorecard_url = clean_url(result.get('scorecard_url', ''))
    additional_links = result.get('additional_links', [])

    category = get_dept_category(dept)
    filename = slugify(title) + '-result.html'
    # Avoid double "result" in filename
    if filename.count('result') > 1:
        filename = slugify(title) + '.html'
    rel_path = f'results/{category}/{filename}'
    canonical = f'{SITE_URL}/{rel_path}'

    description = f"{title}: Result declared. Check your result online at {SITE_NAME}. Result date: {result_date}."

    check_result_btn = (
        f'<a href="{result_url}" target="_blank" rel="noopener" class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;">🎯 Check Result / परिणाम देखें</a>'
        if result_url and result_url != '#'
        else '<a href="#" class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;opacity:0.7;">🎯 Result Link Coming Soon</a>'
    )

    scorecard_btn = (
        f'<a href="{scorecard_url}" target="_blank" rel="noopener" class="btn btn--secondary btn--large" style="display:inline-block;margin-bottom:1rem;">📄 Download Scorecard</a>'
        if scorecard_url and scorecard_url != '#'
        else ''
    )

    # Additional resources
    extra_links_html = ''
    if additional_links:
        links_items = '\n'.join([
            f'<li><a href="{clean_url(lnk.get("url","#"))}" target="_blank" rel="noopener">{clean_text(lnk.get("label","Link"))}</a></li>'
            for lnk in additional_links if lnk.get('url')
        ])
        extra_links_html = f'''
        <div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
          <h3 style="color:var(--primary);margin-top:0;">📎 Important Links</h3>
          <ul style="line-height:2.2;">{links_items}</ul>
        </div>'''

    html = f'''<!DOCTYPE html>
<html lang="hi">
<head>
{build_seo_meta('Result', title, dept, 'India', description, canonical, result_date)}
    <script type="application/ld+json">
{build_result_json_ld(result)}
    </script>
    <script type="application/ld+json">
{build_breadcrumb_json_ld([
    (SITE_NAME, SITE_URL + '/'),
    ('Results', SITE_URL + '/results.html'),
    (dept, SITE_URL + '/results.html'),
    (title, canonical)
])}
    </script>
</head>
<body>
{build_header('results')}
    <div class="content-wrapper container" style="margin-top:2rem;">
        <main>
            <article class="result-detail">
                <nav class="breadcrumb" aria-label="Breadcrumb">
                    <a href="/">Home</a> &gt;
                    <a href="/results.html">Results</a> &gt;
                    <a href="/results.html">{dept}</a> &gt;
                    <span>{title}</span>
                </nav>

                <h1 style="color:var(--primary);">📊 {title}</h1>

                <!-- Ad: content-top -->
                <div class="nd-ad ad-slot" data-ad-slot="content-top"></div>

                <div style="background:#e8f5e9;padding:1.5rem;border-radius:8px;text-align:center;margin:1.5rem 0;">
                    <div style="display:inline-block;background:var(--success);color:#fff;padding:0.5rem 1rem;border-radius:4px;font-weight:bold;margin-bottom:1rem;">✅ Declared / घोषित</div>
                    <p style="color:#666;margin-bottom:1.5rem;">Result Date: {result_date}</p>

                    {check_result_btn}
                    {scorecard_btn}

                    <div style="margin-top:1rem;">
                        <a href="/latest-jobs.html" class="btn btn--secondary">🔍 Browse Latest Jobs</a>
                    </div>
                </div>

                <div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
                    <h3 style="color:var(--primary);margin-top:0;">📋 How to Check Result / परिणाम कैसे देखें</h3>
                    <ol style="line-height:2.2;">
                        <li>Click on <strong>"Check Result"</strong> button above</li>
                        <li>Enter your Roll Number / Registration ID</li>
                        <li>Enter Date of Birth if required</li>
                        <li>Click on Submit / View Result</li>
                        <li>Download and save your result / scorecard</li>
                        <li>Take printout for future reference</li>
                    </ol>
                </div>

                {extra_links_html}

                <!-- Ad: content-bottom -->
                <div class="nd-ad ad-slot" data-ad-slot="content-bottom"></div>

                <div class="share-section">
                    <h3>📢 Share with Friends</h3>
                    <button onclick="shareWhatsApp(window.location.href, '{title.replace(chr(39), '')} Result Declared')" class="share-btn share-btn--whatsapp">WhatsApp</button>
                    <button onclick="shareTelegram(window.location.href, '{title.replace(chr(39), '')} Result')" class="share-btn share-btn--telegram">Telegram</button>
                    <button onclick="copyLink(window.location.href)" class="share-btn share-btn--copy">Copy Link</button>
                </div>
            </article>
        </main>
        {build_sidebar()}
    </div>
{build_footer()}
</body>
</html>'''

    return rel_path, html


# ══════════════════════════════════════════════════════════════
# ADMIT CARD PAGE GENERATOR
# ══════════════════════════════════════════════════════════════

def generate_admit_card_page(admit):
    """Generate HTML page for an admit card."""
    title = clean_text(admit.get('title', ''))
    dept = clean_text(admit.get('dept', ''))
    release_date = admit.get('release_date', date.today().strftime('%d/%m/%Y'))
    exam_date = admit.get('exam_date', 'Check Admit Card')
    download_url = clean_url(admit.get('download_url', ''))
    additional_links = admit.get('additional_links', [])

    category = get_dept_category(dept)
    filename = slugify(title)
    if 'admit' not in filename and 'hall' not in filename:
        filename += '-admit-card'
    filename += '.html'
    rel_path = f'admit-cards/{category}/{filename}'
    canonical = f'{SITE_URL}/{rel_path}'

    description = f"Download {title} admit card / hall ticket at {SITE_NAME}. Exam date: {exam_date}. Direct official link."

    download_btn = (
        f'<a href="{download_url}" target="_blank" rel="noopener" class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;">📥 Download Admit Card / हॉल टिकट डाउनलोड करें</a>'
        if download_url and download_url != '#'
        else '<a href="#" class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;opacity:0.7;">📥 Admit Card Link Coming Soon</a>'
    )

    extra_links_html = ''
    if additional_links:
        links_items = '\n'.join([
            f'<li><a href="{clean_url(lnk.get("url","#"))}" target="_blank" rel="noopener">{clean_text(lnk.get("label","Link"))}</a></li>'
            for lnk in additional_links if lnk.get('url')
        ])
        extra_links_html = f'''
        <div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
          <h3 style="color:var(--primary);margin-top:0;">📎 Important Links</h3>
          <ul style="line-height:2.2;">{links_items}</ul>
        </div>'''

    html = f'''<!DOCTYPE html>
<html lang="hi">
<head>
{build_seo_meta('Admit Card', title, dept, 'India', description, canonical, exam_date)}
    <script type="application/ld+json">
{build_admit_card_json_ld(admit)}
    </script>
    <script type="application/ld+json">
{build_breadcrumb_json_ld([
    (SITE_NAME, SITE_URL + '/'),
    ('Admit Cards', SITE_URL + '/admit-cards.html'),
    (dept, SITE_URL + '/admit-cards.html'),
    (title, canonical)
])}
    </script>
</head>
<body>
{build_header('admit-cards')}
    <div class="content-wrapper container" style="margin-top:2rem;">
        <main>
            <article class="admit-detail">
                <nav class="breadcrumb" aria-label="Breadcrumb">
                    <a href="/">Home</a> &gt;
                    <a href="/admit-cards.html">Admit Cards</a> &gt;
                    <a href="/admit-cards.html">{dept}</a> &gt;
                    <span>{title}</span>
                </nav>

                <h1 style="color:var(--primary);">🎫 {title}</h1>

                <!-- Ad: content-top -->
                <div class="nd-ad ad-slot" data-ad-slot="content-top"></div>

                <div style="background:#e8f5e9;padding:1.5rem;border-radius:8px;text-align:center;margin:1.5rem 0;">
                    <div style="display:inline-block;background:var(--success);color:#fff;padding:0.5rem 1rem;border-radius:4px;font-weight:bold;margin-bottom:1rem;">✅ Available / उपलब्ध</div>
                    <p style="color:#666;margin-bottom:0.5rem;">Released: {release_date}</p>
                    <p style="color:#666;margin-bottom:1.5rem;font-weight:bold;">📅 Exam Date: {exam_date}</p>

                    {download_btn}

                    <div style="margin-top:1rem;">
                        <a href="/results.html" class="btn btn--secondary">📊 Check Results</a>
                    </div>
                </div>

                <div style="border-left:4px solid var(--danger);background:#fff3e0;padding:1.5rem;border-radius:0 8px 8px 0;margin:1.5rem 0;">
                    <h3 style="color:var(--danger);margin-top:0;">⚠️ Important Instructions / महत्वपूर्ण निर्देश</h3>
                    <ul style="line-height:1.8;">
                        <li>Carry <strong>printed admit card</strong> to exam center (color printout preferred)</li>
                        <li>Bring valid <strong>photo ID proof</strong> (Aadhar/PAN/Voter ID)</li>
                        <li>Reach exam center <strong>1 hour before</strong> reporting time</li>
                        <li>Check exam date, time, and center address carefully</li>
                        <li>No electronic devices allowed (mobile, calculator, smartwatch)</li>
                    </ul>
                </div>

                <div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
                    <h3 style="color:var(--primary);margin-top:0;">📋 Exam Day Checklist / परीक्षा दिन चेकलिस्ट</h3>
                    <ul style="list-style:none;padding:0;">
                        <li style="padding:0.5rem 0;">✅ Printed Admit Card (Color)</li>
                        <li style="padding:0.5rem 0;">✅ Valid Photo ID Proof (Aadhar/PAN/Voter ID)</li>
                        <li style="padding:0.5rem 0;">✅ Passport Size Photos (2-3 copies)</li>
                        <li style="padding:0.5rem 0;">✅ Black Ball Point Pen (2 pens)</li>
                        <li style="padding:0.5rem 0;">✅ Water Bottle (Transparent, without label)</li>
                    </ul>
                </div>

                {extra_links_html}

                <!-- Ad: content-bottom -->
                <div class="nd-ad ad-slot" data-ad-slot="content-bottom"></div>

                <div class="share-section">
                    <h3>📢 Share with Friends</h3>
                    <button onclick="shareWhatsApp(window.location.href, '{title.replace(chr(39), '')} Admit Card Available')" class="share-btn share-btn--whatsapp">WhatsApp</button>
                    <button onclick="shareTelegram(window.location.href, '{title.replace(chr(39), '')} Admit Card')" class="share-btn share-btn--telegram">Telegram</button>
                    <button onclick="copyLink(window.location.href)" class="share-btn share-btn--copy">Copy Link</button>
                </div>
            </article>
        </main>
        {build_sidebar()}
    </div>
{build_footer()}
</body>
</html>'''

    return rel_path, html


# ══════════════════════════════════════════════════════════════
# SCRAPERS - OFFICIAL GOVERNMENT PORTALS
# ══════════════════════════════════════════════════════════════

class EmploymentNewsScraper:
    """Scrape Employment News India - employmentnews.gov.in"""
    BASE_URL = 'https://www.employmentnews.gov.in'

    def scrape_jobs(self):
        """Scrape latest job notifications."""
        jobs = []
        url = f'{self.BASE_URL}/EN/NewItems.aspx'
        html = fetch_page(url)
        if not html:
            return jobs

        soup = BeautifulSoup(html, 'lxml')
        # Parse job listings table
        rows = soup.select('table tr')
        for row in rows[1:]:  # Skip header
            cells = row.find_all('td')
            if len(cells) < 3:
                continue
            try:
                title_cell = cells[0] if cells else None
                dept_cell = cells[1] if len(cells) > 1 else None
                date_cell = cells[2] if len(cells) > 2 else None

                if not title_cell:
                    continue

                title = clean_text(title_cell.get_text())
                dept = clean_text(dept_cell.get_text()) if dept_cell else 'Government'
                last_date = clean_text(date_cell.get_text()) if date_cell else ''

                link = title_cell.find('a')
                notification_url = urljoin(self.BASE_URL, link['href']) if link and link.get('href') else ''
                notification_url = clean_url(notification_url)

                if title and len(title) > 5:
                    jobs.append({
                        'title': title,
                        'dept': dept,
                        'last_date': last_date,
                        'date_posted': date.today().strftime('%d/%m/%Y'),
                        'notification_url': notification_url,
                        'source': 'Employment News',
                        'additional_links': [
                            {'label': 'Official Notification PDF', 'url': notification_url}
                        ] if notification_url else []
                    })
                    log.info(f"  Found job: {title[:60]}")
            except Exception as e:
                log.debug(f"Error parsing row: {e}")
                continue

        log.info(f"Employment News: Found {len(jobs)} jobs")
        return jobs


class UPSCScraper:
    """Scrape UPSC - upsc.gov.in"""
    BASE_URL = 'https://upsc.gov.in'

    def scrape_jobs(self):
        jobs = []
        urls = [
            f'{self.BASE_URL}/examinations/active-examinations',
            f'{self.BASE_URL}/examinations/examination-notifications',
        ]
        for url in urls:
            html = fetch_page(url)
            if not html:
                continue
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.views-row, .exam-item, li a, table tr')
            for item in items:
                try:
                    link = item.find('a') if item.name != 'a' else item
                    if not link or not link.get('href'):
                        continue
                    title = clean_text(link.get_text())
                    if len(title) < 10:
                        continue
                    href = urljoin(self.BASE_URL, link['href'])
                    href = clean_url(href)

                    jobs.append({
                        'title': title,
                        'dept': 'UPSC',
                        'last_date': 'Check Notification',
                        'date_posted': date.today().strftime('%d/%m/%Y'),
                        'location': 'All India',
                        'notification_url': href,
                        'source': 'UPSC',
                        'additional_links': [
                            {'label': 'Official UPSC Notification', 'url': href}
                        ]
                    })
                    log.info(f"  Found UPSC: {title[:60]}")
                except Exception as e:
                    log.debug(f"UPSC parse error: {e}")
        log.info(f"UPSC: Found {len(jobs)} items")
        return jobs

    def scrape_results(self):
        results = []
        url = f'{self.BASE_URL}/examinations/results'
        html = fetch_page(url)
        if not html:
            return results
        soup = BeautifulSoup(html, 'lxml')
        links = soup.select('a[href*="result"], a[href*="Result"]')
        for link in links:
            try:
                title = clean_text(link.get_text())
                if len(title) < 10:
                    continue
                href = urljoin(self.BASE_URL, link['href'])
                href = clean_url(href)
                results.append({
                    'title': title,
                    'dept': 'UPSC',
                    'result_date': date.today().strftime('%d/%m/%Y'),
                    'result_url': href,
                    'source': 'UPSC',
                    'additional_links': [
                        {'label': 'Official UPSC Result', 'url': href}
                    ]
                })
                log.info(f"  Found UPSC result: {title[:60]}")
            except Exception as e:
                log.debug(f"UPSC result parse error: {e}")
        log.info(f"UPSC Results: Found {len(results)} items")
        return results


class SSCScraper:
    """Scrape SSC - ssc.gov.in"""
    BASE_URL = 'https://ssc.gov.in'

    def scrape_jobs(self):
        jobs = []
        url = f'{self.BASE_URL}/portal/latest-news'
        html = fetch_page(url)
        if not html:
            return jobs
        soup = BeautifulSoup(html, 'lxml')
        items = soup.select('.news-item, .latest-news li, table tr, .notification-item')
        for item in items:
            try:
                link = item.find('a')
                if not link or not link.get('href'):
                    continue
                title = clean_text(link.get_text())
                if len(title) < 10:
                    continue
                href = urljoin(self.BASE_URL, link['href'])
                href = clean_url(href)

                is_result = any(w in title.lower() for w in ['result', 'merit list', 'final'])
                is_admit = any(w in title.lower() for w in ['admit card', 'hall ticket', 'call letter'])

                entry = {
                    'title': title,
                    'dept': 'SSC',
                    'date_posted': date.today().strftime('%d/%m/%Y'),
                    'location': 'All India',
                    'source': 'SSC',
                    'notification_url': href,
                    'additional_links': [
                        {'label': 'Official SSC Notification', 'url': href}
                    ]
                }
                if is_result:
                    entry['result_url'] = href
                    entry['result_date'] = date.today().strftime('%d/%m/%Y')
                elif is_admit:
                    entry['download_url'] = href
                    entry['release_date'] = date.today().strftime('%d/%m/%Y')
                    entry['exam_date'] = 'Check Admit Card'
                else:
                    entry['last_date'] = 'Check Notification'

                jobs.append(entry)
                log.info(f"  Found SSC: {title[:60]}")
            except Exception as e:
                log.debug(f"SSC parse error: {e}")
        log.info(f"SSC: Found {len(jobs)} items")
        return jobs


class IBPSScraper:
    """Scrape IBPS - ibps.in"""
    BASE_URL = 'https://www.ibps.in'

    def scrape_jobs(self):
        jobs = []
        url = f'{self.BASE_URL}/common-recruitment-process/'
        html = fetch_page(url)
        if not html:
            return jobs
        soup = BeautifulSoup(html, 'lxml')
        links = soup.select('a[href*="crp"], a[href*="ibps"], .notification a')
        for link in links:
            try:
                title = clean_text(link.get_text())
                if len(title) < 10:
                    continue
                href = urljoin(self.BASE_URL, link['href'])
                href = clean_url(href)

                jobs.append({
                    'title': title,
                    'dept': 'IBPS',
                    'last_date': 'Check Notification',
                    'date_posted': date.today().strftime('%d/%m/%Y'),
                    'location': 'All India',
                    'source': 'IBPS',
                    'notification_url': href,
                    'additional_links': [
                        {'label': 'Official IBPS Notification', 'url': href}
                    ]
                })
                log.info(f"  Found IBPS: {title[:60]}")
            except Exception as e:
                log.debug(f"IBPS parse error: {e}")
        log.info(f"IBPS: Found {len(jobs)} items")
        return jobs


class NTAScraper:
    """Scrape NTA - nta.ac.in"""
    BASE_URL = 'https://nta.ac.in'

    def scrape(self):
        items = []
        url = f'{self.BASE_URL}/en/pub_notice'
        html = fetch_page(url)
        if not html:
            return items
        soup = BeautifulSoup(html, 'lxml')
        rows = soup.select('table tr, .pub-notice-item, .notice-item')
        for row in rows:
            try:
                link = row.find('a')
                if not link or not link.get('href'):
                    continue
                title = clean_text(link.get_text())
                if len(title) < 10:
                    continue
                href = urljoin(self.BASE_URL, link['href'])
                href = clean_url(href)

                # Classify
                title_lower = title.lower()
                entry = {
                    'title': title,
                    'dept': 'NTA',
                    'date_posted': date.today().strftime('%d/%m/%Y'),
                    'location': 'All India',
                    'source': 'NTA',
                    'additional_links': [
                        {'label': 'Official NTA Notification', 'url': href}
                    ]
                }

                if any(w in title_lower for w in ['result', 'score card', 'merit']):
                    entry['result_url'] = href
                    entry['result_date'] = date.today().strftime('%d/%m/%Y')
                elif any(w in title_lower for w in ['admit card', 'hall ticket']):
                    entry['download_url'] = href
                    entry['release_date'] = date.today().strftime('%d/%m/%Y')
                    entry['exam_date'] = 'Check Admit Card'
                else:
                    entry['notification_url'] = href
                    entry['last_date'] = 'Check Notification'

                items.append(entry)
                log.info(f"  Found NTA: {title[:60]}")
            except Exception as e:
                log.debug(f"NTA parse error: {e}")
        log.info(f"NTA: Found {len(items)} items")
        return items


# ══════════════════════════════════════════════════════════════
# FILE WRITER
# ══════════════════════════════════════════════════════════════

def write_page(rel_path, html_content):
    """Write generated HTML to file."""
    output_path = SITE_ROOT / rel_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    log.info(f"  Written: {rel_path}")
    return output_path


def update_listing_page(listing_file, new_entries, entry_type='job'):
    """Update listing pages (latest-jobs.html, results.html, admit-cards.html)."""
    filepath = SITE_ROOT / listing_file
    if not filepath.exists():
        log.warning(f"Listing file not found: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Build new rows to prepend to table
    new_rows_html = []
    new_cards_html = []

    for entry in new_entries[:20]:  # Add up to 20 new entries
        title = clean_text(entry.get('title', ''))
        dept = clean_text(entry.get('dept', ''))

        if entry_type == 'job':
            category = get_dept_category(dept)
            page_path = f"jobs/{category}/{slugify(title)}.html"
            date_str = entry.get('last_date', 'Check Notification')
            badge_label = dept.upper()
            btn_label = 'Apply'
            btn_link = page_path
            display_date = date_str

        elif entry_type == 'result':
            category = get_dept_category(dept)
            fname = slugify(title)
            if 'result' not in fname:
                fname += '-result'
            page_path = f"results/{category}/{fname}.html"
            date_str = entry.get('result_date', date.today().strftime('%d/%m/%Y'))
            badge_label = dept.upper()
            btn_label = 'View'
            btn_link = page_path
            display_date = date_str

        else:  # admit-card
            category = get_dept_category(dept)
            fname = slugify(title)
            if 'admit' not in fname and 'hall' not in fname:
                fname += '-admit-card'
            page_path = f"admit-cards/{category}/{fname}.html"
            date_str = entry.get('exam_date', 'Check Admit Card')
            badge_label = dept.upper()
            btn_label = 'Download'
            btn_link = page_path
            display_date = date_str

        new_rows_html.append(f'''        <tr class="">
            <td>{badge_label}</td>
            <td><a href="{btn_link}" style="color:var(--primary);font-weight:600;">{title}</a></td>
            <td>{display_date}</td>
            <td><a href="{btn_link}" class="btn btn--small btn--primary">{btn_label}</a></td>
        </tr>''')

        new_cards_html.append(f'''                    <div class="card">
                        <div class="card__header">
                            <span class="badge">{badge_label}</span>
                        </div>
                        <h3 class="card__title">{title}</h3>
                        <p style="color:#666;font-size:0.875rem;">📅 {display_date}</p>
                        <a href="{btn_link}" class="btn btn--primary btn--block" style="margin-top:1rem;">{btn_label}</a>
                    </div>''')

    if not new_rows_html:
        return

    rows_str = '\n'.join(new_rows_html)
    cards_str = '\n'.join(new_cards_html)

    # Insert after <tbody>
    content = re.sub(r'(<tbody>)', r'\1\n' + rows_str, content, count=1)
    # Insert after <div class="cards">
    content = re.sub(r'(<div class="cards">)', r'\1\n' + cards_str, content, count=1)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    log.info(f"Updated listing page: {listing_file} with {len(new_entries)} new entries")


# ══════════════════════════════════════════════════════════════
# MAIN SCRAPER ORCHESTRATOR
# ══════════════════════════════════════════════════════════════

def run_scraper():
    """Main function - run all scrapers and generate pages."""
    log.info("=" * 60)
    log.info(f"NAUKRI DHABA SCRAPER - Run started at {datetime.now()}")
    log.info("=" * 60)

    seen_jobs = load_seen_jobs()
    new_jobs = []
    new_results = []
    new_admits = []

    # Run all scrapers
    scrapers = [
        ('Employment News', EmploymentNewsScraper(), 'job'),
        ('UPSC Jobs', UPSCScraper(), 'job'),
        ('UPSC Results', UPSCScraper(), 'result'),
        ('SSC', SSCScraper(), 'mixed'),
        ('IBPS', IBPSScraper(), 'job'),
        ('NTA', NTAScraper(), 'mixed'),
    ]

    for name, scraper, stype in scrapers:
        log.info(f"\nRunning {name} scraper...")
        try:
            if stype == 'job':
                items = scraper.scrape_jobs() if hasattr(scraper, 'scrape_jobs') else []
            elif stype == 'result':
                items = scraper.scrape_results() if hasattr(scraper, 'scrape_results') else []
            elif stype == 'mixed':
                items = scraper.scrape() if hasattr(scraper, 'scrape') else scraper.scrape_jobs() if hasattr(scraper, 'scrape_jobs') else []
            else:
                items = []

            for item in items:
                job_id = get_job_id(item.get('title', ''), item.get('dept', ''))
                if job_id in seen_jobs:
                    log.debug(f"  Skipping (already seen): {item.get('title', '')[:40]}")
                    continue

                seen_jobs.add(job_id)
                item['job_id'] = job_id

                # Classify item
                title_lower = item.get('title', '').lower()
                has_result = 'result_url' in item or any(w in title_lower for w in ['result', 'merit list', 'score card'])
                has_admit = 'download_url' in item or any(w in title_lower for w in ['admit card', 'hall ticket', 'call letter'])

                if has_result:
                    new_results.append(item)
                elif has_admit:
                    new_admits.append(item)
                else:
                    new_jobs.append(item)

        except Exception as e:
            log.error(f"Error in {name} scraper: {e}", exc_info=True)

    # Generate pages
    log.info(f"\nGenerating pages...")
    log.info(f"  New jobs: {len(new_jobs)}")
    log.info(f"  New results: {len(new_results)}")
    log.info(f"  New admit cards: {len(new_admits)}")

    generated_jobs = []
    generated_results = []
    generated_admits = []

    for job in new_jobs:
        try:
            rel_path, html = generate_job_page(job)
            write_page(rel_path, html)
            generated_jobs.append(job)
        except Exception as e:
            log.error(f"Error generating job page for {job.get('title', '')}: {e}")

    for result in new_results:
        try:
            rel_path, html = generate_result_page(result)
            write_page(rel_path, html)
            generated_results.append(result)
        except Exception as e:
            log.error(f"Error generating result page: {e}")

    for admit in new_admits:
        try:
            rel_path, html = generate_admit_card_page(admit)
            write_page(rel_path, html)
            generated_admits.append(admit)
        except Exception as e:
            log.error(f"Error generating admit card page: {e}")

    # Update listing pages
    if generated_jobs:
        update_listing_page('latest-jobs.html', generated_jobs, 'job')
        update_listing_page('index.html', generated_jobs[:5], 'job')

    if generated_results:
        update_listing_page('results.html', generated_results, 'result')

    if generated_admits:
        update_listing_page('admit-cards.html', generated_admits, 'admit-card')

    # Save seen jobs
    save_seen_jobs(seen_jobs)

    # Regenerate sitemap
    log.info("\nRegenerating sitemap...")
    try:
        import subprocess
        subprocess.run(
            ['python3', str(SITE_ROOT / 'generate-sitemap.py')],
            check=True, capture_output=True
        )
        log.info("Sitemap regenerated successfully")
    except Exception as e:
        log.warning(f"Sitemap generation failed: {e}")

    total = len(generated_jobs) + len(generated_results) + len(generated_admits)
    log.info(f"\n{'=' * 60}")
    log.info(f"SCRAPER COMPLETE - Generated {total} new pages")
    log.info(f"  Jobs: {len(generated_jobs)}, Results: {len(generated_results)}, Admit Cards: {len(generated_admits)}")
    log.info(f"{'=' * 60}\n")


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Naukri Dhaba Daily Scraper Bot')
    parser.add_argument('--daemon', action='store_true', help='Run as scheduler (every day at 6 AM)')
    parser.add_argument('--time', default='06:00', help='Time to run daily (HH:MM, default: 06:00)')
    args = parser.parse_args()

    if args.daemon:
        log.info(f"Starting Naukri Dhaba Scraper in daemon mode. Scheduled at {args.time} daily.")
        log.info("Press Ctrl+C to stop.")
        schedule.every().day.at(args.time).do(run_scraper)
        # Run immediately on start
        run_scraper()
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        run_scraper()

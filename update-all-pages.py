#!/usr/bin/env python3
"""
============================================================
NAUKRI DHABA - MASS PAGE UPDATER
File: update-all-pages.py
============================================================

Updates ALL 197+ HTML pages with:
  1. Tracking codes (tracking.js + ads-manager.js in <head>)
  2. Open Graph meta tags (og:title, og:description, og:url)
  3. Twitter Card meta tags
  4. Canonical tags
  5. Keyword meta tags (auto-generated from title+dept+location)
  6. JSON-LD structured data for results & admit cards
  7. Breadcrumb schema markup
  8. Fixes broken result/admit card buttons (removes alert())
  9. Removes ALL SarkariResult URLs and references
  10. Fixes "nan" values in Apply buttons
  11. Adds geo tags for India SEO
  12. Adds ads-manager class to existing ad slots

USAGE:
  python3 update-all-pages.py          # Update all pages
  python3 update-all-pages.py --dry-run # Preview changes only

SAFE TO RE-RUN: Won't duplicate tags if already present.
============================================================
"""

import os
import re
import sys
import glob
import json
import argparse
from pathlib import Path
from datetime import date, datetime
from html import escape
from urllib.parse import urlparse, quote

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from site_config import PRETTY_ROUTE_MAP, REDIRECT_PATH, SITE_NAME, SITE_URL, SOURCE_HOSTS

SITE_ROOT = Path(__file__).parent
TODAY = date.today().isoformat()
TRACKING_CONFIG_PATH = SITE_ROOT / 'tracking-config.json'

# Banned URL patterns (sarkariresult)
BANNED_URL_PATTERNS = [
    r'https?://(?:www\.)?sarkariresult(?:s)?\.(?:com|org|in|net)[^\s"\']*',
    r'https?://doc\.sarkariresults?\.org\.in[^\s"\']*',
]

# Banned text references
BANNED_TEXT_PATTERNS = [
    (r'\bSarkariResult(?:s)?\b', SITE_NAME),
    (r'\bsarkari\s*result(?:s)?\b', SITE_NAME, re.IGNORECASE),
    (r'sarkariresult(?:s)?\.(?:com|org|in)', 'naukridhaba.in'),
]

# SEO keywords by department
SEO_KEYWORDS_MAP = {
    'upsc': 'UPSC, Civil Services, IAS, IPS, UPSC Exam 2026, Government Jobs India',
    'ssc': 'SSC, Staff Selection Commission, CGL, CHSL, MTS, SSC Jobs 2026',
    'railway': 'Railway Jobs, RRB, Group D, NTPC, ALP, Indian Railways Vacancy 2026',
    'banking': 'Bank Jobs, IBPS, SBI, RBI, PO, Clerk, Banking Vacancy 2026',
    'police': 'Police Jobs, Constable, SI, CRPF, BSF, CISF, Police Bharti 2026',
    'defence': 'Defence Jobs, Army, Navy, Air Force, NDA, CDS, Defence Bharti 2026',
    'government': 'Government jobs India, government recruitment updates, online form alerts, Naukri Dhaba',
}

DEFAULT_TRACKING_CONFIG = {
    'googleAnalytics4': {'enabled': False, 'measurementId': 'G-XXXXXXXXXX'},
    'googleTagManager': {'enabled': False, 'containerId': 'GTM-XXXXXXX'},
    'consentMode': {'enabled': False, 'storageKey': 'nd_consent_v1', 'defaultMode': 'reject', 'waitForUpdateMs': 500, 'bannerEnabled': True},
    'googleSearchConsole': {'enabled': False, 'verificationCode': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'},
    'googleAdSense': {'enabled': False, 'publisherId': 'ca-pub-XXXXXXXXXXXXXXXX'},
    'microsoftClarity': {'enabled': False, 'projectId': 'XXXXXXXXXX'},
    'facebookPixel': {'enabled': False, 'pixelId': 'XXXXXXXXXXXXXXXXXX'},
    'customHeadCode': {'enabled': False, 'code': '<code goes here>'},
}


def load_tracking_config():
    config = json.loads(json.dumps(DEFAULT_TRACKING_CONFIG))
    if not TRACKING_CONFIG_PATH.exists():
        return config

    try:
        loaded = json.loads(TRACKING_CONFIG_PATH.read_text(encoding='utf-8'))
    except Exception as exc:
        log(f"WARNING: Failed to parse {TRACKING_CONFIG_PATH.name}: {exc}")
        return config

    for key, default_value in DEFAULT_TRACKING_CONFIG.items():
        if isinstance(default_value, dict):
            config[key].update(loaded.get(key, {}))
        else:
            config[key] = loaded.get(key, default_value)
    return config


TRACKING_CONFIG = load_tracking_config()

def log(msg):
    print(msg)

def slugify_title(text):
    """Simple slugify."""
    text = str(text).lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')[:80]


def clean_text(text):
    return re.sub(r'\s+', ' ', str(text or '')).strip()


def strip_icon_prefix(text):
    value = clean_text(text)
    value = re.sub(r'^(?:ð[^\s]*\s+|â[^\s]*\s+)+', '', value)
    return re.sub(r'^[^A-Za-z0-9\u0900-\u097F]+', '', value)


def normalize_title_text(title):
    title = clean_text(title)
    title = re.sub(r'\s*\|\s*' + re.escape(SITE_NAME) + r'.*$', '', title, flags=re.I)
    title = re.sub(r'\bSarkari\s+Naukri\b', '', title, flags=re.I)
    title = re.sub(r'\bSarkari\s+Result\b', '', title, flags=re.I)
    title = re.sub(r'\s*[-|:]\s*$', '', title)
    title = re.sub(r'\s*[-|:]\s*[-|:]\s*', ' - ', title)
    title = re.sub(r'\b(\d{4})\s+\1\b', r'\1', title)
    title = re.sub(r'([A-Za-z0-9])(?=(Apply Online|Result|Admit Card))', r'\1 ', title)
    title = re.sub(r'\b(20\d{2})\s+(Apply Online|Result|Admit Card)\s+\1\b', r'\1 \2', title)
    title = re.sub(r'\bResult\s*-\s*Check Result\b', 'Result', title, flags=re.I)
    title = re.sub(r'\bAdmit Card\s*-\s*Download Admit Card\b', 'Admit Card', title, flags=re.I)
    title = re.sub(r'\bApply Online\s*-\s*Apply Online\b', 'Apply Online', title, flags=re.I)
    return clean_text(title)


def dedupe_csv(*parts):
    seen = set()
    items = []
    for part in parts:
        if not part:
            continue
        for token in [clean_text(x) for x in str(part).split(',')]:
            key = token.lower()
            if not token or key in seen:
                continue
            seen.add(key)
            items.append(token)
    return ', '.join(items)


def to_iso_date(text):
    value = clean_text(text)
    if not value:
        return None
    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def detect_page_type(filepath, content):
    """Detect page type from filepath and content."""
    path = str(filepath).replace('\\', '/')
    if '/jobs/' in path:
        return 'job'
    elif '/results/' in path:
        return 'result'
    elif '/admit-cards/' in path:
        return 'admit_card'
    elif 'latest-jobs.html' in path:
        return 'jobs_list'
    elif path.endswith('results.html') and '/results/' not in path:
        return 'results_list'
    elif 'admit-cards.html' in path and '/admit-cards/' not in path:
        return 'admits_list'
    elif path.endswith('index.html') or path.endswith('/'):
        return 'home'
    return 'other'


def extract_from_html(content):
    """Extract key data from existing HTML."""
    data = {}

    # Title
    m = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
    data['title'] = m.group(1).strip() if m else ''
    data['title'] = normalize_title_text(data['title'])

    # Description
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', content, re.IGNORECASE)
    data['description'] = m.group(1).strip() if m else ''

    # H1
    m = re.search(r'<h1[^>]*>(.*?)</h1>', content, re.IGNORECASE | re.DOTALL)
    data['h1'] = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''

    # Department from breadcrumb or info-grid
    m = re.search(r'class="info-item__value">([A-Z\s]+)</span>', content)
    if m:
        data['dept'] = m.group(1).strip()
    else:
        # Try to extract from title
        for dept in ['UPSC', 'SSC', 'SSC', 'RAILWAY', 'RRB', 'IBPS', 'SBI', 'POLICE', 'ARMY', 'NDA', 'CDS', 'NTA', 'DRDO']:
            if dept in content.upper()[:2000]:
                data['dept'] = dept
                break
        else:
            data['dept'] = 'Government'

    # Location from geo tag or content
    m = re.search(r'<meta\s+name=["\']geo\.placename["\']\s+content=["\'](.*?)["\']', content, re.IGNORECASE)
    data['location'] = m.group(1).strip() if m else 'India'

    return data


def label_key(text):
    value = strip_icon_prefix(text).lower()
    value = re.sub(r'[/|:()\-]+', ' ', value)
    value = re.sub(r'\s+', ' ', value).strip()
    return value


def article_links_dedup(links):
    rows_by_url = {}
    for label, url in links:
        clean_label_value = strip_icon_prefix(label)
        clean_url_value = clean_text(url)
        if not clean_label_value or not clean_url_value or clean_url_value == '#':
            continue
        current = rows_by_url.get(clean_url_value.lower())
        if current is None or len(clean_label_value) < len(current[0]):
            rows_by_url[clean_url_value.lower()] = (clean_label_value, clean_url_value)
    return list(rows_by_url.values())


def extract_detail_data(content, filepath, page_type):
    if BeautifulSoup is None:
        return None

    soup = BeautifulSoup(content, 'html.parser')
    main = soup.find('main')
    if not main:
        return None

    data = extract_from_html(content)
    h1 = main.find('h1')
    title = normalize_title_text(strip_icon_prefix(h1.get_text(' ', strip=True) if h1 else data.get('title', '')))
    year_match = re.search(r'\b(20\d{2})\b', title or '')
    year = year_match.group(1) if year_match else str(date.today().year)

    info = {}
    for item in main.select('.info-item'):
        label = item.select_one('.info-item__label')
        value = item.select_one('.info-item__value')
        if not label or not value:
            continue
        info[label_key(label.get_text(' ', strip=True))] = clean_text(value.get_text(' ', strip=True))

    table_rows = {}
    fee_rows = {}
    for table in main.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue
            label = strip_icon_prefix(cells[0].get_text(' ', strip=True))
            value = clean_text(cells[1].get_text(' ', strip=True))
            key = label_key(label)
            if not key or not value:
                continue
            if re.search(r'\b(general|obc|ews)\b', key):
                fee_rows['general'] = value
            elif re.search(r'\b(sc|st|ph|pwd)\b', key):
                fee_rows['reserved'] = value
            else:
                table_rows[key] = value

    headings = {}
    for heading in main.find_all(['h2', 'h3']):
        headings[label_key(heading.get_text(' ', strip=True))] = heading

    links = []
    for anchor in main.find_all('a', href=True):
        href = clean_text(anchor.get('href'))
        text = strip_icon_prefix(anchor.get_text(' ', strip=True))
        if not href or href == '#':
            continue
        if href.startswith('/') and not href.startswith(REDIRECT_PATH):
            continue
        links.append((text or href, href))
    links = article_links_dedup(links)

    action_links = {}
    for label, href in links:
        lower = label.lower()
        if 'notification' in lower and 'notification' not in action_links:
            action_links['notification_url'] = href
        if 'apply' in lower and 'apply_url' not in action_links:
            action_links['apply_url'] = href
        if 'result' in lower and 'scorecard' not in lower and 'result_url' not in action_links:
            action_links['result_url'] = href
        if ('scorecard' in lower or 'score card' in lower or 'marks' in lower) and 'scorecard_url' not in action_links:
            action_links['scorecard_url'] = href
        if 'admit' in lower and 'admit_url' not in action_links:
            action_links['admit_url'] = href

    article_text = main.get_text(' ', strip=True)
    age_text = info.get('age limit') or table_rows.get('age limit') or table_rows.get('age') or ''
    age_match = re.search(r'(\d{1,2})\D+(\d{1,2})\s*years?', age_text, re.I)
    age_min = age_match.group(1) if age_match else '18'
    age_max = age_match.group(2) if age_match else '40'

    section_key = {
        'job': 'jobs',
        'result': 'results',
        'admit_card': 'admit cards',
    }[page_type]

    detail = {
        'title': title,
        'year': year,
        'dept': info.get('department') or data.get('dept', 'Government'),
        'section_key': section_key,
        'last_date': info.get('last date') or table_rows.get('last date to apply online') or table_rows.get('last date') or 'Check Notification',
        'application_begin': table_rows.get('application begin') or table_rows.get('application start') or 'Check Notification',
        'exam_date': table_rows.get('exam date') or 'As per Schedule',
        'result_date': table_rows.get('result date') or info.get('result date') or 'Check Notification',
        'admit_release': table_rows.get('released') or table_rows.get('admit card available') or 'Check Notification',
        'total_posts': info.get('total posts') or info.get('total post') or table_rows.get('total posts') or 'Check Notification',
        'age_text': age_text or f'{age_min}-{age_max} Years',
        'age_min': age_min,
        'age_max': age_max,
        'qualification': info.get('qualification') or table_rows.get('eligibility') or table_rows.get('qualification') or 'Check Notification',
        'salary': info.get('salary pay scale') or info.get('salary') or table_rows.get('salary') or table_rows.get('pay scale') or 'As per Government Norms',
        'fee_general': fee_rows.get('general', ''),
        'fee_reserved': fee_rows.get('reserved', ''),
        'links': links,
        'apply_url': action_links.get('apply_url', ''),
        'notification_url': action_links.get('notification_url', ''),
        'result_url': action_links.get('result_url', ''),
        'scorecard_url': action_links.get('scorecard_url', ''),
        'admit_url': action_links.get('admit_url', ''),
        'article_text': article_text,
        'filepath': filepath,
    }

    for fee_key in ('fee_general', 'fee_reserved'):
        fee_value = detail[fee_key]
        if not fee_value:
            continue
        if fee_value == detail['last_date'] or re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', fee_value):
            detail[fee_key] = ''

    return detail


def render_link_list(links, heading):
    rows = ''.join(
        f'<li><a href="{escape(url, quote=True)}" target="_blank" rel="nofollow noopener noreferrer">{escape(label)}</a></li>'
        for label, url in links
    )
    if not rows:
        return ''
    return (
        '<div class="links-section">'
        f'<h3 class="links-section__title">{heading}</h3>'
        f'<ul class="links-list">{rows}</ul>'
        '</div>'
    )


def build_job_snapshot(detail):
    lines = [
        f'<li><strong>Department:</strong> {escape(detail["dept"])}</li>',
        f'<li><strong>Application window:</strong> {escape(detail["application_begin"])} to {escape(detail["last_date"])}</li>',
        f'<li><strong>Qualification:</strong> {escape(detail["qualification"])}</li>',
        '<li><strong>Official action:</strong> Always complete the form on the authority site linked below.</li>',
    ]
    return (
        '<div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">'
        '<h3 style="color:var(--primary);margin-top:0;">Role Snapshot</h3>'
        f'<p style="line-height:1.9;color:#444;">{escape(detail["title"])} is listed under {escape(detail["dept"])} recruitment updates on Naukri Dhaba. '
        f'The current application deadline is {escape(detail["last_date"])} and the extracted age range is {escape(detail["age_min"])} to {escape(detail["age_max"])} years. '
        'Verify category relaxation, district-wise notice details, and final instructions on the official authority page before submission.</p>'
        f'<ul style="line-height:2;margin:0;padding-left:1.2rem;">{"".join(lines)}</ul>'
        '</div>'
    )


def build_result_snapshot(detail):
    lines = [
        f'<li><strong>Department:</strong> {escape(detail["dept"])}</li>',
        f'<li><strong>Result date:</strong> {escape(detail["result_date"])}</li>',
        '<li><strong>Next step:</strong> Download the scorecard or shortlist notice from the official portal when available.</li>',
    ]
    return (
        '<div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">'
        '<h3 style="color:var(--primary);margin-top:0;">Result Snapshot</h3>'
        f'<p style="line-height:1.9;color:#444;">{escape(detail["title"])} is tracked here as a result update. '
        f'Use the official result or scorecard links below to confirm marks, qualifying status, and the next recruitment stage.</p>'
        f'<ul style="line-height:2;margin:0;padding-left:1.2rem;">{"".join(lines)}</ul>'
        '</div>'
    )


def build_admit_snapshot(detail):
    lines = [
        f'<li><strong>Department:</strong> {escape(detail["dept"])}</li>',
        f'<li><strong>Release status:</strong> {escape(detail["admit_release"])}</li>',
        f'<li><strong>Exam date:</strong> {escape(detail["exam_date"])}</li>',
    ]
    return (
        '<div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">'
        '<h3 style="color:var(--primary);margin-top:0;">Admit Card Snapshot</h3>'
        f'<p style="line-height:1.9;color:#444;">{escape(detail["title"])} is available as an admit-card update. '
        'Download the hall ticket only from the official authority link and recheck exam city, shift timing, and ID-proof instructions before the exam day.</p>'
        f'<ul style="line-height:2;margin:0;padding-left:1.2rem;">{"".join(lines)}</ul>'
        '</div>'
    )


def build_detail_article(detail, page_type):
    title = escape(detail['title'])
    dept = escape(detail['dept'])
    year_badge = ''
    if detail['year'] and not re.search(rf'\b{re.escape(detail["year"])}\b', detail['title']):
        year_badge = (
            f' <span style="background:var(--secondary);color:#fff;padding:4px 12px;'
            f'border-radius:4px;font-size:1rem;">{escape(detail["year"])}</span>'
        )
    breadcrumb_label = {
        'job': 'Jobs',
        'result': 'Results',
        'admit_card': 'Admit Cards',
    }[page_type]
    breadcrumb_href = pretty_root_path({
        'job': 'latest-jobs.html',
        'result': 'results.html',
        'admit_card': 'admit-cards.html',
    }[page_type])
    extra_links = render_link_list(detail['links'], 'Important Links')

    if page_type == 'job':
        apply_cta = (
            f'<a href="{escape(detail["apply_url"], quote=True)}" target="_blank" rel="nofollow noopener noreferrer" class="btn btn--primary btn--large">Apply Online</a>'
            if detail['apply_url']
            else '<span class="btn btn--primary btn--large" style="opacity:.65;cursor:default;">Official Apply Link Awaited</span>'
        )
        notify_cta = (
            f'<a href="{escape(detail["notification_url"], quote=True)}" target="_blank" rel="nofollow noopener noreferrer" class="btn btn--secondary btn--large">Download Notification</a>'
            if detail['notification_url']
            else ''
        )
        fee_section = ''
        if detail['fee_general'] or detail['fee_reserved']:
            fee_rows = ''
            if detail['fee_general']:
                fee_rows += f'<tr><td style="padding:8px 0;color:#666;">General / OBC / EWS</td><td style="padding:8px 0;font-weight:bold;">{escape(detail["fee_general"])}</td></tr>'
            if detail['fee_reserved']:
                fee_rows += f'<tr><td style="padding:8px 0;color:#666;">SC / ST / PH</td><td style="padding:8px 0;font-weight:bold;">{escape(detail["fee_reserved"])}</td></tr>'
            fee_section = (
                '<div style="border-left:4px solid var(--warning);background:#fff8e1;padding:1.5rem;border-radius:0 8px 8px 0;margin:1.5rem 0;">'
                '<h3 style="color:var(--primary);margin-top:0;">Application Fee</h3>'
                f'<table style="width:100%;border-collapse:collapse;">{fee_rows}</table>'
                '</div>'
        )
        return f'''<main>
    <article class="job-detail">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/">Home</a> &gt; <a href="{breadcrumb_href}">{breadcrumb_label}</a> &gt; <span>{title}</span>
      </nav>
      <h1 style="color:var(--primary);margin-bottom:.5rem;">{title}{year_badge}</h1>
      <div class="nd-ad ad-slot" data-ad-slot="content-top"></div>
      <div class="info-grid">
        <div class="info-item"><span class="info-item__label">Last Date</span><span class="info-item__value" style="color:var(--danger);">{escape(detail["last_date"])}</span></div>
        <div class="info-item"><span class="info-item__label">Department</span><span class="info-item__value">{dept}</span></div>
        <div class="info-item"><span class="info-item__label">Total Posts</span><span class="info-item__value">{escape(detail["total_posts"])}</span></div>
        <div class="info-item"><span class="info-item__label">Age Limit</span><span class="info-item__value">{escape(detail["age_text"])}</span></div>
        <div class="info-item"><span class="info-item__label">Qualification</span><span class="info-item__value" style="font-size:.95rem;">{escape(detail["qualification"])}</span></div>
        <div class="info-item"><span class="info-item__label">Salary / Pay Scale</span><span class="info-item__value" style="font-size:.95rem;">{escape(detail["salary"])}</span></div>
      </div>
      <div class="action-bar">{apply_cta}{notify_cta}</div>
      <div style="border-left:4px solid var(--primary);background:var(--surface);padding:1.5rem;margin:1.5rem 0;">
        <h2 style="color:var(--primary);margin-top:0;">Important Dates</h2>
        <table style="width:100%;border-collapse:collapse;">
          <tr style="border-bottom:1px solid #eee;"><td style="padding:10px 0;color:#666;width:55%;">Application Begin</td><td style="font-weight:bold;">{escape(detail["application_begin"])}</td></tr>
          <tr style="border-bottom:1px solid #eee;"><td style="padding:10px 0;color:#666;">Last Date to Apply Online</td><td style="font-weight:bold;color:var(--danger);">{escape(detail["last_date"])}</td></tr>
          <tr style="border-bottom:1px solid #eee;"><td style="padding:10px 0;color:#666;">Exam Date</td><td style="font-weight:bold;">{escape(detail["exam_date"])}</td></tr>
        </table>
      </div>
      {fee_section}
      {build_job_snapshot(detail)}
      <div class="nd-ad ad-slot" data-ad-slot="content-mid"></div>
      <div class="calculator">
        <h3 style="margin-top:0;">Age Eligibility Calculator</h3>
        <p style="color:#666;font-size:.875rem;">Age limit: {escape(detail["age_min"])}-{escape(detail["age_max"])} years. OBC +3 yrs, SC/ST +5 yrs relaxation.</p>
        <div class="form-group"><label>Date of Birth:</label><input type="date" id="dob-input"></div>
        <div class="form-group"><label>Category:</label><select id="category-select"><option value="general">General</option><option value="obc">OBC (+3 years)</option><option value="sc">SC (+5 years)</option><option value="st">ST (+5 years)</option></select></div>
        <button onclick="checkEligibility({escape(detail["age_min"])}, {escape(detail["age_max"])})" class="btn btn--primary">Check Eligibility</button>
        <div id="eligibility-result" style="display:none;margin-top:1rem;padding:1rem;border-radius:4px;"></div>
      </div>
      {extra_links}
      <div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
        <h3 style="color:var(--primary);margin-top:0;">How to Apply</h3>
        <ol style="line-height:2.2;">
          <li>Use the official authority portal linked above, not third-party mirrors.</li>
          <li>Verify category, district, and document rules before you create an account.</li>
          <li>Fill the application form carefully and review the preview before final submission.</li>
          <li>Upload only the files and dimensions allowed in the official notice.</li>
          <li>Save the application number, preview, and payment receipt for later stages.</li>
        </ol>
      </div>
      {build_faq_html(build_job_faq_data(detail))}
      <div class="share-section">
        <h3>Share with Friends</h3>
        <button onclick="shareWhatsApp(window.location.href,'{title}')" class="share-btn share-btn--whatsapp">WhatsApp</button>
        <button onclick="shareTelegram(window.location.href,'{title}')" class="share-btn share-btn--telegram">Telegram</button>
        <button onclick="copyLink(window.location.href)" class="share-btn share-btn--copy">Copy Link</button>
      </div>
      <div class="nd-ad ad-slot" data-ad-slot="content-bottom"></div>
    </article>
  </main>'''

    if page_type == 'result':
        result_cta = (
            f'<a href="{escape(detail["result_url"], quote=True)}" target="_blank" rel="nofollow noopener noreferrer" class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;">Check Result</a>'
            if detail['result_url']
            else '<span class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;opacity:.7;cursor:default;">Result Link Coming Soon</span>'
        )
        score_cta = (
            f'<a href="{escape(detail["scorecard_url"], quote=True)}" target="_blank" rel="nofollow noopener noreferrer" class="btn btn--secondary btn--large" style="display:inline-block;margin-bottom:1rem;">Download Scorecard</a>'
            if detail['scorecard_url']
            else ''
        )
        return f'''<main>
    <article class="result-detail">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/">Home</a> &gt; <a href="{breadcrumb_href}">{breadcrumb_label}</a> &gt; <span>{title}</span>
      </nav>
      <h1 style="color:var(--primary);">{title}</h1>
      <div class="nd-ad ad-slot" data-ad-slot="content-top"></div>
      <div class="info-grid">
        <div class="info-item"><span class="info-item__label">Department</span><span class="info-item__value">{dept}</span></div>
        <div class="info-item"><span class="info-item__label">Result Date</span><span class="info-item__value">{escape(detail["result_date"])}</span></div>
        <div class="info-item"><span class="info-item__label">Stage</span><span class="info-item__value">Result Declared</span></div>
        <div class="info-item"><span class="info-item__label">Official Status</span><span class="info-item__value">Check authority links below</span></div>
      </div>
      <div style="background:#e8f5e9;padding:1.5rem;border-radius:8px;text-align:center;margin:1.5rem 0;">
        <div style="display:inline-block;background:var(--success);color:#fff;padding:.5rem 1rem;border-radius:4px;font-weight:bold;margin-bottom:1rem;">Declared</div>
        <p style="color:#666;margin-bottom:1rem;">Result Date: {escape(detail["result_date"])}</p>
        {result_cta}
        {score_cta}
      </div>
      {build_result_snapshot(detail)}
      <div class="nd-ad ad-slot" data-ad-slot="content-mid"></div>
      {extra_links}
      <div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
        <h3 style="color:var(--primary);margin-top:0;">How to Check Result</h3>
        <ol style="line-height:2.2;">
          <li>Open the official result portal linked above.</li>
          <li>Keep your roll number or registration number ready before login.</li>
          <li>Check your name, category, marks, and qualifying stage carefully.</li>
          <li>Download the official PDF or scorecard and keep a copy for verification.</li>
        </ol>
      </div>
      {build_faq_html(build_result_faq_data(detail))}
      <div class="share-section">
        <h3>Share with Friends</h3>
        <button onclick="shareWhatsApp(window.location.href,'{title} Result')" class="share-btn share-btn--whatsapp">WhatsApp</button>
        <button onclick="shareTelegram(window.location.href,'{title} Result')" class="share-btn share-btn--telegram">Telegram</button>
        <button onclick="copyLink(window.location.href)" class="share-btn share-btn--copy">Copy Link</button>
      </div>
      <div class="nd-ad ad-slot" data-ad-slot="content-bottom"></div>
    </article>
  </main>'''

    admit_cta = (
        f'<a href="{escape(detail["admit_url"], quote=True)}" target="_blank" rel="nofollow noopener noreferrer" class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;">Download Admit Card</a>'
        if detail['admit_url']
        else '<span class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;opacity:.7;cursor:default;">Admit Card Link Coming Soon</span>'
    )
    return f'''<main>
    <article class="admit-detail">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="/">Home</a> &gt; <a href="{breadcrumb_href}">{breadcrumb_label}</a> &gt; <span>{title}</span>
      </nav>
      <h1 style="color:var(--primary);">{title}</h1>
      <div class="nd-ad ad-slot" data-ad-slot="content-top"></div>
      <div class="info-grid">
        <div class="info-item"><span class="info-item__label">Department</span><span class="info-item__value">{dept}</span></div>
        <div class="info-item"><span class="info-item__label">Release Status</span><span class="info-item__value">{escape(detail["admit_release"])}</span></div>
        <div class="info-item"><span class="info-item__label">Exam Date</span><span class="info-item__value">{escape(detail["exam_date"])}</span></div>
        <div class="info-item"><span class="info-item__label">Document Type</span><span class="info-item__value">Admit Card / Exam City</span></div>
      </div>
      <div style="background:#e8f5e9;padding:1.5rem;border-radius:8px;text-align:center;margin:1.5rem 0;">
        <div style="display:inline-block;background:var(--success);color:#fff;padding:.5rem 1rem;border-radius:4px;font-weight:bold;margin-bottom:1rem;">Available</div>
        <p style="color:#666;margin-bottom:.5rem;">Released: {escape(detail["admit_release"])}</p>
        <p style="color:#666;font-weight:bold;margin-bottom:1.5rem;">Exam Date: {escape(detail["exam_date"])}</p>
        {admit_cta}
      </div>
      {build_admit_snapshot(detail)}
      <div class="nd-ad ad-slot" data-ad-slot="content-mid"></div>
      {extra_links}
      <div style="border-left:4px solid var(--danger);background:#fff3e0;padding:1.5rem;border-radius:0 8px 8px 0;margin:1.5rem 0;">
        <h3 style="color:var(--danger);margin-top:0;">Important Instructions</h3>
        <ul style="line-height:1.8;">
          <li>Carry a printed admit card exactly as required in the official instructions.</li>
          <li>Bring a valid photo ID that matches the admit-card identity details.</li>
          <li>Check reporting time, gate closing time, and venue address before travel.</li>
          <li>Avoid restricted items such as phones, smartwatches, calculators, or loose papers.</li>
        </ul>
      </div>
      <div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">
        <h3 style="color:var(--primary);margin-top:0;">Exam Day Checklist</h3>
        <ul style="list-style:none;padding:0;">
          <li style="padding:.4rem 0;">Printed admit card</li>
          <li style="padding:.4rem 0;">Valid photo ID proof</li>
          <li style="padding:.4rem 0;">Passport-size photos if required</li>
          <li style="padding:.4rem 0;">Pens and transparent water bottle if allowed</li>
        </ul>
      </div>
      {build_faq_html(build_admit_faq_data(detail))}
      <div class="share-section">
        <h3>Share with Friends</h3>
        <button onclick="shareWhatsApp(window.location.href,'{title} Admit Card')" class="share-btn share-btn--whatsapp">WhatsApp</button>
        <button onclick="shareTelegram(window.location.href,'{title} Admit Card')" class="share-btn share-btn--telegram">Telegram</button>
        <button onclick="copyLink(window.location.href)" class="share-btn share-btn--copy">Copy Link</button>
      </div>
      <div class="nd-ad ad-slot" data-ad-slot="content-bottom"></div>
    </article>
  </main>'''


def build_standard_sidebar():
    return '''<aside class="sidebar">
  <div class="widget widget--telegram">
    <h3 class="widget__title">Join Telegram</h3>
    <p style="margin-bottom:1rem;">Get instant job alerts on your phone.</p>
    <a href="https://t.me/naukridhaba" target="_blank" class="btn" style="background:#fff;color:#0088cc;width:100%;">Join Channel</a>
  </div>
  <div class="widget">
    <h3 class="widget__title">Quick Links</h3>
    <div class="footer__links">
      <a href="/latest-jobs.html">Latest Jobs</a>
      <a href="/results.html">Results</a>
      <a href="/admit-cards.html">Admit Cards</a>
      <a href="/eligibility-calculator.html">Eligibility Check</a>
    </div>
  </div>
  <div class="nd-ad ad-slot" data-ad-slot="sidebar-top" style="min-height:250px;"></div>
</aside>'''


def build_standard_footer():
    return '''<footer class="footer">
  <div class="container">
    <div class="footer__grid">
      <div>
        <h3 class="footer__title">Naukri Dhaba</h3>
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
      <p>&copy; 2026 Naukri Dhaba. All rights reserved.</p>
      <p>Disclaimer: We are not affiliated with any government body. Information only.</p>
    </div>
  </div>
</footer>'''


def rebuild_detail_main(content, filepath, page_type):
    # V2 detail pages use class="detail-page" — skip them entirely.
    # Their content is authoritative (generated by sarkari_scraper.py) and
    # must not be overwritten with the old-template rebuild logic.
    if 'class="detail-page"' in content:
        return content
    detail = extract_detail_data(content, filepath, page_type)
    if not detail:
        return content
    rebuilt_main = build_detail_article(detail, page_type)
    shell = (
        '<div class="content-wrapper container" style="margin-top:2rem;">\n'
        f'{rebuilt_main}\n'
        f'{build_standard_sidebar()}\n'
        '</div>\n\n'
        f'{build_standard_footer()}\n'
        '<script src="/js/app.js"></script>\n'
    )
    result = re.sub(r'<div class="content-wrapper container" style="margin-top:2rem;">.*?</body>', shell + '</body>', content, count=1, flags=re.DOTALL)

    # Inject FAQ JSON-LD into <head>
    if page_type == 'job':
        faq_qas = build_job_faq_data(detail)
    elif page_type == 'result':
        faq_qas = build_result_faq_data(detail)
    else:
        faq_qas = build_admit_faq_data(detail)
    faq_ld = build_faq_json_ld(faq_qas)
    # Insert before </head> only if FAQPage JSON-LD not already present
    if '"FAQPage"' not in result:
        result = result.replace('</head>', faq_ld + '\n</head>', 1)

    return result


def get_canonical_url(filepath):
    """Get canonical URL for a file."""
    rel = str(filepath.relative_to(SITE_ROOT)).replace('\\', '/')
    if rel in PRETTY_ROUTE_MAP:
        return SITE_URL + PRETTY_ROUTE_MAP[rel]
    return SITE_URL + '/' + rel


def get_css_path(filepath):
    """Get relative CSS path based on depth."""
    depth = len(filepath.relative_to(SITE_ROOT).parts) - 1
    if depth == 0:
        return 'css/style.css'
    return '../../css/style.css'


def get_js_path(filepath, jsfile):
    """Get relative JS path based on depth."""
    depth = len(filepath.relative_to(SITE_ROOT).parts) - 1
    if depth == 0:
        return f'js/{jsfile}'
    return f'../../js/{jsfile}'


def pretty_root_path(filename):
    return PRETTY_ROUTE_MAP.get(filename, '/' + filename)


def site_route(filename):
    return SITE_URL + pretty_root_path(filename)


def normalize_root_links(content):
    """Convert extensionless pretty routes to .html links (GitHub Pages compatible)."""
    _ROUTE_NAMES = (
        'latest-jobs', 'results', 'admit-cards', 'resources',
        'previous-papers', 'eligibility-calculator', 'study-planner',
    )

    def repl(match):
        attr = match.group('attr')
        quote = match.group('quote')
        url = match.group('url')
        suffix = match.group('suffix') or ''

        prefix = ''
        path = url
        if path.startswith(SITE_URL):
            prefix = SITE_URL
            path = path[len(SITE_URL):]

        # path is now e.g. "/latest-jobs"
        new_path = path + '.html'
        return f'{attr}={quote}{prefix}{new_path}{suffix}{quote}'

    # Match extensionless pretty routes (no trailing slash, no .html)
    route_alt = '|'.join(re.escape(r) for r in _ROUTE_NAMES)
    pattern = re.compile(
        r'(?P<attr>href|src)=(?P<quote>["\'])(?P<url>(?:' + re.escape(SITE_URL) + r')?'
        r'/(?:' + route_alt + r'))'
        r'(?P<suffix>[?#][^"\']*)?(?P=quote)',
        flags=re.IGNORECASE
    )
    return pattern.sub(repl, content)


def is_placeholder(value, placeholders):
    normalized = clean_text(value)
    return (not normalized) or normalized in placeholders


def serialize_tracking_config():
    payload = json.dumps(TRACKING_CONFIG, separators=(',', ':'), ensure_ascii=False)
    return payload.replace('</', '<\\/')


def build_consent_bootstrap_markup():
    consent = TRACKING_CONFIG.get('consentMode', {})
    if not consent.get('enabled'):
        return ''

    storage_key = escape(consent.get('storageKey', 'nd_consent_v1'), quote=True)
    default_mode = escape(consent.get('defaultMode', 'reject'), quote=True)
    wait_for_update = int(consent.get('waitForUpdateMs', 500) or 500)
    return '\n'.join([
        '    <script>',
        '      (function(w){',
        '        var consentKey = "' + storage_key + '";',
        '        var defaultMode = "' + default_mode + '";',
        '        var waitForUpdate = ' + str(wait_for_update) + ';',
        '        var denied = {',
        '          ad_storage: "denied",',
        '          analytics_storage: "denied",',
        '          ad_user_data: "denied",',
        '          ad_personalization: "denied",',
        '          functionality_storage: "granted",',
        '          security_storage: "granted",',
        '          personalization_storage: "denied"',
        '        };',
        '        var analyticsGranted = {',
        '          ad_storage: "denied",',
        '          analytics_storage: "granted",',
        '          ad_user_data: "denied",',
        '          ad_personalization: "denied",',
        '          functionality_storage: "granted",',
        '          security_storage: "granted",',
        '          personalization_storage: "denied"',
        '        };',
        '        var allGranted = {',
        '          ad_storage: "granted",',
        '          analytics_storage: "granted",',
        '          ad_user_data: "granted",',
        '          ad_personalization: "granted",',
        '          functionality_storage: "granted",',
        '          security_storage: "granted",',
        '          personalization_storage: "granted"',
        '        };',
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


def build_head_tracking_markup(filepath):
    tracking_path = get_js_path(filepath, 'tracking.js')
    lines = [
        f'    <script>window.NAUKRI_DHABA_TRACKING_CONFIG = {serialize_tracking_config()};</script>'
    ]

    gsc = TRACKING_CONFIG.get('googleSearchConsole', {})
    if gsc.get('enabled') and not is_placeholder(
        gsc.get('verificationCode'),
        {'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'}
    ):
        lines.append(
            f'    <meta name="google-site-verification" content="{escape(gsc["verificationCode"], quote=True)}">'
        )

    gtm = TRACKING_CONFIG.get('googleTagManager', {})
    gtm_enabled = gtm.get('enabled') and not is_placeholder(
        gtm.get('containerId'),
        {'GTM-XXXXXXX'}
    )
    if gtm_enabled:
        container_id = escape(gtm['containerId'], quote=True)
        consent_markup = build_consent_bootstrap_markup()
        if consent_markup:
            lines.append(consent_markup)
        lines.append('    <!-- Google Tag Manager -->')
        lines.append('    <script>')
        lines.append('      (function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({"gtm.start":')
        lines.append('      new Date().getTime(),event:"gtm.js"});var f=d.getElementsByTagName(s)[0],')
        lines.append('      j=d.createElement(s),dl=l!="dataLayer"?"&l="+l:"";j.async=true;j.src=')
        lines.append('      "https://www.googletagmanager.com/gtm.js?id="+i+dl;f.parentNode.insertBefore(j,f);')
        lines.append(f'      }})(window,document,"script","dataLayer","{container_id}");')
        lines.append('    </script>')
        lines.append('    <!-- End Google Tag Manager -->')
    else:
        ga4 = TRACKING_CONFIG.get('googleAnalytics4', {})
        if ga4.get('enabled') and not is_placeholder(
            ga4.get('measurementId'),
            {'G-XXXXXXXXXX'}
        ):
            measurement_id = escape(ga4['measurementId'], quote=True)
            consent_markup = build_consent_bootstrap_markup()
            if consent_markup:
                lines.append(consent_markup)
            lines.append('    <!-- Google Analytics 4 -->')
            lines.append(f'    <script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>')
            lines.append('    <script>')
            lines.append('      window.dataLayer = window.dataLayer || [];')
            lines.append('      function gtag(){dataLayer.push(arguments);}')
            lines.append('      gtag("js", new Date());')
            lines.append(f'      gtag("config", "{measurement_id}");')
            lines.append('    </script>')

    custom_head = TRACKING_CONFIG.get('customHeadCode', {})
    if custom_head.get('enabled') and custom_head.get('code') and custom_head.get('code') != '<code goes here>':
        lines.append(f'    {custom_head["code"]}')

    lines.append(f'    <script src="{tracking_path}"></script>')
    return '\n'.join(lines)


def build_body_tracking_markup():
    gtm = TRACKING_CONFIG.get('googleTagManager', {})
    if not (
        gtm.get('enabled')
        and not is_placeholder(gtm.get('containerId'), {'GTM-XXXXXXX'})
    ):
        return ''
    container_id = escape(gtm['containerId'], quote=True)
    return (
        '    <!-- Google Tag Manager (noscript) -->\n'
        f'    <noscript><iframe src="https://www.googletagmanager.com/ns.html?id={container_id}" '
        'height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>\n'
        '    <!-- End Google Tag Manager (noscript) -->'
    )


def get_keywords(page_type, title, dept, filepath=None):
    """Auto-generate SEO keywords."""
    dept_lower = dept.lower()
    path_str = str(filepath).lower().replace('\\', '/') if filepath else ''
    base_kws = SEO_KEYWORDS_MAP.get('government', '')
    for key, kws in SEO_KEYWORDS_MAP.items():
        if key in dept_lower or key in title.lower() or f'/{key}/' in path_str:
            base_kws = kws
            break

    extra_kws = [
        normalize_title_text(title),
        f"{dept} Jobs",
        "Government Jobs India",
        SITE_NAME,
    ]
    return dedupe_csv(base_kws, ', '.join(extra_kws))


def title_already_has_intent(title, page_type):
    lower_title = title.lower()
    intent_patterns = {
        'job': r'(apply online|online form|recruitment|vacancy|registration|application form)',
        'result': r'(result|score ?card|merit list|cut ?off|selection list)',
        'admit_card': r'(admit card|hall ticket|exam city|call letter)',
    }
    pattern = intent_patterns.get(page_type)
    return bool(pattern and re.search(pattern, lower_title))


def build_meta_block(data, page_type, filepath, canonical_url):
    """Build complete SEO meta tag block."""
    title = normalize_title_text(data.get('title', SITE_NAME))
    description = clean_text(data.get('description', f"{title} - Check details at {SITE_NAME}"))
    dept = data.get('dept', 'Government')
    location = data.get('location', 'India')

    page_defaults = {
        'home': {
            'title': f'{SITE_NAME} | Govt Jobs, Results, Admit Cards',
            'description': f'{SITE_NAME} brings the latest government jobs, exam results, admit cards, and official updates for India.',
            'keywords': dedupe_csv(
                'Government Jobs India, Latest Govt Jobs, Exam Results, Admit Card, Govt Recruitment Updates',
                SITE_NAME,
            ),
        },
        'jobs_list': {
            'title': f'Latest Govt Jobs 2026 | {SITE_NAME}',
            'description': f'Browse the latest government jobs, online forms, and recruitment updates across India on {SITE_NAME}.',
            'keywords': dedupe_csv(
                'Latest Govt Jobs 2026, Government Jobs India, Online Form, Govt Recruitment Updates',
                SITE_NAME,
            ),
        },
        'results_list': {
            'title': f'Latest Results 2026 | {SITE_NAME}',
            'description': f'Check the latest government exam results, merit lists, and score cards on {SITE_NAME}.',
            'keywords': dedupe_csv(
                'Latest Results 2026, Government Exam Result, Score Card, Merit List, Result Updates India',
                SITE_NAME,
            ),
        },
        'admits_list': {
            'title': f'Latest Admit Cards 2026 | {SITE_NAME}',
            'description': f'Download the latest admit cards, hall tickets, and exam city slips for government exams on {SITE_NAME}.',
            'keywords': dedupe_csv(
                'Latest Admit Cards 2026, Hall Ticket, Exam City, Government Admit Card',
                SITE_NAME,
            ),
        },
    }

    if page_type in page_defaults:
        full_title = page_defaults[page_type]['title']
        og_title = full_title
        og_desc = page_defaults[page_type]['description']
        keywords = page_defaults[page_type]['keywords']
    else:
        keywords = get_keywords(page_type, title, dept, filepath)
        og_title = f"{title} | {SITE_NAME}"
        og_desc = (description[:160] if description else og_title)

        type_suffix = {
            'job': 'Apply Online',
            'result': 'Check Result',
            'admit_card': 'Download Admit Card',
            'other': 'Government Update'
        }.get(page_type, 'Government Update')

        full_title = (
            f"{title} | {SITE_NAME}"
            if title_already_has_intent(title, page_type) or type_suffix.lower() in title.lower()
            else f"{title} - {type_suffix} | {SITE_NAME}"
        )

    og_type = 'article' if page_type in {'job', 'result', 'admit_card'} else 'website'
    is_detail_page = page_type in {'job', 'result', 'admit_card'}
    preconnect_block = '''    <link rel="preconnect" href="https://www.googletagmanager.com">
    <link rel="preconnect" href="https://www.google-analytics.com">
    <link rel="dns-prefetch" href="https://www.googletagmanager.com">
    <link rel="dns-prefetch" href="https://www.google-analytics.com">''' if is_detail_page else ''

    return f'''    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{full_title}</title>
    <meta name="description" content="{og_desc}">
    <meta name="keywords" content="{keywords}">
    <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
    <meta name="author" content="{SITE_NAME}">
    <link rel="canonical" href="{canonical_url}">
{preconnect_block}
    <!-- Open Graph -->
    <meta property="og:type" content="{og_type}">
    <meta property="og:title" content="{og_title}">
    <meta property="og:description" content="{og_desc}">
    <meta property="og:url" content="{canonical_url}">
    <meta property="og:site_name" content="{SITE_NAME}">
    <meta property="og:locale" content="en_IN">
    <meta property="og:image" content="{SITE_URL}/img/og-default.png">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{og_title}">
    <meta name="twitter:description" content="{og_desc}">
    <meta name="twitter:image" content="{SITE_URL}/img/og-default.png">
    <!-- India Geo -->
    <meta name="geo.region" content="IN">
    <meta name="geo.placename" content="{location}">'''


def _job_location_for(title):
    """Return (streetAddress, city, state, postalCode) based on job title keywords."""
    STATE_LOCS = {
        'BIHAR': ('Patna', 'Bihar', '800001'),
        'RAJASTHAN': ('Jaipur', 'Rajasthan', '302001'),
        'UTTAR PRADESH': ('Lucknow', 'Uttar Pradesh', '226001'),
        ' UP ': ('Lucknow', 'Uttar Pradesh', '226001'),
        'MADHYA PRADESH': ('Bhopal', 'Madhya Pradesh', '462001'),
        'MPESB': ('Bhopal', 'Madhya Pradesh', '462001'),
        'MPPSC': ('Bhopal', 'Madhya Pradesh', '462001'),
        'HARYANA': ('Chandigarh', 'Haryana', '160001'),
        'JHARKHAND': ('Ranchi', 'Jharkhand', '834001'),
        'PUNJAB': ('Chandigarh', 'Punjab', '160001'),
        'UTTARAKHAND': ('Dehradun', 'Uttarakhand', '248001'),
        'GUJARAT': ('Gandhinagar', 'Gujarat', '382010'),
        'MAHARASHTRA': ('Mumbai', 'Maharashtra', '400001'),
        'KARNATAKA': ('Bengaluru', 'Karnataka', '560001'),
        'KERALA': ('Thiruvananthapuram', 'Kerala', '695001'),
        'TAMIL NADU': ('Chennai', 'Tamil Nadu', '600001'),
        'ANDHRA': ('Amaravati', 'Andhra Pradesh', '522020'),
        'TELANGANA': ('Hyderabad', 'Telangana', '500001'),
        'ODISHA': ('Bhubaneswar', 'Odisha', '751001'),
        'WEST BENGAL': ('Kolkata', 'West Bengal', '700001'),
        'ASSAM': ('Guwahati', 'Assam', '781001'),
        'DELHI': ('New Delhi', 'Delhi', '110001'),
        'DSSSB': ('New Delhi', 'Delhi', '110001'),
    }
    tu = title.upper()
    for kw, (city, state, pin) in STATE_LOCS.items():
        if kw in tu:
            return (f'{state} Government', city, state, pin)
    return ('Government of India', 'New Delhi', 'Delhi', '110001')


def build_job_json_ld(title, dept, last_date, canonical_url):
    """Build JobPosting JSON-LD with all required fields for Google Search Console."""
    import datetime as _dt
    iso_last_date = to_iso_date(last_date) or (_dt.date.today().replace(year=_dt.date.today().year + 1)).isoformat()
    safe_title = normalize_title_text(title)
    desc = f"{safe_title}: {dept} recruitment notification. Last date: {last_date}. Apply at {SITE_NAME}."
    slug = canonical_url.rstrip('/').split('/')[-1].replace('.html', '')
    _street, _city, _region, _pin = _job_location_for(title)
    ld = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": safe_title,
        "description": desc,
        "identifier": {"@type": "PropertyValue", "name": dept, "value": slug},
        "datePosted": TODAY,
        "validThrough": iso_last_date,
        "employmentType": "FULL_TIME",
        "hiringOrganization": {
            "@type": "Organization",
            "name": dept,
            "sameAs": "https://naukridhaba.in",
            "logo": "https://naukridhaba.in/img/og-default.png"
        },
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": _street,
                "addressLocality": _city,
                "addressRegion": _region,
                "postalCode": _pin,
                "addressCountry": "IN"
            }
        },
        "applicantLocationRequirements": {"@type": "Country", "name": "India"},
        "baseSalary": {
            "@type": "MonetaryAmount",
            "currency": "INR",
            "value": {"@type": "QuantitativeValue", "value": "As per Government Norms", "unitText": "MONTH"}
        },
        "url": canonical_url
    }
    import json as _json
    return f'    <script type="application/ld+json">\n    {_json.dumps(ld, ensure_ascii=False)}\n    </script>'


def build_result_json_ld(title, dept, canonical_url):
    """Build WebPage JSON-LD for result pages."""
    return f'''    <script type="application/ld+json">
    {{"@context":"https://schema.org","@type":"WebPage","name":"{normalize_title_text(title)}","description":"{normalize_title_text(title)} result declared. Check at {SITE_NAME}.","url":"{canonical_url}","about":{{"@type":"Organization","name":"{dept}"}}}}
    </script>'''


def build_admit_json_ld(title, dept, canonical_url):
    """Build WebPage JSON-LD for admit card pages."""
    return f'''    <script type="application/ld+json">
    {{"@context":"https://schema.org","@type":"WebPage","name":"{normalize_title_text(title)}","description":"Download {normalize_title_text(title)} admit card at {SITE_NAME}.","url":"{canonical_url}","about":{{"@type":"Organization","name":"{dept}"}}}}
    </script>'''


def build_faq_json_ld(qas):
    """Build FAQPage JSON-LD from list of (question, answer) tuples."""
    entities = json.dumps([
        {"@type": "Question", "name": q,
         "acceptedAnswer": {"@type": "Answer", "text": a}}
        for q, a in qas
    ], ensure_ascii=False)
    return f'    <script type="application/ld+json">\n    {{"@context":"https://schema.org","@type":"FAQPage","mainEntity":{entities}}}\n    </script>'


def build_job_faq_data(detail):
    title = escape(detail['title'])
    dept  = escape(detail['dept'])
    last_d = escape(detail['last_date'])
    posts  = escape(detail['total_posts'])
    age_min = escape(str(detail['age_min']))
    age_max = escape(str(detail['age_max']))
    fee_g  = escape(detail['fee_general'])
    fee_r  = escape(detail['fee_reserved'])
    qual   = escape(detail['qualification'])
    return [
        (f"What is the last date to apply for {title}?",
         f"The last date to apply for {title} is {last_d}. Submit before this deadline to avoid rejection."),
        (f"How many vacancies are available in {title}?",
         f"{'There are ' + posts + ' vacancies advertised under ' + title + '.' if posts and posts != 'Check Notification' else 'The total vacancy count has not been specified yet. Please check the official notification.'}"),
        (f"What is the age limit for {title}?",
         f"The age limit is {age_min} to {age_max} years. Age relaxation applies for SC/ST/OBC/PwD as per government norms."),
        (f"What is the application fee for {title}?",
         f"{'Application fee: General/OBC/EWS — ' + fee_g + ('; SC/ST/PH — ' + fee_r if fee_r else '') + '.' if fee_g else 'Fee details are in the official notification.'}"),
        (f"What qualification is required for {title}?",
         f"Required qualification: {qual}. Verify from the official notification before applying."),
    ]


def build_result_faq_data(detail):
    title  = escape(detail['title'])
    dept   = escape(detail['dept'])
    r_date = escape(detail['result_date'])
    return [
        (f"When was the {title} declared?",
         f"The {title} was declared on {r_date}. Check using the official link on this page."),
        (f"How can I check the {title}?",
         f"Click the result link, enter your roll number or registration ID, verify your details, and download the PDF."),
        ("What documents are needed to check the result?",
         "Keep your admit card (roll number/registration number) and date of birth ready before opening the result portal."),
        (f"What should I do after checking the {title}?",
         f"Download and save the result PDF. If selected, await official instructions from {dept} and keep original documents ready for verification."),
    ]


def build_admit_faq_data(detail):
    title   = escape(detail['title'])
    release = escape(detail['admit_release'])
    exam_dt = escape(detail['exam_date'])
    return [
        (f"When was the {title} released?",
         f"The {title} was released on {release}. Download using the official link on this page."),
        (f"How to download the {title}?",
         "Click the download link, enter your registration number and date of birth, then print the admit card in colour."),
        (f"What is the exam date for {title}?",
         f"The exam date is {exam_dt}. Verify reporting time and exam centre from your admit card."),
        (f"What documents to carry with {title}?",
         f"Carry the printed {title} along with a valid photo ID (Aadhaar / PAN / Passport) to the exam centre."),
    ]


def build_faq_html(qas):
    """Generate FAQ HTML for a list of (question, answer) tuples."""
    items = '\n'.join(
        f'<div style="border-bottom:1px solid #eee;padding:1rem 0;">'
        f'<h3 style="color:var(--primary);margin:0 0 .4rem;font-size:1rem;">{q}</h3>'
        f'<div>'
        f'<p style="color:#444;line-height:1.8;margin:0;">{a}</p>'
        f'</div></div>'
        for q, a in qas
    )
    return (
        '<div style="background:var(--surface);padding:1.5rem;border-radius:8px;margin:1.5rem 0;">'
        '<h2 style="color:var(--primary);margin-top:0;">Frequently Asked Questions</h2>'
        + items + '</div>'
    )


def build_breadcrumb_json_ld(items):
    """Build BreadcrumbList JSON-LD."""
    elements = ','.join([
        f'{{"@type":"ListItem","position":{i+1},"name":"{name}","item":"{url}"}}'
        for i, (name, url) in enumerate(items)
    ])
    return f'''    <script type="application/ld+json">
    {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{elements}]}}
    </script>'''


def fix_broken_buttons(content):
    """Fix result/admit card buttons that show alert()."""
    # Remove alert handlers from buttons.
    content = re.sub(
        r'<a\s+href="#"\s+onclick="alert\([^)]+\)"([^>]*)>',
        r'<a href="#"\1>',
        content
    )
    # Also fix: onclick="alert('Result checking will be available here')"
    content = re.sub(
        r'\s*onclick="alert\([^)]*\)"',
        '',
        content
    )
    # Replace dead primary action anchors with spans so no page ships with href="#".
    content = re.sub(
        r'<a\s+href="#"\s+([^>]*class="btn[^"]*btn--primary[^"]*"[^>]*)>(.*?)</a>',
        r'<span \1>\2</span>',
        content,
        flags=re.IGNORECASE | re.DOTALL
    )
    content = re.sub(
        r'<a\s+href="#"\s+([^>]*class="btn[^"]*"[^>]*)>(.*?)</a>',
        r'<span \1>\2</span>',
        content,
        flags=re.IGNORECASE | re.DOTALL
    )
    # V2 template: remove target="_blank" from placeholder link-item anchors (href="#").
    # A link that goes nowhere should never open a new tab.
    content = re.sub(
        r'(<a\s+href="#"[^>]*class="link-item"[^>]*)\s+target="_blank"',
        r'\1',
        content,
        flags=re.IGNORECASE | re.DOTALL
    )
    content = re.sub(
        r'(<a\s+href="#"[^>]*)target="_blank"\s*([^>]*class="link-item")',
        r'\1\2',
        content,
        flags=re.IGNORECASE | re.DOTALL
    )
    return content


def fix_nan_links(content):
    """Fix href="nan" and similar broken links."""
    # Fix Apply Online button with href="nan"
    content = re.sub(
        r'href="nan"([^>]*class="btn btn--primary[^"]*")',
        r'data-missing-link="true" style="opacity:0.7;cursor:default;"\1',
        content
    )
    content = re.sub(
        r'href="nan"',
        r'data-missing-link="true"',
        content
    )
    # Fix "nan" in text content
    content = re.sub(r'>nan<', '><span style="color:#999">Check Notification</span><', content)
    # Fix age limit "21.0-32.0 Years" format
    content = re.sub(
        r'(\d+)\.0-(\d+)\.0\s*Years',
        lambda m: f'{int(m.group(1))}-{int(m.group(2))} Years',
        content
    )
    return content


def remove_sarkariresult_urls(content):
    """Remove/replace all SarkariResult URLs."""
    protected_attrs = {}

    def protect_attr(match):
        token = f"__ND_ATTR_{len(protected_attrs)}__"
        protected_attrs[token] = match.group(0)
        return token

    # Protect existing href/src URLs so text cleanup does not corrupt redirect targets.
    content = re.sub(
        r'''(?:href|src)=(".*?"|'.*?')''',
        protect_attr,
        content,
        flags=re.IGNORECASE | re.DOTALL
    )

    # Replace SarkariResult document URLs in visible text blocks.
    for pattern in BANNED_URL_PATTERNS:
        content = re.sub(pattern, '#', content, flags=re.IGNORECASE)

    # Replace SarkariResult text mentions
    content = re.sub(r'sarkariresult(?:s)?\.(?:com|org|in|net)', 'naukridhaba.in', content, flags=re.IGNORECASE)
    content = re.sub(r'\bSarkariResult(?:s)?\b', SITE_NAME, content)
    content = re.sub(r'\bsarkariresult(?:s)?\b', SITE_NAME, content, flags=re.IGNORECASE)
    content = re.sub(r'sarkari\s+result(?:s)?', SITE_NAME, content, flags=re.IGNORECASE)
    content = re.sub(r'doc\.sarkariresults?\.org\.in', 'naukridhaba.in', content, flags=re.IGNORECASE)

    for token, original in protected_attrs.items():
        content = content.replace(token, original)

    return content


def wrap_source_links(content):
    """Wrap any direct source host href/src through the redirect proxy.

    Handles:
    - Absolute URLs whose host is in SOURCE_HOSTS
    - Absolute URLs from related org.in subdomains (www.sarkariresults.org.in)
    - Relative paths that contain SarkariResult branding in the filename
    """
    _SARKARI_PATH_RE = re.compile(r'sarkariresult', re.IGNORECASE)

    def repl(match):
        attr = match.group(1)
        quote_char = match.group(2)
        url = match.group(3)
        # Skip anchor links and already-wrapped redirects
        if url.startswith('#') or REDIRECT_PATH in url:
            return match.group(0)
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        # Wrap absolute URLs whose host is in SOURCE_HOSTS
        if netloc and netloc in SOURCE_HOSTS:
            wrapped = f'{REDIRECT_PATH}?target={quote(url, safe="")}'
            return f'{attr}={quote_char}{wrapped}{quote_char}'
        # Wrap absolute URLs from sarkariresults.org.in variants
        if netloc and _SARKARI_PATH_RE.search(netloc):
            wrapped = f'{REDIRECT_PATH}?target={quote(url, safe="")}'
            return f'{attr}={quote_char}{wrapped}{quote_char}'
        # Remove relative paths that contain SarkariResult in the filename
        # (e.g., /upload/SarkariResult.Com_SSB_...pdf)
        if not netloc and _SARKARI_PATH_RE.search(parsed.path):
            return f'{attr}={quote_char}#{quote_char}'
        return match.group(0)

    return re.sub(
        r'(href|src)=(["\'])([^"\']+)\2',
        repl,
        content,
        flags=re.IGNORECASE,
    )


def fix_malformed_redirect_hosts(content):
    """Repair broken hostnames introduced by older text replacement passes."""
    return re.sub(
        r'(?:www\.)?naukri\s+dhaba\.com',
        'www.sarkariresult.com',
        content,
        flags=re.IGNORECASE
    )


def fix_source_redirect_targets(content):
    """Replace go.html?target=<source-host-url> links with '#' to avoid validation failures.

    Source-host PDF/upload links were scraped but cannot be legitimately served
    through the redirect proxy — they point back to the scraping source.
    """
    from urllib.parse import unquote, parse_qs

    def repl(match):
        quote_char = match.group(1)
        url = match.group(2)
        # Decode the target parameter
        if REDIRECT_PATH not in url:
            return match.group(0)
        try:
            query = url.split('?', 1)[1] if '?' in url else ''
            target = parse_qs(query).get('target', [None])[0]
            if not target:
                return match.group(0)
            target = unquote(target)
            from urllib.parse import urlparse as _up
            netloc = _up(target).netloc.lower()
            if netloc in SOURCE_HOSTS:
                return f'href={quote_char}#{quote_char}'
        except Exception:
            pass
        return match.group(0)

    return re.sub(
        r'href=(["\'])([^"\']*go\.html[^"\']*)\1',
        repl,
        content,
        flags=re.IGNORECASE,
    )


def add_tracking_scripts(content, filepath):
    """Add tracking.js and ads-manager.js to <head>."""
    tracking_path = get_js_path(filepath, 'tracking.js')
    ads_path = get_js_path(filepath, 'ads-manager.js')
    tracking_tag = f'<script src="{tracking_path}"></script>'
    ads_tag = f'<script src="{ads_path}" defer></script>'

    # Check if already added
    if 'tracking.js' in content and 'ads-manager.js' in content:
        return content

    if 'tracking.js' not in content:
        # Add before </head> or after <link rel="stylesheet">
        content = re.sub(
            r'(<link[^>]+style\.css[^>]*>)',
            r'\1\n    ' + tracking_tag,
            content,
            count=1
        )

    if 'ads-manager.js' not in content:
        content = re.sub(
            r'(</head>)',
            f'    {ads_tag}\n\\1',
            content,
            count=1
        )

    return content


def update_ad_slots(content):
    """Add data-ad-slot attributes and nd-ad class to existing ad divs."""
    # Main content ad slot (728x90)
    content = re.sub(
        r'<div class="ad-slot">Advertisement Space 728x90</div>',
        '<div class="nd-ad ad-slot" data-ad-slot="header-banner">Advertisement Space 728x90</div>',
        content
    )
    content = re.sub(
        r'<div class="ad-slot">Advertisement Space</div>',
        '<div class="nd-ad ad-slot" data-ad-slot="content-bottom">Advertisement Space</div>',
        content
    )
    # Sidebar ad slot (300x250)
    content = re.sub(
        r'<div class="ad-slot" style="min-height:250px;">\s*<p>Advertisement</p>\s*<p[^>]*>300x250</p>\s*</div>',
        '<div class="nd-ad ad-slot" data-ad-slot="sidebar-top" style="min-height:250px;"><p>Advertisement</p><p style="font-size:0.75rem;">300x250</p></div>',
        content
    )
    return content


def rebuild_head(content, data, page_type, filepath, canonical_url):
    """Replace the <head> content with upgraded SEO version."""
    meta_block = build_meta_block(data, page_type, filepath, canonical_url)
    ads_path = get_js_path(filepath, 'ads-manager.js')
    css_path = get_css_path(filepath)
    tracking_block = build_head_tracking_markup(filepath)

    # Extract the existing <head> block so we can preserve V2 assets.
    existing_head_m = re.search(r'<head>(.*?)</head>', content, re.DOTALL)
    existing_head = existing_head_m.group(1) if existing_head_m else ''

    # Collect any extra <script> tags in the existing head that are NOT
    # tracking/ads scripts (e.g. header-footer.js injected by the scraper).
    extra_head_scripts = ''
    hf_js_path = get_js_path(filepath, 'header-footer.js')
    if hf_js_path not in existing_head:
        # header-footer.js is already referenced in the page body for V2 pages;
        # only add it to head if it isn't present anywhere in the file.
        if 'header-footer.js' not in content:
            extra_head_scripts = f'    <script src="{hf_js_path}" defer></script>\n'

    # Build JSON-LD
    json_ld_blocks = ''
    title = data.get('title', '')
    dept = data.get('dept', 'Government')

    if page_type in {'job', 'result', 'admit_card'}:
        # For V2 detail pages the scraper already injected rich JSON-LD blocks
        # (JobPosting with identifier/qualifications, FAQPage, etc.).
        # Preserve ALL existing ld+json blocks from the head rather than
        # replacing them with simpler generated ones.
        existing_ld = re.findall(
            r'<script type="application/ld\+json">.*?</script>',
            existing_head, re.DOTALL
        )
        if existing_ld:
            json_ld_blocks = '\n'.join(existing_ld)
        else:
            # Fallback: generate minimal blocks for pages that have none yet.
            if page_type == 'job':
                m = re.search(r'info-item__value[^>]*>([^<]{5,20})</span>', content)
                last_date = m.group(1).strip() if m else TODAY
                if not to_iso_date(last_date):
                    last_date = TODAY
                json_ld_blocks = build_job_json_ld(title, dept, last_date, canonical_url)
            elif page_type == 'result':
                json_ld_blocks = build_result_json_ld(title, dept, canonical_url)
            else:
                json_ld_blocks = build_admit_json_ld(title, dept, canonical_url)
            json_ld_blocks += '\n' + build_breadcrumb_json_ld([
                (SITE_NAME, site_route('index.html')),
                ({'job': 'Jobs', 'result': 'Results', 'admit_card': 'Admit Cards'}[page_type],
                 site_route({'job': 'latest-jobs.html', 'result': 'results.html', 'admit_card': 'admit-cards.html'}[page_type])),
                (dept, site_route({'job': 'latest-jobs.html', 'result': 'results.html', 'admit_card': 'admit-cards.html'}[page_type])),
                (title, canonical_url)
            ])
    elif page_type in {'jobs_list', 'results_list', 'admits_list'}:
        # Preserve the existing ItemList JSON-LD that replace_listing_sections() injects.
        # Rebuilding the head would otherwise wipe the structured data listing.
        existing_jsonld = re.search(
            r'<script type="application/ld\+json">.*?</script>',
            content, re.DOTALL
        )
        if existing_jsonld:
            json_ld_blocks = existing_jsonld.group(0)
    elif page_type == 'home':
        # Homepage requires Organization + WebSite schemas for validation
        json_ld_blocks = f'''    <script type="application/ld+json">
    {{"@context":"https://schema.org","@type":"Organization","name":"{SITE_NAME}","url":"{SITE_URL}/","logo":"{SITE_URL}/img/og-default.png","sameAs":[]}}
    </script>
    <script type="application/ld+json">
    {{"@context":"https://schema.org","@type":"WebSite","name":"{SITE_NAME}","url":"{SITE_URL}/","potentialAction":{{"@type":"SearchAction","target":{{"@type":"EntryPoint","urlTemplate":"{SITE_URL}/latest-jobs.html?q={{search_term_string}}"}},"query-input":"required name=search_term_string"}}}}
    </script>'''

    # Build complete new head content
    new_head = f'''<head>
{meta_block}
    <link rel="stylesheet" href="{css_path}">
{tracking_block}
{json_ld_blocks}
{extra_head_scripts}    <script src="{ads_path}" defer></script>
</head>'''

    # Replace old head block
    content = re.sub(r'<head>.*?</head>', new_head, content, count=1, flags=re.DOTALL)
    return content


def inject_body_tracking(content):
    """Inject body-start tracking markup such as GTM noscript."""
    body_markup = build_body_tracking_markup()
    if not body_markup:
        return content
    if 'googletagmanager.com/ns.html' in content:
        return content
    return re.sub(r'(<body[^>]*>)', r'\1' + '\n' + body_markup, content, count=1, flags=re.IGNORECASE)


def update_page(filepath, dry_run=False):
    """Apply all updates to a single HTML file."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        original = f.read()

    content = original

    # Step 0: Repair malformed redirect targets from earlier rewrites
    content = fix_malformed_redirect_hosts(content)

    # Step 0b: Remove go.html redirect links that still target source hosts
    content = fix_source_redirect_targets(content)

    # Step 1: Remove SarkariResult references
    content = remove_sarkariresult_urls(content)

    # Step 1b: Wrap any remaining direct source host links through redirect proxy
    content = wrap_source_links(content)

    # Step 2: Fix broken buttons
    content = fix_broken_buttons(content)

    # Step 3: Fix nan links
    content = fix_nan_links(content)

    # Step 4: Update ad slots
    content = update_ad_slots(content)

    # Step 4b: Normalize top-level internal links to deployed pretty URLs
    content = normalize_root_links(content)
    content = content.replace(
        'Your gateway to Sarkari Naukri. Latest government jobs, results, and admit cards.',
        'Independent government job updates, result tracking, and admit card alerts for India.'
    )
    content = content.replace(', Sarkari Naukri', '')
    content = content.replace('Sarkari Naukri, ', '')

    # Step 5: Extract existing data
    data = extract_from_html(content)
    page_type = detect_page_type(filepath, content)
    canonical_url = get_canonical_url(filepath)

    # Step 6: Rebuild head with complete SEO
    content = rebuild_head(content, data, page_type, filepath, canonical_url)
    content = inject_body_tracking(content)
    if page_type in {'job', 'result', 'admit_card'}:
        content = rebuild_detail_main(content, filepath, page_type)

    if content == original:
        return False  # No changes

    if not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

    return True


def main():
    parser = argparse.ArgumentParser(description='Naukri Dhaba Mass Page Updater')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing')
    parser.add_argument('--path', default=None, help='Update only this file/directory')
    args = parser.parse_args()

    if args.dry_run:
        log("DRY RUN MODE - No files will be modified")
        log("")

    # Find all HTML files
    if args.path:
        search_path = Path(args.path)
        if search_path.is_file():
            html_files = [search_path]
        else:
            html_files = list(search_path.rglob('*.html'))
    else:
        html_files = [
            f for f in SITE_ROOT.rglob('*.html')
            if '.git' not in str(f) and 'scraper' not in str(f) and f.name != 'go.html'
        ]

    log(f"Found {len(html_files)} HTML files to process")
    log("")

    updated = 0
    skipped = 0
    errors = 0

    for i, filepath in enumerate(sorted(html_files), 1):
        rel = filepath.relative_to(SITE_ROOT)
        try:
            changed = update_page(filepath, dry_run=args.dry_run)
            if changed:
                updated += 1
                status = "UPDATED" if not args.dry_run else "WOULD UPDATE"
                log(f"  [{i:3d}/{len(html_files)}] {status}: {rel}")
            else:
                skipped += 1
                log(f"  [{i:3d}/{len(html_files)}] NO CHANGE: {rel}")
        except Exception as e:
            errors += 1
            log(f"  [{i:3d}/{len(html_files)}] ERROR: {rel} - {e}")

    log("")
    log("=" * 60)
    log(f"COMPLETE: {updated} updated, {skipped} unchanged, {errors} errors")
    if args.dry_run:
        log("(DRY RUN - no files were modified)")
    log("=" * 60)


if __name__ == '__main__':
    main()

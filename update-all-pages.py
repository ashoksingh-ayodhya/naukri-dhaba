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
import argparse
from pathlib import Path
from datetime import date

SITE_ROOT = Path(__file__).parent
SITE_URL = 'https://www.naukridhaba.in'
SITE_NAME = 'Naukri Dhaba'
TODAY = date.today().isoformat()

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
    'government': 'Sarkari Naukri 2026, Govt Jobs India, Government Jobs Online Form',
}

def log(msg):
    print(msg)

def slugify_title(text):
    """Simple slugify."""
    text = str(text).lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')[:80]


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
    # Clean title
    data['title'] = re.sub(r'\s*\|\s*' + re.escape(SITE_NAME) + r'.*$', '', data['title']).strip()
    data['title'] = re.sub(r'\s+\d{4}$', '', data['title']).strip()  # Remove trailing year

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


def get_canonical_url(filepath):
    """Get canonical URL for a file."""
    rel = str(filepath.relative_to(SITE_ROOT)).replace('\\', '/')
    if rel == 'index.html':
        return SITE_URL + '/'
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


def get_keywords(page_type, title, dept):
    """Auto-generate SEO keywords."""
    dept_lower = dept.lower()
    base_kws = SEO_KEYWORDS_MAP.get('government', '')
    for key, kws in SEO_KEYWORDS_MAP.items():
        if key in dept_lower or key in title.lower():
            base_kws = kws
            break

    year = date.today().year
    extra_kws = [
        title,
        f"{dept} Jobs {year}",
        f"{title} {year}",
        "Sarkari Naukri",
        "Govt Jobs Online Form",
        SITE_NAME
    ]
    return base_kws + ', ' + ', '.join([k for k in extra_kws if k and 'nan' not in k.lower()])


def build_meta_block(data, page_type, filepath, canonical_url):
    """Build complete SEO meta tag block."""
    title = data.get('title', SITE_NAME)
    description = data.get('description', f"{title} - Check details at {SITE_NAME}")
    dept = data.get('dept', 'Government')
    location = data.get('location', 'India')

    keywords = get_keywords(page_type, title, dept)
    og_title = f"{title} | {SITE_NAME}"
    og_desc = description[:160] if description else og_title

    # Page type suffix for title
    type_suffix = {
        'job': 'Apply Online',
        'result': 'Check Result',
        'admit_card': 'Download Admit Card',
        'jobs_list': 'Latest Government Jobs 2026',
        'results_list': 'Exam Results 2026',
        'admits_list': 'Admit Cards 2026',
        'home': 'Sarkari Naukri 2026 | Govt Jobs, Results, Admit Cards',
        'other': 'Sarkari Naukri'
    }.get(page_type, 'Sarkari Naukri')

    full_title = f"{title} - {type_suffix} | {SITE_NAME}" if type_suffix not in title else f"{title} | {SITE_NAME}"

    return f'''    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{full_title}</title>
    <meta name="description" content="{og_desc}">
    <meta name="keywords" content="{keywords}">
    <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
    <meta name="author" content="{SITE_NAME}">
    <link rel="canonical" href="{canonical_url}">
    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="{og_title}">
    <meta property="og:description" content="{og_desc}">
    <meta property="og:url" content="{canonical_url}">
    <meta property="og:site_name" content="{SITE_NAME}">
    <meta property="og:locale" content="hi_IN">
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{og_title}">
    <meta name="twitter:description" content="{og_desc}">
    <!-- India Geo -->
    <meta name="geo.region" content="IN">
    <meta name="geo.placename" content="{location}">'''


def build_job_json_ld(title, dept, last_date, canonical_url):
    """Build JobPosting JSON-LD."""
    return f'''    <script type="application/ld+json">
    {{"@context":"https://schema.org","@type":"JobPosting","title":"{title}","datePosted":"{TODAY}","validThrough":"{last_date}","employmentType":"FULL_TIME","hiringOrganization":{{"@type":"Organization","name":"{dept}"}},"jobLocation":{{"@type":"Place","address":{{"@type":"PostalAddress","addressCountry":"IN"}}}},"url":"{canonical_url}"}}
    </script>'''


def build_result_json_ld(title, dept, canonical_url):
    """Build Event JSON-LD for result pages."""
    return f'''    <script type="application/ld+json">
    {{"@context":"https://schema.org","@type":"Event","name":"{title}","description":"{title} result declared. Check at {SITE_NAME}.","startDate":"{TODAY}","organizer":{{"@type":"Organization","name":"{dept}"}},"location":{{"@type":"VirtualLocation","url":"{canonical_url}"}}}}
    </script>'''


def build_admit_json_ld(title, dept, canonical_url):
    """Build Event JSON-LD for admit card pages."""
    return f'''    <script type="application/ld+json">
    {{"@context":"https://schema.org","@type":"Event","name":"{title}","description":"Download {title} admit card at {SITE_NAME}.","startDate":"{TODAY}","organizer":{{"@type":"Organization","name":"{dept}"}},"location":{{"@type":"VirtualLocation","url":"{canonical_url}"}}}}
    </script>'''


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
    # Fix: onclick="alert('...')" → remove onclick, keep href="#" as is (handled per page type later)
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
    return content


def fix_nan_links(content):
    """Fix href="nan" and similar broken links."""
    # Fix Apply Online button with href="nan"
    content = re.sub(
        r'href="nan"([^>]*class="btn btn--primary[^"]*")',
        r'href="#" style="opacity:0.7;cursor:default;"\1',
        content
    )
    content = re.sub(
        r'href="nan"',
        r'href="#"',
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
    # Replace SarkariResult document URLs (PDFs etc.) with #
    for pattern in BANNED_URL_PATTERNS:
        content = re.sub(pattern, '#', content, flags=re.IGNORECASE)

    # Replace SarkariResult text mentions
    content = re.sub(r'\bSarkariResult(?:s)?\b', SITE_NAME, content)
    content = re.sub(r'\bsarkariresult(?:s)?\b', SITE_NAME, content, flags=re.IGNORECASE)
    content = re.sub(r'sarkariresult(?:s)?\.(?:com|org|in|net)', 'naukridhaba.in', content, flags=re.IGNORECASE)
    content = re.sub(r'sarkari\s+result(?:s)?', SITE_NAME, content, flags=re.IGNORECASE)
    content = re.sub(r'doc\.sarkariresults?\.org\.in', 'naukridhaba.in', content, flags=re.IGNORECASE)

    return content


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
    tracking_path = get_js_path(filepath, 'tracking.js')
    ads_path = get_js_path(filepath, 'ads-manager.js')
    css_path = get_css_path(filepath)

    # Build JSON-LD
    json_ld_blocks = ''
    title = data.get('title', '')
    dept = data.get('dept', 'Government')

    if page_type == 'job':
        # Extract last_date from content
        m = re.search(r'info-item__value[^>]*>([^<]{5,20})</span>', content)
        last_date = m.group(1).strip() if m else TODAY
        if not re.search(r'\d{2}[/-]\d{2}[/-]\d{4}', last_date):
            last_date = TODAY
        json_ld_blocks = build_job_json_ld(title, dept, last_date, canonical_url)
        # Add breadcrumb
        json_ld_blocks += '\n' + build_breadcrumb_json_ld([
            (SITE_NAME, SITE_URL + '/'),
            ('Jobs', SITE_URL + '/latest-jobs.html'),
            (dept, SITE_URL + '/latest-jobs.html'),
            (title, canonical_url)
        ])
    elif page_type == 'result':
        if '<script type="application/ld+json">' not in content:
            json_ld_blocks = build_result_json_ld(title, dept, canonical_url)
            json_ld_blocks += '\n' + build_breadcrumb_json_ld([
                (SITE_NAME, SITE_URL + '/'),
                ('Results', SITE_URL + '/results.html'),
                (dept, SITE_URL + '/results.html'),
                (title, canonical_url)
            ])
    elif page_type == 'admit_card':
        if '<script type="application/ld+json">' not in content:
            json_ld_blocks = build_admit_json_ld(title, dept, canonical_url)
            json_ld_blocks += '\n' + build_breadcrumb_json_ld([
                (SITE_NAME, SITE_URL + '/'),
                ('Admit Cards', SITE_URL + '/admit-cards.html'),
                (dept, SITE_URL + '/admit-cards.html'),
                (title, canonical_url)
            ])

    # Build complete new head content
    new_head = f'''<head>
{meta_block}
    <link rel="stylesheet" href="{css_path}">
    <script src="{tracking_path}"></script>
{json_ld_blocks}
    <script src="{ads_path}" defer></script>
</head>'''

    # Replace old head block
    content = re.sub(r'<head>.*?</head>', new_head, content, count=1, flags=re.DOTALL)
    return content


def update_page(filepath, dry_run=False):
    """Apply all updates to a single HTML file."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        original = f.read()

    content = original

    # Step 1: Remove SarkariResult references
    content = remove_sarkariresult_urls(content)

    # Step 2: Fix broken buttons
    content = fix_broken_buttons(content)

    # Step 3: Fix nan links
    content = fix_nan_links(content)

    # Step 4: Update ad slots
    content = update_ad_slots(content)

    # Step 5: Extract existing data
    data = extract_from_html(content)
    page_type = detect_page_type(filepath, content)
    canonical_url = get_canonical_url(filepath)

    # Step 6: Rebuild head with complete SEO
    content = rebuild_head(content, data, page_type, filepath, canonical_url)

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
            if '.git' not in str(f) and 'scraper' not in str(f)
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

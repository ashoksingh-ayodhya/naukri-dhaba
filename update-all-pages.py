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

from site_config import PRETTY_ROUTE_MAP, SITE_NAME, SITE_URL

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
    'consentMode': {'enabled': False, 'storageKey': 'nd_consent_v1', 'waitForUpdateMs': 500, 'bannerEnabled': True},
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


def normalize_title_text(title):
    title = clean_text(title)
    title = re.sub(r'\s*\|\s*' + re.escape(SITE_NAME) + r'.*$', '', title, flags=re.I)
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
    """Convert top-level .html links to deployed extensionless routes."""
    filename_to_path = {name: pretty_root_path(name) for name in PRETTY_ROUTE_MAP if name != 'index.html'}
    filename_to_path['index.html'] = '/'

    def repl(match):
        attr = match.group('attr')
        quote = match.group('quote')
        url = match.group('url')
        suffix = match.group('suffix') or ''
        parsed = url
        prefix = ''

        if parsed.startswith(SITE_URL + '/'):
            prefix = SITE_URL
            parsed = parsed[len(SITE_URL):]

        filename = parsed.split('/')[-1]
        if filename not in filename_to_path:
            return match.group(0)

        new_url = filename_to_path[filename] + suffix
        if prefix:
            new_url = prefix + new_url
        return f'{attr}={quote}{new_url}{quote}'

    pattern = re.compile(
        r'(?P<attr>href|src)=(?P<quote>["\'])(?P<url>(?:https://naukridhaba\.in/)?(?:/|(?:\.\./)*)'
        r'(?:index|latest-jobs|results|admit-cards|resources|previous-papers|eligibility-calculator|study-planner)\.html)'
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
    wait_for_update = int(consent.get('waitForUpdateMs', 500) or 500)
    return '\n'.join([
        '    <script>',
        '      (function(w){',
        '        var consentKey = "' + storage_key + '";',
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
        '        var initialMode = readStoredMode();',
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


def get_keywords(page_type, title, dept):
    """Auto-generate SEO keywords."""
    dept_lower = dept.lower()
    base_kws = SEO_KEYWORDS_MAP.get('government', '')
    for key, kws in SEO_KEYWORDS_MAP.items():
        if key in dept_lower or key in title.lower():
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
                'Government Jobs India, Sarkari Naukri, Latest Govt Jobs, Exam Results, Admit Card',
                SITE_NAME,
            ),
        },
        'jobs_list': {
            'title': f'Latest Govt Jobs 2026 | {SITE_NAME}',
            'description': f'Browse the latest government jobs, online forms, and recruitment updates across India on {SITE_NAME}.',
            'keywords': dedupe_csv(
                'Latest Govt Jobs 2026, Government Jobs India, Online Form, Sarkari Naukri',
                SITE_NAME,
            ),
        },
        'results_list': {
            'title': f'Latest Results 2026 | {SITE_NAME}',
            'description': f'Check the latest government exam results, merit lists, and score cards on {SITE_NAME}.',
            'keywords': dedupe_csv(
                'Latest Results 2026, Sarkari Result, Exam Result, Score Card, Merit List',
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
        keywords = get_keywords(page_type, title, dept)
        og_title = f"{title} | {SITE_NAME}"
        og_desc = (description[:160] if description else og_title)

        type_suffix = {
            'job': 'Apply Online',
            'result': 'Check Result',
            'admit_card': 'Download Admit Card',
            'other': 'Sarkari Naukri'
        }.get(page_type, 'Sarkari Naukri')

        full_title = (
            f"{title} | {SITE_NAME}"
            if title_already_has_intent(title, page_type) or type_suffix.lower() in title.lower()
            else f"{title} - {type_suffix} | {SITE_NAME}"
        )

    og_type = 'article' if page_type in {'job', 'result', 'admit_card'} else 'website'

    return f'''    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{full_title}</title>
    <meta name="description" content="{og_desc}">
    <meta name="keywords" content="{keywords}">
    <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
    <meta name="author" content="{SITE_NAME}">
    <link rel="canonical" href="{canonical_url}">
    <!-- Open Graph -->
    <meta property="og:type" content="{og_type}">
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
    iso_last_date = to_iso_date(last_date) or TODAY
    return f'''    <script type="application/ld+json">
    {{"@context":"https://schema.org","@type":"JobPosting","title":"{normalize_title_text(title)}","datePosted":"{TODAY}","validThrough":"{iso_last_date}","employmentType":"FULL_TIME","hiringOrganization":{{"@type":"Organization","name":"{dept}"}},"jobLocation":{{"@type":"Place","address":{{"@type":"PostalAddress","addressCountry":"IN"}}}},"url":"{canonical_url}"}}
    </script>'''


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


def fix_malformed_redirect_hosts(content):
    """Repair broken hostnames introduced by older text replacement passes."""
    return re.sub(
        r'(?:www\.)?naukri\s+dhaba\.com',
        'www.sarkariresult.com',
        content,
        flags=re.IGNORECASE
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

    # Build JSON-LD
    json_ld_blocks = ''
    title = data.get('title', '')
    dept = data.get('dept', 'Government')

    if page_type == 'job':
        # Extract last_date from content
        m = re.search(r'info-item__value[^>]*>([^<]{5,20})</span>', content)
        last_date = m.group(1).strip() if m else TODAY
        if not to_iso_date(last_date):
            last_date = TODAY
        json_ld_blocks = build_job_json_ld(title, dept, last_date, canonical_url)
        # Add breadcrumb
        json_ld_blocks += '\n' + build_breadcrumb_json_ld([
            (SITE_NAME, site_route('index.html')),
            ('Jobs', site_route('latest-jobs.html')),
            (dept, site_route('latest-jobs.html')),
            (title, canonical_url)
        ])
    elif page_type == 'result':
        json_ld_blocks = build_result_json_ld(title, dept, canonical_url)
        json_ld_blocks += '\n' + build_breadcrumb_json_ld([
            (SITE_NAME, site_route('index.html')),
            ('Results', site_route('results.html')),
            (dept, site_route('results.html')),
            (title, canonical_url)
        ])
    elif page_type == 'admit_card':
        json_ld_blocks = build_admit_json_ld(title, dept, canonical_url)
        json_ld_blocks += '\n' + build_breadcrumb_json_ld([
            (SITE_NAME, site_route('index.html')),
            ('Admit Cards', site_route('admit-cards.html')),
            (dept, site_route('admit-cards.html')),
            (title, canonical_url)
        ])

    # Build complete new head content
    new_head = f'''<head>
{meta_block}
    <link rel="stylesheet" href="{css_path}">
{tracking_block}
{json_ld_blocks}
    <script src="{ads_path}" defer></script>
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

    # Step 1: Remove SarkariResult references
    content = remove_sarkariresult_urls(content)

    # Step 2: Fix broken buttons
    content = fix_broken_buttons(content)

    # Step 3: Fix nan links
    content = fix_nan_links(content)

    # Step 4: Update ad slots
    content = update_ad_slots(content)

    # Step 4b: Normalize top-level internal links to deployed pretty URLs
    content = normalize_root_links(content)

    # Step 5: Extract existing data
    data = extract_from_html(content)
    page_type = detect_page_type(filepath, content)
    canonical_url = get_canonical_url(filepath)

    # Step 6: Rebuild head with complete SEO
    content = rebuild_head(content, data, page_type, filepath, canonical_url)
    content = inject_body_tracking(content)

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

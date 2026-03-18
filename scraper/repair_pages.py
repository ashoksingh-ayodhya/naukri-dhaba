#!/usr/bin/env python3
"""
repair_pages.py — Patches existing static HTML pages in-place.

Fixes applied:
  1. Telegram URL trailing space  (all pages)
  2. Department label "Government" → inferred acronym  (job detail pages)
  3. Adds unique description paragraph below H1  (job detail pages)
  4. Notification button "#" → Google search URL  (job detail pages)
  5. sanitize_url: replace any residual naukridhaba.in internal links → '#'
"""

import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

# ── import helpers from the scraper ────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from sarkari_scraper import infer_dept, build_unique_desc, get_category, SITE_ROOT

# ──────────────────────────────────────────────────────────
# Helper: extract text of an info-item by label keyword
# ──────────────────────────────────────────────────────────
def extract_info(html: str, label_keyword: str) -> str:
    pattern = (
        r'info-item__label[^>]*>[^<]*' + re.escape(label_keyword) + r'[^<]*</span>'
        r'\s*<span[^>]*info-item__value[^>]*>(.*?)</span>'
    )
    m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    if m:
        # strip inner tags
        return re.sub(r'<[^>]+>', '', m.group(1)).strip()
    return ''


def extract_title(html: str) -> str:
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if m:
        # strip the year badge span
        raw = re.sub(r'<span[^>]*>.*?</span>', '', m.group(1), flags=re.DOTALL)
        return re.sub(r'<[^>]+>', '', raw).strip()
    return ''


def reconstruct_d(html: str) -> dict:
    """Partially reconstruct data dict from existing HTML for description building."""
    title       = extract_title(html)
    last_date   = extract_info(html, 'Last Date')
    total_posts = extract_info(html, 'Total Posts')
    age_raw     = extract_info(html, 'Age Limit')  # e.g. "21–37 Years" or "21-37 Years"
    fee_raw     = extract_info(html, 'General / OBC')

    age_min = age_max = ''
    age_m = re.search(r'(\d+)\s*[–\-]\s*(\d+)', age_raw or '')
    if age_m:
        age_min, age_max = age_m.group(1), age_m.group(2)

    # Extract apply URL
    apply_m = re.search(r'btn--primary btn--large[^>]*href="([^"]+)"', html)
    if not apply_m:
        apply_m = re.search(r'href="([^"]+)"[^>]*class="btn btn--primary btn--large"', html)
    apply_url = apply_m.group(1) if apply_m else '#'

    return {
        'title':       title,
        'last_date':   last_date or 'Check Notification',
        'total_posts': total_posts if total_posts not in ('Check Notification', '') else None,
        'age_min':     age_min,
        'age_max':     age_max,
        'fee_general': fee_raw or '',
        'apply_url':   apply_url,
    }


# ──────────────────────────────────────────────────────────
# Fix 1 — Telegram trailing space
# ──────────────────────────────────────────────────────────
def fix_telegram(html: str) -> str:
    return html.replace('https://t.me/naukridhaba ', 'https://t.me/naukridhaba')


# ──────────────────────────────────────────────────────────
# Fix 2 — Department "Government" → inferred acronym
# ──────────────────────────────────────────────────────────
def fix_department(html: str, title: str) -> tuple[str, str]:
    """Returns (updated_html, new_dept)."""
    # Only fix if it currently shows 'Government'
    if '<span class="info-item__value">Government</span>' not in html:
        current = re.search(r'🏢 Department.*?info-item__value[^>]*>([^<]+)<', html, re.DOTALL)
        current_dept = current.group(1).strip() if current else 'Government'
        return html, current_dept

    new_dept = infer_dept(title)
    if new_dept == 'Government':
        return html, 'Government'

    html = html.replace(
        '<span class="info-item__value">Government</span>',
        f'<span class="info-item__value">{new_dept}</span>',
        1
    )
    return html, new_dept


# ──────────────────────────────────────────────────────────
# Fix 3 — Add unique description paragraph below H1
# ──────────────────────────────────────────────────────────
_DESC_MARKER = 'style="color:#555;font-size:1rem;line-height:1.7;margin:.75rem 0 1.25rem;"'

def fix_add_description(html: str, d: dict, dept: str) -> str:
    # Skip if already has the description paragraph
    if _DESC_MARKER in html:
        return html

    desc_text = build_unique_desc(d, dept)
    if not desc_text:
        return html

    desc_para = f'\n      <p style="color:#555;font-size:1rem;line-height:1.7;margin:.75rem 0 1.25rem;">{desc_text}</p>\n'

    # Insert after closing </h1>
    html = re.sub(r'(</h1>)', r'\1' + desc_para, html, count=1)
    return html


# ──────────────────────────────────────────────────────────
# Fix 4 — Notification button '#' → Google search
# ──────────────────────────────────────────────────────────
def fix_notification_btn(html: str, title: str) -> str:
    # Match the secondary button with href="#"
    pattern = (
        r'<a href="#"[^>]*class="btn btn--secondary btn--large"[^>]*>'
        r'\s*📄 Download Notification\s*</a>'
    )
    if not re.search(pattern, html):
        return html

    q = quote_plus(f'{title} official notification PDF')
    new_btn = (
        f'<a href="https://www.google.com/search?q={q}" target="_blank" rel="noopener" '
        f'class="btn btn--secondary btn--large">🔍 Search Notification on Google</a>'
    )
    return re.sub(pattern, new_btn, html, count=1)


# ──────────────────────────────────────────────────────────
# Fix 5 — Remove residual naukridhaba.in internal links
# ──────────────────────────────────────────────────────────
def fix_internal_links(html: str) -> str:
    # Any href pointing to our own domain that is NOT a real path we generate
    # (these come from sanitize_url previously replacing sarkariresult URLs)
    # Safe to drop only links that look like they came from sarkariresult path structure
    # Pattern: href="https://www.naukridhaba.in/latestjob..." or similar non-standard paths
    def replace_bad_href(m):
        href = m.group(1)
        # Keep our known page patterns
        if re.match(r'https://www\.naukridhaba\.in/(jobs|results|admit-cards|index|latest-jobs|resources|eligibility)', href):
            return m.group(0)
        # Drop anything else pointing to our domain (was a sarkariresult path)
        return 'href="#"'

    return re.sub(r'href="(https://www\.naukridhaba\.in[^"]*)"', replace_bad_href, html)


# ──────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────
def repair_file(path: Path, is_job: bool) -> bool:
    try:
        html = path.read_text(encoding='utf-8')
        original = html

        html = fix_telegram(html)
        html = fix_internal_links(html)

        if is_job:
            title = extract_title(html)
            if title:
                html, dept = fix_department(html, title)
                d = reconstruct_d(html)
                d['title'] = title  # ensure consistent
                html = fix_add_description(html, d, dept)
                html = fix_notification_btn(html, title)

        if html != original:
            path.write_text(html, encoding='utf-8')
            return True
        return False
    except Exception as e:
        print(f'  ERROR {path}: {e}')
        return False


def main():
    dirs = [
        (SITE_ROOT / 'jobs',        True),
        (SITE_ROOT / 'results',     False),
        (SITE_ROOT / 'admit-cards', False),
    ]

    total = fixed = 0
    for base, is_job in dirs:
        for path in sorted(base.rglob('*.html')):
            total += 1
            changed = repair_file(path, is_job)
            if changed:
                fixed += 1
                print(f'  ✅ Fixed: {path.relative_to(SITE_ROOT)}')
            else:
                print(f'     OK  : {path.relative_to(SITE_ROOT)}')

    print(f'\nDone. {fixed}/{total} files updated.')


if __name__ == '__main__':
    main()

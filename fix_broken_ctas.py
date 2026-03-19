#!/usr/bin/env python3
"""
Fix existing admit-card and result pages:
1. Replace disabled "Coming Soon" spans with Google search links.
2. Remove contradicting "Result Date: Check Notification" line from result pages.
3. Fix FAQ answer that says "declared on Check Notification".
"""
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent

ADMIT_SPAN = re.compile(
    r'<span class="btn btn--primary btn--large"[^>]*>\s*'
    r'(?:📥\s*)?Admit Card Link Coming Soon\s*</span>'
)
RESULT_SPAN = re.compile(
    r'<span class="btn btn--primary btn--large"[^>]*>\s*'
    r'(?:🎯\s*)?Result Link Coming Soon\s*</span>'
)
# "Result Date: Check Notification" paragraph
RESULT_DATE_UNKNOWN = re.compile(
    r'<p[^>]*>\s*Result Date:\s*Check Notification\s*</p>'
)
# FAQ answer saying "declared on Check Notification"
FAQ_DECLARED_UNKNOWN = re.compile(
    r'The ([^<]+) was declared on Check Notification\. Check using the official link on this page\.'
)
TITLE_RE = re.compile(r'<h1[^>]*>\s*(?:📊\s*)?([^<]+)</h1>', re.I)


def google_url(title: str, suffix: str) -> str:
    return f'https://www.google.com/search?q={quote(title.strip() + " " + suffix)}'


fixed = 0

for p in sorted(ROOT.glob('admit-cards/**/*.html')):
    html = p.read_text(encoding='utf-8')
    if not ADMIT_SPAN.search(html):
        continue
    m = TITLE_RE.search(html)
    title = m.group(1).strip() if m else p.stem.replace('-', ' ').title()
    url = google_url(title, 'admit card download')
    html = ADMIT_SPAN.sub(
        f'<a href="{url}" target="_blank" rel="nofollow noopener noreferrer" '
        f'class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;">'
        f'📥 Download Admit Card / हॉल टिकट डाउनलोड करें</a>',
        html
    )
    p.write_text(html, encoding='utf-8')
    print(f'  admit  {p.relative_to(ROOT)}')
    fixed += 1

for p in sorted(ROOT.glob('results/**/*.html')):
    html = p.read_text(encoding='utf-8')
    changed = False

    # Fix "Coming Soon" button
    if RESULT_SPAN.search(html):
        m = TITLE_RE.search(html)
        title = m.group(1).strip() if m else p.stem.replace('-', ' ').title()
        url = google_url(title, 'result')
        html = RESULT_SPAN.sub(
            f'<a href="{url}" target="_blank" rel="nofollow noopener noreferrer" '
            f'class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;">'
            f'🎯 Check Result / परिणाम देखें</a>',
            html
        )
        changed = True

    # Remove "Result Date: Check Notification" — contradicts the Declared badge
    if RESULT_DATE_UNKNOWN.search(html):
        html = RESULT_DATE_UNKNOWN.sub('', html)
        changed = True

    # Fix FAQ: "declared on Check Notification" → sensible answer
    if FAQ_DECLARED_UNKNOWN.search(html):
        html = FAQ_DECLARED_UNKNOWN.sub(
            r'The \1 has been declared. Visit the official link on this page to check your result.',
            html
        )
        changed = True

    if changed:
        p.write_text(html, encoding='utf-8')
        print(f'  result {p.relative_to(ROOT)}')
        fixed += 1

print(f'\nFixed {fixed} pages.')

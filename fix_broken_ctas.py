#!/usr/bin/env python3
"""
Fix existing admit-card and result pages:
Replace disabled "Coming Soon" spans with Google search links.
"""
import re
import sys
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
TITLE_RE = re.compile(r'<h1[^>]*>([^<]+)</h1>', re.I)

def google_url(title: str, suffix: str) -> str:
    return f'https://www.google.com/search?q={quote(title.strip() + " " + suffix)}'

def fix_file(path: Path, span_re: re.Pattern, suffix: str, btn_text: str) -> bool:
    html = path.read_text(encoding='utf-8')
    if not span_re.search(html):
        return False
    m = TITLE_RE.search(html)
    title = m.group(1).strip() if m else path.stem.replace('-', ' ').title()
    url = google_url(title, suffix)
    replacement = (
        f'<a href="{url}" target="_blank" rel="nofollow noopener noreferrer" '
        f'class="btn btn--primary btn--large" style="display:inline-block;margin-bottom:1rem;">'
        f'{btn_text}</a>'
    )
    new_html = span_re.sub(replacement, html)
    path.write_text(new_html, encoding='utf-8')
    return True

fixed = 0
for p in sorted(ROOT.glob('admit-cards/**/*.html')):
    if fix_file(p, ADMIT_SPAN, 'admit card download', '📥 Download Admit Card / हॉल टिकट डाउनलोड करें'):
        print(f'  admit  {p.relative_to(ROOT)}')
        fixed += 1

for p in sorted(ROOT.glob('results/**/*.html')):
    if fix_file(p, RESULT_SPAN, 'result', '🎯 Check Result / परिणाम देखें'):
        print(f'  result {p.relative_to(ROOT)}')
        fixed += 1

print(f'\nFixed {fixed} pages.')

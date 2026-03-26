#!/usr/bin/env python3
"""Generate /state/XX.html pages by scanning existing job/result/admit detail pages."""

from __future__ import annotations
import re
import json
from pathlib import Path

ROOT = Path(__file__).parent
SITE_URL = "https://naukridhaba.in"

STATES = {
    "uttar-pradesh": {
        "name": "Uttar Pradesh",
        "hi": "उत्तर प्रदेश",
        "keywords": ["uttar pradesh", "up ", " up ", "upsc", "uppsc", "upsessb", "upbed",
                     "upsssc", "uptet", "upmsp", "up police", "up board", "up metro",
                     "up forest", "up psc", "lekhpal", "jeecup", "upbeb", "up rte",
                     "anganwadi"],
    },
    "bihar": {
        "name": "Bihar",
        "hi": "बिहार",
        "keywords": ["bihar", "bpsc", "bssc", "bpssc", "btsc", "bcece", "bihar police",
                     "bihar board", "bihar stet", "bihar tet"],
    },
    "rajasthan": {
        "name": "Rajasthan",
        "hi": "राजस्थान",
        "keywords": ["rajasthan", "rssb", "rpsc", "reet", "raj police", "rajasthan police",
                     "rajasthan board", "rajasthan psc", "rsmsb"],
    },
    "madhya-pradesh": {
        "name": "Madhya Pradesh",
        "hi": "मध्य प्रदेश",
        "keywords": ["madhya pradesh", "mppsc", "mp board", "mp police", "mpesb",
                     "vyapam", "mp vyapam", "mptransco", "mptet", "mp psc"],
    },
    "delhi": {
        "name": "Delhi",
        "hi": "दिल्ली",
        "keywords": ["delhi", "dsssb", "dmrc", "delhi police", "dda ", "delhi metro",
                     "delhi board", "gnct", "delhi mcd"],
    },
    "maharashtra": {
        "name": "Maharashtra",
        "hi": "महाराष्ट्र",
        "keywords": ["maharashtra", "mpsc", "mahapariksha", "maha police",
                     "maharashtra police", "mseb", "maharashtra board"],
    },
    "haryana": {
        "name": "Haryana",
        "hi": "हरियाणा",
        "keywords": ["haryana", "hssc", "hpsc", "htet", "haryana police",
                     "haryana board", "haryana psc"],
    },
    "jharkhand": {
        "name": "Jharkhand",
        "hi": "झारखंड",
        "keywords": ["jharkhand", "jpsc", "jssc", "jharkhand police",
                     "jharkhand board", "jac "],
    },
    "gujarat": {
        "name": "Gujarat",
        "hi": "गुजरात",
        "keywords": ["gujarat", "gpsc", "gsssb", "gujarat police",
                     "gujarat board", "gsrtc", "gmdc"],
    },
    "punjab": {
        "name": "Punjab",
        "hi": "पंजाब",
        "keywords": ["punjab", "ppsc", "psssb", "punjab police",
                     "punjab board", "pseb ", "puda"],
    },
}

# Load tracking config from an existing page
def load_tracking_block() -> str:
    sample = ROOT / "latest-jobs.html"
    content = sample.read_text(encoding="utf-8", errors="replace")
    # Extract everything from <script>window.NAUKRI_DHABA... to closing </script>
    m = re.search(
        r'(<script>window\.NAUKRI_DHABA_TRACKING_CONFIG.*?</script>.*?)'
        r'(?=\s*<script src="/js/tracking\.js"|\s*</head>)',
        content, re.DOTALL
    )
    if m:
        return m.group(1)
    # Fallback: just the config line
    m2 = re.search(r'<script>window\.NAUKRI_DHABA_TRACKING_CONFIG[^\n]+</script>', content)
    return m2.group(0) if m2 else ""

def load_head_scripts() -> str:
    """Extract GTM, consent scripts from latest-jobs.html head."""
    sample = ROOT / "latest-jobs.html"
    content = sample.read_text(encoding="utf-8", errors="replace")
    # Get everything between <link rel="stylesheet"...> and </head>
    m = re.search(r'(<link rel="stylesheet".*?</head>)', content, re.DOTALL)
    return m.group(1) if m else '<link rel="stylesheet" href="/css/style.css">\n</head>'

def load_gtm_noscript() -> str:
    sample = ROOT / "latest-jobs.html"
    content = sample.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'(<!-- Google Tag Manager \(noscript\).*?<!-- End Google Tag Manager \(noscript\) -->)', content, re.DOTALL)
    return m.group(1) if m else ""

def load_footer() -> str:
    sample = ROOT / "latest-jobs.html"
    content = sample.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'(<footer class="footer">.*?</footer>)', content, re.DOTALL)
    return m.group(1) if m else ""

def load_consent_banner() -> str:
    sample = ROOT / "latest-jobs.html"
    content = sample.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'(<!-- Consent Banner.*?<!-- End Consent Banner -->)', content, re.DOTALL)
    return m.group(1) if m else ""


def extract_entries(kind: str) -> list[dict]:
    """Extract title, dept, date, url from all detail pages of given kind."""
    entries = []
    subdir = {"job": "jobs", "result": "results", "admit": "admit-cards"}[kind]
    for p in sorted((ROOT / subdir).rglob("*.html")):
        content = p.read_text(encoding="utf-8", errors="replace")
        rel = "/" + p.relative_to(ROOT).as_posix()

        # title from <h1>
        t = re.search(r'<h1[^>]*>([^<]+)</h1>', content)
        title = t.group(1).strip() if t else p.stem.replace("-", " ").title()

        # dept from badge
        d = re.search(r'<span class="badge"[^>]*>([^<]+)</span>', content)
        dept = d.group(1).strip() if d else "GOVT"

        # date
        dt = re.search(r'<p[^>]*>\s*(?:Last Date|Date)[^:]*:\s*([^<]+)</p>', content, re.IGNORECASE)
        if not dt:
            dt = re.search(r'"datePublished"\s*:\s*"([^"]+)"', content)
        date_str = dt.group(1).strip() if dt else ""

            # Only include entries whose file actually exists on disk
        if not p.exists():
            continue
        entries.append({"title": title, "dept": dept, "date": date_str,
                        "url": rel, "kind": kind})
    return entries


def matches_state(entry: dict, keywords: list[str]) -> bool:
    text = (entry["title"] + " " + entry["dept"]).lower()
    return any(kw in text for kw in keywords)


def build_table_rows(entries: list[dict], action_label: str) -> str:
    rows = []
    for e in entries:
        rows.append(
            f'<tr><td>{e["dept"]}</td>'
            f'<td><a href="{e["url"]}" style="color:var(--primary);font-weight:600;">{e["title"]}</a></td>'
            f'<td>{e["date"] or "—"}</td>'
            f'<td><a href="{e["url"]}" class="btn btn--small btn--primary">{action_label}</a></td></tr>'
        )
    return "\n".join(rows)


def build_cards(entries: list[dict], action_label: str) -> str:
    cards = []
    for e in entries:
        cards.append(
            f'<div class="card"><div class="card__header"><span class="badge">{e["dept"]}</span></div>'
            f'<h3 class="card__title">{e["title"]}</h3>'
            f'<p style="color:#666;font-size:.875rem;">{e["date"] or "—"}</p>'
            f'<a href="{e["url"]}" class="btn btn--primary btn--block" style="margin-top:1rem;">{action_label}</a></div>'
        )
    return "\n".join(cards)


def generate_state_page(slug: str, info: dict,
                        jobs: list[dict], results: list[dict], admits: list[dict],
                        head_scripts: str, gtm_noscript: str,
                        footer_html: str, consent_html: str) -> str:
    name = info["name"]
    hi = info["hi"]
    total = len(jobs) + len(results) + len(admits)
    canonical = f"{SITE_URL}/state/{slug}"

    jobs_rows = build_table_rows(jobs, "Apply")
    results_rows = build_table_rows(results, "Check")
    admits_rows = build_table_rows(admits, "Download")
    jobs_cards = build_cards(jobs, "Apply")
    results_cards = build_cards(results, "Check")
    admits_cards = build_cards(admits, "Download")

    def section(title_en: str, rows: str, cards: str, table_id: str, kind: str) -> str:
        if not rows:
            return ""
        return f"""
<h2 style="color:var(--primary);margin-top:2rem;">{title_en}</h2>
<div class="table-wrapper">
<table class="table" id="{table_id}">
<thead><tr><th>Department</th><th>Name</th><th>Date</th><th>Action</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</div>
<div class="cards">{cards}</div>"""

    jobs_section    = section(f"{name} Govt Jobs 2026", jobs_rows, jobs_cards, f"jobs-{slug}", "job")
    results_section = section(f"{name} Results 2026",   results_rows, results_cards, f"results-{slug}", "result")
    admits_section  = section(f"{name} Admit Cards 2026", admits_rows, admits_cards, f"admits-{slug}", "admit")

    empty_msg = "" if total else f'<p style="text-align:center;padding:2rem;color:#666;">No entries found for {name} yet. Check back soon!</p>'

    return f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} Govt Jobs, Results & Admit Cards 2026 | Naukri Dhaba</title>
    <meta name="description" content="Latest government jobs, exam results, and admit cards for {name} ({hi}) 2026. Sarkari naukri updates for {name} on Naukri Dhaba.">
    <meta name="keywords" content="{name} Govt Jobs 2026, {name} Sarkari Result, {name} Admit Card, {hi} Naukri, Naukri Dhaba">
    <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
    <meta name="author" content="Naukri Dhaba">
    <link rel="canonical" href="{canonical}">
    <link rel="preconnect" href="https://www.googletagmanager.com">
    <link rel="preconnect" href="https://www.google-analytics.com">
    <link rel="dns-prefetch" href="https://www.googletagmanager.com">
    <link rel="dns-prefetch" href="https://www.google-analytics.com">
    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:title" content="{name} Govt Jobs, Results & Admit Cards 2026 | Naukri Dhaba">
    <meta property="og:description" content="Latest government jobs, exam results, and admit cards for {name} 2026 on Naukri Dhaba.">
    <meta property="og:url" content="{canonical}">
    <meta property="og:site_name" content="Naukri Dhaba">
    <meta property="og:locale" content="en_IN">
    <meta property="og:image" content="https://naukridhaba.in/img/og-default.png">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:image" content="https://naukridhaba.in/img/og-default.png">
    <meta name="twitter:title" content="{name} Govt Jobs, Results & Admit Cards 2026 | Naukri Dhaba">
    <meta name="twitter:description" content="Latest government jobs, exam results, and admit cards for {name} 2026 on Naukri Dhaba.">
    <!-- India Geo -->
    <meta name="geo.region" content="IN">
    <meta name="geo.placename" content="{name}">
    {head_scripts}
<body>
    {gtm_noscript}
<header class="header">
<div class="container header__container">
<a class="logo" href="/">&#x1F4CB; Naukri Dhaba</a>
<nav class="nav nav--desktop">
<a class="" href="/latest-jobs.html">&#x1F4BC; Latest Jobs</a>
<a class="" href="/results.html">&#x1F4CA; Results</a>
<a class="" href="/admit-cards.html">&#x1F3AB; Admit Cards</a>
<a class="" href="/resources.html">&#x1F4DA; Resources</a>
</nav>
<div style="display:flex;gap:1rem;align-items:center;">
<button class="btn--icon" onclick="toggleDarkMode()" title="Toggle Dark Mode">&#x1F313;</button>
<button class="btn--icon menu-toggle" onclick="toggleMobileMenu()" style="display:none;font-size:1.5rem;cursor:pointer;" aria-label="Open menu">&#x2630;</button>
</div>
</div>
<nav class="nav--mobile"><button onclick="closeMobileMenu()" style="position:absolute;top:1rem;right:1rem;background:none;border:none;font-size:1.5rem;cursor:pointer;">&#x2715;</button><a href="/">&#x1F3E0; Home</a><a href="/latest-jobs.html">&#x1F4BC; Latest Jobs</a><a href="/results.html">&#x1F4CA; Results</a><a href="/admit-cards.html">&#x1F3AB; Admit Cards</a><a href="/resources.html">&#x1F4DA; Resources</a></nav>
<style>.menu-toggle{{display:none!important}}@media(max-width:768px){{.nav--desktop{{display:none}}.menu-toggle{{display:block!important}}}}</style>
<div id="menu-overlay" onclick="closeMobileMenu()" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:1000;"></div>
</header>

<div class="container" style="margin-top:2rem;">
<nav aria-label="breadcrumb" style="font-size:0.875rem;margin-bottom:1rem;">
  <a href="/">Home</a> &rsaquo; <span>{name}</span>
</nav>
<h1 style="color:var(--primary);">{name} ({hi}) — Sarkari Jobs & Results 2026</h1>
<p style="color:#666;margin:.5rem 0 1.5rem;">All government job updates, exam results, and admit card notifications for {name}. Total: <strong>{total}</strong> entries.</p>
{empty_msg}
{jobs_section}
{results_section}
{admits_section}
<div class="ad-slot" style="margin-top:2rem;">Advertisement</div>
</div>

{consent_html}
{footer_html}
<script src="/js/app.js"></script>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  "name": "{name} Govt Jobs, Results & Admit Cards 2026",
  "description": "Latest government jobs, exam results, and admit cards for {name} 2026.",
  "url": "{canonical}",
  "publisher": {{
    "@type": "Organization",
    "name": "Naukri Dhaba",
    "url": "https://naukridhaba.in"
  }}
}}
</script>
</body>
</html>"""


def main():
    print("Loading existing detail pages...")
    all_jobs    = extract_entries("job")
    all_results = extract_entries("result")
    all_admits  = extract_entries("admit")
    print(f"  Jobs: {len(all_jobs)}, Results: {len(all_results)}, Admits: {len(all_admits)}")

    head_scripts  = load_head_scripts()
    gtm_noscript  = load_gtm_noscript()
    footer_html   = load_footer()
    consent_html  = load_consent_banner()

    state_dir = ROOT / "state"
    state_dir.mkdir(exist_ok=True)

    total_pages = 0
    for slug, info in STATES.items():
        kw = info["keywords"]
        jobs    = [e for e in all_jobs    if matches_state(e, kw)]
        results = [e for e in all_results if matches_state(e, kw)]
        admits  = [e for e in all_admits  if matches_state(e, kw)]

        html = generate_state_page(slug, info, jobs, results, admits,
                                   head_scripts, gtm_noscript, footer_html, consent_html)
        out = state_dir / f"{slug}.html"
        out.write_text(html, encoding="utf-8")
        total = len(jobs) + len(results) + len(admits)
        print(f"  {info['name']:20s}  jobs={len(jobs):3d}  results={len(results):3d}  admits={len(admits):3d}  → {out.relative_to(ROOT)}")
        total_pages += 1

    print(f"\nGenerated {total_pages} state pages in state/")


if __name__ == "__main__":
    main()

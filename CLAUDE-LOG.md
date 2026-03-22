# CLAUDE-LOG — Naukri Dhaba Operations Log

> **This file is updated every time Claude pushes changes.**
> Last updated: 2026-03-20

---

## Project Overview

| Field | Value |
|-------|-------|
| **Repo** | `ashoksingh-ayodhya/naukri-dhaba` |
| **Domain** | `naukridhaba.in` |
| **Platform** | GitHub Pages (static HTML) |
| **Primary Source** | sarkariresult.com |
| **Scraper Schedule** | Every 5 min via GitHub Actions (`*/5 * * * *`) |
| **GA4** | `G-E3C5CLPP6B` |
| **GTM** | `GTM-5L4D9C9M` |

---

## Architecture

### Content Pipeline
```
sarkariresult.com → CF Worker Proxy → sarkari_scraper.py → HTML pages → GitHub Pages
```

### File Structure (250 files on main)
```
/                          Root (44 files: HTML pages, Python scripts, configs)
├── jobs/                  38 job detail pages (upsc/, ssc/, railway/, police/, government/, defence/)
├── results/               76 result pages
├── admit-cards/           79 admit card pages
├── state/                 10 state pages (UP, Bihar, Rajasthan, MP, Delhi, Maharashtra, Haryana, Jharkhand, Gujarat, Punjab)
├── feed/                  3 RSS feeds (jobs.xml, results.xml, admit-cards.xml)
├── api/                   1 JSON API (latest.json)
├── scraper/               6 files (sarkari_scraper.py, job_poster.py, check_sources.py, cf-proxy-worker.js, requirements.txt, seen_items.json)
├── css/                   1 file (style.css)
├── js/                    3 files (app.js, tracking.js, ads-manager.js)
├── img/                   1 file (og-default.png)
└── .github/workflows/     1 file (daily-scraper.yml)
```

### Key Scripts
| Script | Lines | Purpose |
|--------|-------|---------|
| `scraper/sarkari_scraper.py` | ~2,950 | Main scraper: fetch listings → parse details → generate HTML pages → rebuild listings |
| `update-all-pages.py` | ~1,560 | Mass updater: tracking codes, OG tags, SEO, JSON-LD, sanitize source URLs |
| `generate-state-pages.py` | ~330 | Generates /state/XX.html pages by scanning detail pages |
| `generate-sitemap.py` | ~160 | Scans all HTML → generates sitemap.xml |
| `validate-generated-site.py` | ~205 | Pre-publish validator: checks meta tags, canonical, JSON-LD, source URL leaks |
| `scraper/job_poster.py` | ~165 | Daemon/cron wrapper: runs scraper every 5 min |
| `scraper/check_sources.py` | ~110 | Pre-flight: checks if source sites are reachable |
| `scraper/cf-proxy-worker.js` | ~130 | Cloudflare Worker proxy to bypass IP blocks |
| `site_config.py` | ~42 | Shared config: SOURCES, SITE_URL, REDIRECT_PATH, PRETTY_ROUTE_MAP |
| `fix_broken_ctas.py` | exists | CTA button fixer |

### Static Pages
| Page | Purpose |
|------|---------|
| `index.html` | Homepage with latest 10 jobs, hero search, ticker |
| `latest-jobs.html` | All jobs listing with search/filter |
| `results.html` | All results listing |
| `admit-cards.html` | All admit cards listing |
| `resources.html` | Study resources, official portals |
| `previous-papers.html` | Previous year papers (manual + auto-scraped) |
| `study-planner.html` | Interactive study planner tool |
| `eligibility-calculator.html` | Age/eligibility checker |
| `syllabus.html` | Exam syllabus reference |
| `cut-off-marks.html` | Cut-off marks reference |
| `go.html` | Redirect handler for external links |
| `404.html` | Custom 404 page |
| `widget.html` + `widget.js` | Embeddable widget |
| `share-diff-preview.html` | Mobile UI diff preview |

### Scraping Flow (sarkari_scraper.py)
1. **Pre-flight** (`check_sources.py`): Verify at least one source is reachable
2. **Fetch listings**: GET /latestjob.php, /result.php, /admitcard.php via CF Worker → direct fallback
3. **Parse listings**: Extract title, dept, date, detail_url from table rows (2-col or 3-col)
4. **Filter**: `kind_matches_title()` — jobs must NOT match result/admit patterns
5. **Skip**: Items older than 2025, already-seen items (unless `--refresh-existing`)
6. **Fetch details**: GET each detail page → extract dates, fees, age, qualification, CTA links
7. **Build HTML**: `build_job_page()` / `build_result_page()` / `build_admit_page()` with SEO, FAQ, JSON-LD
8. **Rebuild listings**: Replace listing sections on latest-jobs.html, results.html, admit-cards.html, index.html
9. **Save seen set** → `seen_items.json`
10. **Regenerate sitemap**

### URL Safety Rules
- Source URLs (sarkariresult.com) → NEVER shown to users, rewritten to naukridhaba.in
- Official govt URLs (.gov.in, .nic.in) → Shown directly
- Unknown URLs → `google_search_url()` fallback
- CTA buttons: Only official portal URLs or Google search fallback, never source site

### Tracking Stack
- GA4 + GTM injected via `detail_head_tracking_markup()` in scraper and `update-all-pages.py`
- Consent mode: default reject, banner on first visit, 3 modes (reject/analytics/all)
- `tracking.js`: Loads AdSense, Facebook Pixel, Clarity (all currently disabled)
- `ads-manager.js`: Hides all ad slots until configured

---

## Configuration

### site_config.py (current state — only sarkariresult.com)
```python
SOURCES = [
    {
        "name": "sarkariresult",
        "base": "https://www.sarkariresult.com",
        "urls": {
            "job":    "https://www.sarkariresult.com/latestjob.php",
            "result": "https://www.sarkariresult.com/result.php",
            "admit":  "https://www.sarkariresult.com/admitcard.php",
        },
    },
]
```

### GitHub Actions Secrets Required
- `CF_WORKER_PROXY_URL` — Cloudflare Worker URL for proxied scraping
- `CF_WORKER_SECRET` — Optional auth token for CF Worker

### .gitignore
```
__pycache__/
scraper/__pycache__/
scraper/logs/
output/playwright/
.playwright-cli/
```

---

## Known Issues & Notes

1. **`api/latest.json` admit URLs** use `/admits/` path instead of `/admit-cards/` — mismatch with actual file paths
2. **`seen_items.json`** is always empty because `--refresh-existing` flag resets it each run
3. **Scraper logs** are ephemeral — only exist during GitHub Actions runs, never committed (gitignored)
4. **Last workflow step** (`tail -50 scraper/logs/scraper.log`) shows logs in Actions console
5. **`RESTORE.md`** has rollback instructions for UI redesign (pre-snapshot: `73f5053`)
6. **Consent mode** defaults to "reject" — GA4 only fires after user accepts
7. **AdSense, Facebook Pixel, Clarity** all disabled (placeholder IDs)

---

## Push Log

### 2026-03-20 — Session: claude/add-chat-import-MHO3i

| Time (UTC) | Commit | Description |
|------------|--------|-------------|
| — | `c3d13dc` | `chore: drop secondary sources, keep only sarkariresult.com` — Removed freejobalert, rojgarresult, sarkariexam from site_config.py SOURCES (previously applied & pushed by earlier session, then reverted; now re-applied on this branch) |
| — | (this commit) | `chore: add CLAUDE-LOG.md — onboarding context + push log for all future sessions` |

---

*End of log. Next Claude session: read this file first, then append to the Push Log table above after every push.*

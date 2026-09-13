# Naukri Dhaba

**Clean, ad-free government job updates** — [naukridhaba.in](https://naukridhaba.in)

Job notifications, exam results, admit cards, answer keys and syllabi for SSC, Railway, Banking, UPSC, Police, Defence, State PSCs and other government recruiters. No ads, no sign-up — just the facts from official notifications, presented clearly.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 15 (App Router, `output: "export"`) |
| Styling | Tailwind CSS |
| Content | MDX files with YAML frontmatter under `content/` |
| Hosting | GitHub Pages (serves the repository root of `main`) |
| Scraper | Python 3.11, run twice daily by GitHub Actions |
| Proxy | Optional Cloudflare Worker (`scraper/cf-worker.js`) for source sites that block CI IPs |
| Analytics | GA4 via Google Tag Manager (consent-gated). **No advertising.** |

---

## How content flows

```
GitHub Actions  ─ "Scrape content" (07:00 & 19:00 IST)
  scraper/sarkari_scraper.py
    listings → classify title → skip known posts → detail page → parse → normalise
    → content/{jobs,results,admit-cards,answer-keys,syllabus}/…/slug.mdx
    → scraper/validate_content.py (every file must pass)
    → commit to main
        │
        ▼
GitHub Actions  ─ "Build and deploy" (after a scrape, or on source changes)
  validate content → tsc → next build → scripts/publish-out.sh → commit out/ to main root
        │
        ▼
GitHub Pages → naukridhaba.in
```

### Content model

```
content/
  jobs/<category>/<slug>.mdx
  results/<category>/<slug>.mdx
  admit-cards/<category>/<slug>.mdx
  answer-keys/<slug>.mdx
  syllabus/<slug>.mdx
```

Frontmatter mirrors `lib/types.ts` (`PostFrontmatter`). All copy on a page (`shortDescription`, body, FAQ) is generated **only from scraped fields** by `scraper/content_writer.py` — nothing is invented, no dates or years are guessed.

---

## Scraper

| File | Purpose |
|------|---------|
| `sarkari_scraper.py` | Orchestrator: discovery, time budget, seen-tracking, refresh of open jobs |
| `site_config.py` | Source sites and their listing URLs |
| `listing.py` | Listing-page row extraction |
| `classify.py` | Title → job / result / admit / answer-key / syllabus |
| `detail_parser/` | Per-source detail-page parsers |
| `mdx_generator.py` | `normalize_frontmatter()` — the single place scraped values are cleaned — and MDX writing |
| `content_writer.py` | Fact-only description / body / FAQ |
| `urls.py`, `portals.py`, `taxonomy.py`, `textutil.py` | URL policy, official portals, categories, date/text helpers |
| `validate_content.py` | Content validator (CI gate, also run after every write) |
| `repair_content.py` | Idempotent repair of existing files (re-normalise, reclassify, remove junk) |
| `tests/` | Regression tests incl. an end-to-end run against a local HTTP server |

Rules enforced by the validator: no aggregator branding anywhere, no links to aggregator or social hosts, ISO `publishedAt`, `DD/MM/YYYY` deadlines, type matches directory, slug matches filename, no "Click Here" qualifications.

### Running locally

```bash
pip install -r scraper/requirements.txt
python -m unittest discover -s scraper/tests
python scraper/sarkari_scraper.py --dry-run        # fetch + parse, write nothing
python scraper/sarkari_scraper.py                  # daily run
python scraper/sarkari_scraper.py --sitemap        # add historical backfill
python scraper/validate_content.py
```

Optional environment: `CF_WORKER_PROXY_URL`, `CF_WORKER_SECRET` (GitHub Secrets; see `scraper/cf-worker.js`), `GOOGLE_INDEXING_SA_KEY` for the Indexing API.

---

## Site

```bash
npm ci
npm run dev
npx tsc --noEmit
npm run build      # static export → out/
```

`images: { unoptimized: true }` and `output: "export"` in `next.config.ts` are required for static hosting.

Structured data per page type: `JobPosting` (jobs, full HTML description, `validThrough` from the deadline), `NewsArticle` (results, admit cards), `LearningResource` (answer keys, syllabi), `BreadcrumbList` everywhere, `CollectionPage`/`ItemList` on category pages, `WebSite` + `Organization` on the home page.

---

## Workflows

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `scrape.yml` | 07:00 & 19:00 IST, manual | tests → scrape (45-min budget) → validate → commit content |
| `deploy.yml` | after a scrape, source/content push, PR, manual | validate → type-check → build → publish `out/` to repo root |

The scraper never marks a post as seen until it has been written and validated, so a timeout or crash never loses posts.

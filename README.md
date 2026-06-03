# Naukri Dhaba

**India's Trusted Sarkari Naukri Portal** — [naukridhaba.in](https://naukridhaba.in)

Government job notifications, exam results, admit cards, answer keys and syllabi for SSC, Railway, Banking, UPSC, Police, Defence and all state government jobs.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 15 (App Router, static export) |
| Styling | Tailwind CSS |
| Content | MDX files + YAML frontmatter |
| Hosting | Cloudflare Pages (free tier) |
| Scraper | Python 3.11 (GitHub Actions) |
| Proxy | Cloudflare Worker (`nd-proxy`) |
| Analytics | Google Tag Manager + GA4 |
| Ads | Google AdSense |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  GitHub Actions (4× daily)                              │
│  scraper/sarkari_scraper.py                             │
│       │                                                  │
│       ▼                                                  │
│  CF Worker Proxy ──► Source Sites                       │
│  (nd-proxy.workers.dev)   (sarkariresult, freejobalert, │
│                            rojgarresult, sarkariexam)   │
│       │                                                  │
│       ▼                                                  │
│  MDX files → content/{jobs,results,admit-cards}/        │
│       │                                                  │
│       ▼                                                  │
│  git commit + push → main                               │
│       │                                                  │
│       ▼                                                  │
│  Cloudflare Pages (auto-deploy on push)                 │
│  Next.js static build → HTML/CSS/JS                     │
│       │                                                  │
│       ▼                                                  │
│  naukridhaba.in (Cloudflare CDN)                        │
└─────────────────────────────────────────────────────────┘
```

### Content Model

Every post is a `.mdx` file under `content/`:

```
content/
  jobs/
    ssc/          ← category slug
      ssc-cgl-2026.mdx
    railway/
    banking/
    ...
  results/
    ssc/
    railway/
    ...
  admit-cards/
    ssc/
    ...
  answer-keys/
  syllabus/
```

Each MDX file has YAML frontmatter with fields like `title`, `slug`, `organization`, `lastDate`, `totalPosts`, `qualification`, `salary`, `applyUrl`, etc. The body contains structured sections rendered by dedicated React components.

---

## Local Development

```bash
# Install dependencies
npm install

# Run dev server
npm run dev

# Build static export
npm run build

# Type check
npx tsc --noEmit
```

> **Note:** `images: { unoptimized: true }` in `next.config.ts` is intentional — required for static export on Cloudflare Pages. Do not change it.

---

## Scraper

The Python scraper lives in `scraper/` and runs automatically via GitHub Actions 4× daily (7 AM, 1 PM, 7 PM, 1 AM IST).

### How it works

1. Fetches listing pages from 4 sources via CF Worker proxy
2. For each new item, fetches the detail page and parses structured data
3. Generates an MDX file via `mdx_generator.py`
4. Tracks seen items in `scraper/seen_items.json` (MD5 hashes)
5. Commits new MDX files and pushes to main
6. Self-triggers another run via `repository_dispatch` until content goals are met (3000 jobs / 2000 results / 1500 admit cards)

### Running locally

```bash
cd scraper
pip install -r requirements.txt
python sarkari_scraper.py
```

Requires `CF_WORKER_PROXY_URL` and `CF_WORKER_SECRET` environment variables (stored as GitHub Secrets — do not commit).

### Key files

| File | Purpose |
|------|---------|
| `sarkari_scraper.py` | Main entry point — orchestrates all sources |
| `mdx_generator.py` | Converts structured data to MDX |
| `seen_items.json` | Deduplication store (MD5 hashes) |
| `detail_parser/` | Per-source HTML parsers |
| `cf-worker.js` | Cloudflare Worker proxy source code |
| `notify_indexing_api.py` | Google Indexing API notifier |
| `site_config.py` | Category mappings used by scraper |

---

## GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `daily-scraper.yml` | Cron 4×/day + `repository_dispatch: scrape` | Run scraper, commit content, ping sitemaps |
| `daily-agent.yml` | Cron every 3h | SEO rewriter, branding fixes, freshness alerts |
| `wakeup-resume.yml` | Cron every 6h | Check content progress, update RESUME.md |
| `health-check.yml` | After scraper completes | Verify site is live and returning 200 |
| `post-scrape-update.yml` | `repository_dispatch: deploy` | Trigger Cloudflare Pages rebuild |

---

## Project Structure

```
naukri-dhaba/
├── app/                    # Next.js App Router pages
│   ├── page.tsx            # Homepage
│   ├── latest-jobs/        # All jobs listing
│   ├── jobs/
│   │   ├── [category]/     # Category listing + detail pages
│   │   └── qualification/  # Qualification-based pages (10th, graduate, etc.)
│   ├── results/            # Exam results
│   ├── admit-cards/        # Hall tickets
│   ├── answer-keys/        # Answer keys
│   ├── syllabus/           # Exam syllabi
│   ├── state/[state]/      # State-wise job pages
│   ├── search/             # Search page (server + client split)
│   ├── feed.xml/           # RSS feed
│   └── sitemap.ts          # Dynamic XML sitemap
├── components/
│   ├── detail/             # Job detail page sections
│   ├── home/               # Homepage widgets
│   ├── layout/             # Header, Footer, BottomNav
│   ├── listings/           # JobsTable, PaginatedJobsTable, JobRow, MobileJobCard
│   └── ui/                 # Badge, Breadcrumb, ShareButtons, etc.
├── config/
│   └── site.ts             # Site config, categories, states
├── content/                # MDX content files (generated by scraper)
├── lib/
│   ├── content.ts          # MDX reader, sorting, filtering
│   ├── seo.ts              # Schema.org JSON-LD builders
│   ├── types.ts            # TypeScript types
│   └── category-descriptions.ts  # SEO descriptions per category
├── scraper/                # Python scraper
├── agent/                  # SEO rewriter agent
├── public/                 # Static assets
├── FOUNDATION.md           # Architecture decisions and rules
├── RISK-ASSESSMENT.md      # Risk matrix with priorities
├── SEO-COMPETITOR-AUDIT.md # Competitor analysis and SEO backlog
└── RESUME.md               # Auto-generated: current state for next session
```

---

## Key Decisions & Rules

- **Static export only** — no server-side rendering. Everything is pre-built at deploy time. Client components use `"use client"` for interactivity.
- **`output: "export"` + `images: { unoptimized: true }`** — do not change, required for Cloudflare Pages.
- **MDX is the CMS** — no database, no CMS platform. Content is files. This works until ~7000 posts (Cloudflare's 20K file limit).
- **Sorting** — active jobs (deadline ≥ today) first, soonest deadline first. Expired jobs last, newest published first.
- **Date format** — scraper writes both `DD/MM/YYYY` and `DD-MM-YYYY`. Both are handled by `parseDDMMYYYY()` in `lib/content.ts`.
- **No secrets in repo** — `CF_WORKER_PROXY_URL`, `CF_WORKER_SECRET`, `GOOGLE_INDEXING_SA_KEY` are GitHub Secrets only.

See `FOUNDATION.md` for the full architecture reference.

---

## Content Categories

| Slug | Label | Full Name |
|------|-------|-----------|
| `ssc` | SSC | Staff Selection Commission |
| `railway` | Railway | Railway Recruitment Boards |
| `banking` | Banking | Banking & Insurance |
| `upsc` | UPSC | Union Public Service Commission |
| `police` | Police | Police & Paramilitary |
| `defence` | Defence | Army, Navy & Air Force |
| `teaching` | Teaching | Teaching & Education |
| `psu` | PSU | Public Sector Undertakings |
| `state-psc` | State PSC | State Public Service Commissions |
| `postal` | Postal | India Post & Postal Services |
| `medical` | Medical | Medical & Health Dept |
| `government` | Govt | Other Government Jobs |

---

## Deployment

Cloudflare Pages deploys automatically on every push to `main`. No manual steps required.

Build command: `npm run build`  
Output directory: `out`  
Node version: 20

**Build limits (free tier):** 500 builds/month. Scraper commits use `[skip ci]` to avoid triggering unnecessary builds.

---

## Links

- Site: [naukridhaba.in](https://naukridhaba.in)
- Twitter: [@naukridhaba](https://twitter.com/naukridhaba)
- Telegram: [t.me/naukridhaba](https://t.me/naukridhaba)
- WhatsApp: [whatsapp.com/channel/naukridhaba](https://whatsapp.com/channel/naukridhaba)

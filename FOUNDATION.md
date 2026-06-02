# NAUKRI DHABA — COMPLETE FOUNDATION DOCUMENT

**Last updated:** 2026-06-02  
**Purpose:** Single source of truth for architecture, SEO rules, content standards, scraper operations, and all decisions made for this website. Every component, every rule, every reason — documented here.

---

## TABLE OF CONTENTS

1. [Site Purpose & Business Goal](#1-site-purpose--business-goal)
2. [What Has Gone Wrong — Bug History](#2-what-has-gone-wrong--bug-history)
3. [Architecture Overview](#3-architecture-overview)
4. [Content Structure & URL Rules](#4-content-structure--url-rules)
5. [Categories & Departments — All Valid Values](#5-categories--departments--all-valid-values)
6. [Sorting System](#6-sorting-system)
7. [SEO Foundation — Complete Rules](#7-seo-foundation--complete-rules)
8. [H1 / H2 / H3 Usage Rules](#8-h1--h2--h3-usage-rules)
9. [Content Size Rules (Min/Max)](#9-content-size-rules-minmax)
10. [Metadata Rules](#10-metadata-rules)
11. [Structured Data (JSON-LD) Rules](#11-structured-data-json-ld-rules)
12. [Internal Linking Strategy](#12-internal-linking-strategy)
13. [Scraper System — Architecture & Rules](#13-scraper-system--architecture--rules)
14. [Scraper Alternatives (Non-GitHub-Actions)](#14-scraper-alternatives-non-github-actions)
15. [Content Rewriter Rules](#15-content-rewriter-rules)
16. [CMS System Design](#16-cms-system-design)
17. [AdSense Optimization Rules](#17-adsense-optimization-rules)
18. [Component Documentation](#18-component-documentation)
19. [SEO Checklist — Complete](#19-seo-checklist--complete)
20. [Immediate Action Items](#20-immediate-action-items)

---

## 1. SITE PURPOSE & BUSINESS GOAL

**Domain:** naukridhaba.in  
**Goal:** Maximum Google organic traffic → AdSense revenue.

**What we are:** A comprehensive government job portal for India. We aggregate:
- Job notifications (recruitment advertisements)
- Exam results
- Admit cards
- Answer keys
- Syllabi

**Target user:** Indian job seekers aged 18–35 searching for government jobs (SSC, Railway, Banking, UPSC, Police, Defence, State PSC, Teaching, PSU, Postal, Medical).

**Business logic:**
- Volume of quality content → Google rankings → organic traffic → AdSense impressions → revenue
- Expired jobs ARE valuable: "SSC CGL 2024 Result" still gets searched millions of times
- Expired jobs must NOT appear at top of listings — they belong in their own section or deeper in the list
- Fresh, active jobs with upcoming deadlines must always show first

---

## 2. WHAT HAS GONE WRONG — BUG HISTORY

This is a complete audit of every major bug, mistake, and failure from day one.

### BUG-01: seen_items.json TIMEOUT POISONING (Critical, Recurring)

**What happened:** The scraper added ALL discovered sitemap URLs to `seen_items.json` at discovery time, before actually processing them. GitHub Actions has an 80-minute timeout. When the runner was killed mid-run, the intermediate `save_seen()` call had already saved ~57,000 URLs as "seen" even though 0 MDX files were written for them. On every subsequent run, the scraper saw all those URLs as already processed and skipped them. The scraper appeared to run but produced 0 new content for weeks.

**Root cause in code:** In `_scrape_sitemap_generic()`, the line `seen.add(url_id)` was executed at the point of URL discovery, not after MDX write.

**Fix applied (commit `77d015dff8`):** Removed `seen.add()` from discovery. URLs are only added to `seen` AFTER a successful MDX file is written.

**Status:** Fixed.

### BUG-02: seen_items.json MERGE POISONING (Critical)

**What happened:** A git merge brought in an older state of `seen_items.json` with 78,000+ entries from a previous deploy branch. This poisoned the scraper — everything was seen, nothing was scraped.

**Fix applied:** Rebuilt `seen_items.json` from scratch by scanning all actual `.mdx` files and re-computing their URL hashes and title hashes. Result: ~6,760 real entries instead of 78,000+ fake ones.

**Status:** Fixed. Run rebuild script if this ever happens again:
```python
# python scraper/rebuild_seen.py
# Scans content/**/*.mdx, extracts sourceUrl + title, rebuilds seen_items.json
```

### BUG-03: NUMERIC IDs AS JOB TITLES (Critical, User-Visible)

**What happened:** freejobalert.com uses numeric article IDs (e.g., `52433`, `1000367`) in its URLs. The scraper used these IDs as the slug and initial title. The parser's `if not data.title:` condition prevented the `<h1>` tag from overriding the numeric ID. So 514 files were written with titles like "52433" and slugs like "52433". The SEO rewriter then ran on these files and hallucinated content like "52433 Recruitment 2026 Notification" — completely fake.

**Root cause:** Parser code had `if not data.title: data.title = text` — the condition was wrong. Since `data.title` was already set to "52433", the real page title from `<h1>` was never applied.

**Fix applied:** Changed all parser `_extract_header` methods to `data.title = text` (always override) when a real h1/h2 is found. Also added slug regeneration in `base_parser.py`: if the initial slug was a bare integer, it's replaced with a slugified version of the real title after parsing.

**Status:** Fixed. All 514 bad files were deleted. They will be re-scraped with correct titles.

### BUG-04: PRE-2022 ITEMS BURNING FETCH SLOTS (Performance)

**What happened:** Items older than `MIN_POST_DATE = "2022-01-01"` were fetched (2-5 seconds each via the CF Worker proxy), parsed, then discarded without being marked as seen. This meant the same 3,000+ pre-2022 URLs would be re-fetched on every single run, eating most of the 80-minute GitHub Actions budget.

**Fix applied (commit `f47963cde0`):** After date-filter skip and kind-mismatch skip, `seen.add(item['_seen_id'])` is called immediately. These items will never be fetched again.

**Status:** Fixed.

### BUG-05: SEO REWRITER GENERATING FAKE CONTENT

**What happened:** The `seo_rewriter.py` agent ran on files that had numeric IDs as titles (see BUG-03). It generated content like "52433 Recruitment 2026 — Check Notification PDF, Application Form, Eligibility, Salary" — completely fabricated data. This content went live.

**Fix applied:** Parser now writes correct titles before the rewriter ever sees a file. All 514 affected files deleted. The rewriter now has a guard: if `title` is purely numeric or fewer than 10 characters, skip the file.

**Status:** Partially fixed. Files deleted; rewriter guard needed (pending implementation).

### BUG-06: KIND-MISMATCH ITEMS NOT MARKED SEEN

**What happened:** Some sitemap items scrape as a different kind (e.g., a URL categorized as "job" actually contains a "result" page). These were fetched, kind-checked, rejected, but NOT marked as seen. They were re-fetched on every run.

**Fix applied:** Added `seen.add()` after kind-mismatch rejection.

**Status:** Fixed.

### BUG-07: MAX_PER_KIND CAPS TOO LOW

**What happened:** Previous caps were `{'job': 200, 'result': 150, 'admit': 150, ...}`. After fixing BUG-04 (pre-cutoff waste), there was room for more processing, but the caps prevented it.

**Fix applied:** Raised to `{'job': 400, 'result': 350, 'admit': 350, 'answer-key': 60, 'syllabus': 60}`.

**Status:** Fixed.

### BUG-08: DATE PARSING INCONSISTENCY IN FRONTEND

**What happened:** MDX files use two date formats: `DD/MM/YYYY` and `DD-MM-YYYY`. The `parseDDMMYYYY` function in `lib/content.ts` only accepted `/` separator. Dates with `-` separator were silently ignored, causing jobs to show "No deadline" even when `lastDate` was set.

**Fix applied:** Changed regex to `/(\d{2})[\/\-](\d{2})[\/\-](\d{4})/`.

**Status:** Fixed.

### BUG-09: CATEGORY MAPPING MISMATCH

**What happened:** `TYPE_DIR_MAP` in `mdx_generator.py` maps page_type strings to content directory names. At various points, the scraper produced page_type values not in the map (e.g., `admit_card` instead of `admit`), causing MDX files to be written to wrong directories or skipped.

**Fix applied:** Standardized all type strings. Added slug-based page_type inference as last-resort fallback.

**Status:** Fixed.

### BUG-10: SLUG COLLISIONS FROM SHORT TITLES

**What happened:** Multiple jobs with the same short title (e.g., "Recruitment 2025") generated identical slugs. MDX generator overwrote existing files silently.

**Fix applied:** MDX generator appends a hash suffix when a slug collision is detected.

**Status:** Fixed.

### BUG-11: CF WORKER PROXY SECRETS IN CODE

**What happened:** At one point, `CF_WORKER_PROXY_URL` and `CF_WORKER_SECRET` values were hardcoded in Python files and committed to the repo.

**Fix applied:** Removed from code. Now read only from environment variables. GitHub Actions secrets provide them. NEVER commit these values.

**Rule (permanent):** `CF_WORKER_PROXY_URL` and `CF_WORKER_SECRET` are GitHub Actions secrets ONLY. Never in code, never in `.env` committed to repo.

**Status:** Fixed.

### BUG-12: FRAMER MOTION + THREE.JS BUNDLE SIZE

**What happened:** The site loads `framer-motion`, `@react-three/fiber`, and `three` for animations. These are 500KB+ of JS that must parse before any interaction. This hammers Core Web Vitals (FID/INP) on slow Indian mobile connections.

**Status:** Not yet fixed. To fix: lazy-load animation components, or replace Three.js with CSS animations.

### BUG-13: `parseDDMMYYYY` NOT HANDLING MONTH NAMES

**What happened:** Some scraper sources return dates like "15 June 2026" or "June 15, 2026". These are not parsed at all and stored as raw strings. The frontend treats them as invalid dates.

**Status:** Partially addressed. A date normalization pass is needed in the scraper.

---

## 3. ARCHITECTURE OVERVIEW

### Technology Stack

```
Content layer:      MDX files with YAML frontmatter (no database)
Frontend:           Next.js 15 (App Router), TypeScript, Tailwind CSS
Deployment:         Cloudflare Pages (static HTML export via `output: "export"`)
Scraper:            Python 3.x, BeautifulSoup4, httpx
Proxy:              Cloudflare Worker (nd-proxy.awesomeashoksingh.workers.dev)
CI/CD:              GitHub Actions (`daily-scraper.yml`)
Analytics:          Google Analytics 4 + Google Tag Manager
Search:             Client-side (search-index.json built at deploy time)
```

### Scraper → Content → Frontend Flow

```
Python Scraper
  └─ Fetches listing pages (paginated HTML) from 5 sources
  └─ Fetches detail pages via CF Worker proxy
  └─ Parses HTML with source-specific parsers
  └─ Produces DetailData objects
  └─ Generates MDX files in content/{type}/{category}/{slug}.mdx
  └─ Updates seen_items.json to prevent re-scraping

Git commit + push
  └─ GitHub Actions triggers Cloudflare Pages build
  └─ Next.js builds static HTML from MDX files
  └─ Cloudflare Pages deploys to CDN

User request
  └─ Cloudflare Pages serves static HTML
  └─ Next.js client-side JS hydrates for interactivity
```

### The Five Scraper Sources

| Source | Method | ID type | Notes |
|--------|--------|---------|-------|
| sarkariresult.com | Listing + Sitemap | URL hash | Highest volume; 8 page types |
| freejobalert.com | Listing | Numeric article ID | IDs look like "52433" — see BUG-03 |
| sarkariexam.com | Listing | URL hash | Similar layout to sarkariresult |
| naukri.com | API | Item ID | Structured JSON; clean titles |
| rojgarlive.com | Listing | URL hash | Good date coverage |

### seen_items.json — How It Works

Two types of entries:
1. **URL hash** (sitemap items): `md5(url)[:14]` → True
2. **Title+dept hash** (listing items): `md5(title.lower() + dept.lower())[:14]` → True

An item is skipped if its hash exists in `seen_items.json`. Items are only added to seen AFTER a successful MDX write.

**Never** add items to seen at discovery time. Always at write time.

---

## 4. CONTENT STRUCTURE & URL RULES

### Directory Structure

```
content/
  jobs/
    ssc/          → /jobs/ssc/{slug}/
    railway/      → /jobs/railway/{slug}/
    banking/      → /jobs/banking/{slug}/
    upsc/         → /jobs/upsc/{slug}/
    police/       → /jobs/police/{slug}/
    defence/      → /jobs/defence/{slug}/
    state-psc/    → /jobs/state-psc/{slug}/
    government/   → /jobs/government/{slug}/   (catch-all)
    teaching/     → /jobs/teaching/{slug}/
    psu/          → /jobs/psu/{slug}/
    postal/       → /jobs/postal/{slug}/
    medical/      → /jobs/medical/{slug}/
  results/
    [same categories]
  admit-cards/
    [same categories]
  answer-keys/
    government/   (currently only one)
  syllabus/
    government/   (currently only one)
```

### URL Pattern Rules

| Page | URL Pattern | Example |
|------|-------------|---------|
| Job detail | `/jobs/{category}/{slug}/` | `/jobs/ssc/ssc-cgl-2025-recruitment/` |
| Result detail | `/results/{category}/{slug}/` | `/results/railway/rrb-ntpc-result-2025/` |
| Admit card | `/admit-cards/{category}/{slug}/` | `/admit-cards/banking/ibps-po-admit-2025/` |
| Answer key | `/answer-keys/{category}/{slug}/` | `/answer-keys/government/ssc-cgl-answer-key-2025/` |
| Syllabus | `/syllabus/{category}/{slug}/` | `/syllabus/government/upsc-cse-syllabus/` |
| Category listing | `/jobs/{category}/` | `/jobs/ssc/` |
| All jobs hub | `/jobs/` | `/jobs/` |
| Latest jobs | `/latest-jobs/` | `/latest-jobs/` |
| Latest results | `/results/` | `/results/` |
| Latest admits | `/admit-cards/` | `/admit-cards/` |
| Search | `/search/` | `/search/` |
| State filter | `/state/{state}/` | `/state/uttar-pradesh/` |

### URL Rules
- Always lowercase, hyphen-separated
- No underscores
- Trailing slash always (enforced by `trailingSlash: true` in next.config.ts)
- Slug max 120 characters
- Slugs must be descriptive: include org name + exam name + year
- Never use numeric IDs as slugs (see BUG-03)
- Category must match exactly one of the valid values in Section 5

### MDX Frontmatter — All Fields

```yaml
---
title: "SSC CGL 2025 Recruitment — 17727 Vacancies, Apply Online"
slug: "ssc-cgl-2025-recruitment-17727-vacancies"
type: "job"                          # job | result | admit | answer-key | syllabus
category: "ssc"                      # see Section 5 for valid values
dept: "SSC"                          # department code (see Section 5)
organization: "Staff Selection Commission"
totalPosts: "17727"
lastDate: "15/07/2025"               # DD/MM/YYYY format ONLY
applicationBegin: "12/06/2025"       # DD/MM/YYYY format ONLY
examDate: ""                         # optional
ageMin: 18
ageMax: 32
qualification: "Graduate in any stream"
qualificationItems:
  - "Bachelor's degree from recognized university"
  - "Valid CCC certificate (optional)"
salary: "Pay Level 4-8 (₹25,500 – ₹81,100)"
applyUrl: "https://ssc.nic.in/..."
notificationUrl: "https://ssc.nic.in/..."
officialWebsiteUrl: "https://ssc.nic.in"
sourceUrl: "https://www.sarkariresult.com/..."  # original scrape URL
publishedAt: "2025-06-01"            # YYYY-MM-DD, set once at creation
updatedAt: "2025-06-01"              # YYYY-MM-DD, update when re-processed
shortDescription: "SSC CGL 2025 notification released for 17727 posts. Apply online from 12 June to 15 July 2025. Eligibility: Graduate. Salary up to ₹1,51,100."
dates:
  Advertisement Date: "01/06/2025"
  Application Begin: "12/06/2025"
  Last Date: "15/07/2025"
fees:
  General/OBC/EWS: "₹100"
  SC/ST/PwBD/Female: "₹0 (Exempt)"
vacancyBreakdown:
  - post_name: "Junior Engineer"
    total: "1765"
    general: "800"
    obc: "400"
    sc: "250"
    st: "150"
    ews: "165"
howToApply:
  - "Visit official SSC website ssc.nic.in"
  - "Click on 'Apply Online' under CGL 2025"
  - "Register with valid email and mobile"
  - "Fill application form and upload documents"
  - "Pay application fee (₹100 for General)"
  - "Submit and download confirmation page"
importantLinks:
  - label: "Apply Online"
    url: "https://ssc.nic.in/..."
    link_type: "apply"
  - label: "Download Notification"
    url: "https://ssc.nic.in/.../notification.pdf"
    link_type: "notification"
downloadLinks:
  - label: "Official Notification PDF"
    url: "https://..."
---

[MDX content body here]
```

**Date format rule:** ALL dates in frontmatter must be `DD/MM/YYYY`. No other format. The frontend parser only accepts this format (fixed in lib/content.ts).

---

## 5. CATEGORIES & DEPARTMENTS — ALL VALID VALUES

### Valid Category Values

| category value | Display Name | Content Types | Description |
|---------------|--------------|---------------|-------------|
| `ssc` | SSC | jobs, results, admits, answer-keys, syllabus | Staff Selection Commission |
| `railway` | Railway | jobs, results, admits, answer-keys, syllabus | RRB, RRC, Railway Board |
| `banking` | Banking | jobs, results, admits | IBPS, SBI, RBI, NABARD |
| `upsc` | UPSC | jobs, results, admits, syllabus | Civil Services, CDS, NDA |
| `police` | Police | jobs, results, admits | State police, CISF, CRPF, BSF |
| `defence` | Defence | jobs, results, admits | Army, Navy, Air Force, CDS |
| `state-psc` | State PSC | jobs, results, admits | UPPSC, MPPSC, RPSC, BPSC, etc. |
| `government` | Government | jobs, results, admits | Catch-all for ministry/PSU/others |
| `teaching` | Teaching | jobs, results | TGT, PGT, NTA NET, CTET, TET |
| `psu` | PSU | jobs, results | ONGC, BHEL, SAIL, NTPC, GAIL |
| `postal` | Postal | jobs, results, admits | India Post, GDS, Postman |
| `medical` | Medical | jobs, results | AIIMS, NHM, Nursing, Para-medical |

### Valid Dept Values (uppercase string codes)

These are organization-level groupings, different from `category`:

```
SSC         → Staff Selection Commission
RAILWAY     → Railway Recruitment Board / RRC
BANK        → Any banking organization
UPSC        → Union Public Service Commission
POLICE      → Any police organization  
ARMY        → Indian Army / Defence recruitment
NAVY        → Indian Navy
AIRFORCE    → Indian Air Force
NVS         → Navodaya Vidyalaya Samiti
KVS         → Kendriya Vidyalaya Sangathan
AIIMS       → All India Institute of Medical Sciences
NHM         → National Health Mission
POST        → India Post / Postal Department
ONGC        → Oil and Natural Gas Corporation
NTPC        → National Thermal Power Corporation
DRDO        → Defence Research and Development Organisation
ISRO        → Indian Space Research Organisation
HIGH COURT  → Any High Court
[STATE]     → State-specific (e.g., UP, MP, RJ, etc.)
OTHER       → Default fallback
```

### Category Assignment Rules

1. If organization is SSC → `category: "ssc"`, `dept: "SSC"`
2. If organization contains "Railway" or "RRB" → `category: "railway"`, `dept: "RAILWAY"`
3. If organization is IBPS, SBI, RBI, bank → `category: "banking"`, `dept: "BANK"`
4. If organization is UPSC → `category: "upsc"`, `dept: "UPSC"`
5. If "Police" in org name → `category: "police"`, `dept: "POLICE"`
6. If Army/Navy/Air Force/CDS/NDA → `category: "defence"`, `dept: "ARMY"/"NAVY"/"AIRFORCE"`
7. If "PSC" in org name (UPPSC, MPPSC, etc.) → `category: "state-psc"`, `dept: "[STATE]"`
8. If Teaching (TGT, PGT, NET, TET) → `category: "teaching"`, `dept: "NVS"/"KVS"/etc.`
9. If Post/Postal/GDS → `category: "postal"`, `dept: "POST"`
10. If Medical/Nursing/AIIMS → `category: "medical"`, `dept: "AIIMS"/"NHM"`
11. If PSU (ONGC, NTPC, BHEL, etc.) → `category: "psu"`, `dept: "[ORG]"`
12. Everything else → `category: "government"`, `dept: "OTHER"`

---

## 6. SORTING SYSTEM

### Core Principle

**Active jobs FIRST. Expired jobs LAST. Within each group, sort by relevance.**

### Sorting Algorithm (per listing page)

```
1. ACTIVE GROUP (deadline >= today OR no deadline set):
   Sort by: soonest lastDate first (ascending)
   Rationale: Users need to act fast on jobs closing soon
   
2. RECENTLY PUBLISHED (no deadline, published within 30 days):
   Sort by: publishedAt descending
   
3. EXPIRED GROUP (deadline < today):
   Sort by: publishedAt descending (newest post first)
   Rationale: Expired jobs still get searched; show most-relevant first
   DO NOT show expired jobs on page 1 if active jobs are available
```

### Applied Per Content Type

**Jobs listing:**
- Active: soonest deadline first
- Expired: by publish date descending
- Never show expired jobs in top 10 if there are 10+ active jobs

**Results listing:**
- Sort by publishedAt descending (all results are "done" — no deadline)
- Most recent result at top

**Admit cards listing:**
- Sort by examDate ascending (soonest exam first, if date known)
- If no examDate, sort by publishedAt descending

**Answer keys:**
- Sort by publishedAt descending

**Syllabus:**
- Sort by publishedAt descending (syllabus doesn't expire in the same way)

### Implementation (lib/content.ts)

```typescript
// Active-first sort — already implemented as sortByActiveFirst()
// Active = lastDate >= today, or no lastDate
// Within active: sort by soonest deadline
// Within expired: sort by newest publishedAt
```

### Why Expired Jobs Exist on the Site

Rationale: "SSC CGL 2024 Result", "RRB NTPC 2024 Cut-off" still get millions of searches monthly. These pages rank on Google and bring traffic. That traffic generates AdSense impressions. So expired content has real value — it just must not appear at the top of active listings, confusing users who want to apply.

**Rule:** Never put an expired job in the top 3 positions of any active listing page.

---

## 7. SEO FOUNDATION — COMPLETE RULES

### 7.1 Title Tag Rules

**Format:** `{Post Title} | Naukri Dhaba`  
Applied via Next.js metadata template: `%s | ${siteConfig.name}`

**Per-page title rules:**

| Page | Title Pattern | Example |
|------|---------------|---------|
| Job detail | `{Job Title} {Year} — {Vacancies} Vacancies` | `SSC CGL 2025 — 17727 Vacancies Apply Online` |
| Result detail | `{Exam} Result {Year} — Check Merit List` | `RRB NTPC Result 2025 — Check CEN 01/2019` |
| Admit card | `{Exam} Admit Card {Year} — Download Hall Ticket` | `IBPS PO Admit Card 2025 — Download Now` |
| Answer key | `{Exam} Answer Key {Year} — Objection, Cut-off` | `SSC GD Constable Answer Key 2025` |
| Syllabus | `{Exam} Syllabus {Year} — Exam Pattern, PDF` | `UPSC CSE Syllabus 2025 — Prelims, Mains, Interview` |
| Category | `{Category} Jobs {Year} — Latest Notifications` | `SSC Jobs 2025 — Latest Recruitment Notifications` |
| Home | `Sarkari Naukri 2025 — Latest Govt Jobs, Results & Admit Cards` | (static) |

**Rules:**
- Max 60 characters (Google truncates at ~60)
- Must include year (2025/2026 — use the post's year, not "current")
- Must include primary keyword at start
- Never use clickbait ("Shocking!", "You won't believe")
- Never duplicate across pages (each title must be unique)

### 7.2 Meta Description Rules

**Max:** 160 characters  
**Min:** 120 characters  

**Pattern:** `{Org} {type} {year}. {Vacancies} posts. Eligibility: {qualification}. Last date: {lastDate}. Apply at Naukri Dhaba.`

**Example:**
```
SSC CGL 2025 recruitment notification for 17727 posts. 
Eligibility: Graduate. Last date: 15/07/2025. 
Check eligibility, fees, dates and apply online.
```

**Rules:**
- Must include primary keyword (exam name + year)
- Must include at least one number (vacancies, date, or year)
- Must have a call-to-action ("Apply online", "Check result", "Download")
- Never use generic phrases: "This page contains information about..."
- Never duplicate descriptions

### 7.3 Canonical URL Rules

- Every page must have a canonical URL
- Format: `https://naukridhaba.in{path}/` (with trailing slash)
- Category: `/jobs/ssc/` canonical = `https://naukridhaba.in/jobs/ssc/`
- Detail: `/jobs/ssc/ssc-cgl-2025/` canonical = `https://naukridhaba.in/jobs/ssc/ssc-cgl-2025/`
- Never set canonical to a different domain
- `/go/` redirect pages must be `noindex`

### 7.4 Open Graph Rules

```typescript
og:title     = same as <title> (without " | Naukri Dhaba")
og:description = same as meta description
og:image     = https://naukridhaba.in/og-default.png (1200×630px)
og:type      = "website" for listings, "article" for detail pages
og:url       = same as canonical
```

### 7.5 Sitemap Rules

- All content pages: `priority 0.6`, `changeFrequency: "weekly"`
- Category pages: `priority 0.8`, `changeFrequency: "daily"`  
- Home, Latest Jobs, Results, Admits: `priority 0.9–1.0`, `changeFrequency: "daily"`
- Search page: `priority 0.5`, `changeFrequency: "monthly"`
- The `/go/` redirect page: exclude from sitemap
- All URLs must match actual pages (no 404s in sitemap)
- Sitemap is dynamically generated at build time via `app/sitemap.ts`

### 7.6 robots.txt Rules

```
User-agent: *
Allow: /
Disallow: /go/
Disallow: /api/
Sitemap: https://naukridhaba.in/sitemap.xml
```

Never disallow content pages. Only disallow utility/redirect pages.

### 7.7 Core Web Vitals Rules

**LCP (Largest Contentful Paint) — target < 2.5s:**
- Hero image must be `loading="eager"` and `fetchPriority="high"`
- OG/hero images should be < 100KB
- Avoid heavy fonts above the fold

**CLS (Cumulative Layout Shift) — target < 0.1:**
- All AdSense ad units must have fixed dimensions or `min-height` set
- Images must have `width` and `height` attributes always set
- Never load content that shifts existing content

**INP (Interaction to Next Paint) — target < 200ms:**
- Lazy-load Framer Motion and Three.js components (not imported at root level)
- Use `dynamic(() => import(...), { ssr: false })` for heavy animation components

---

## 8. H1 / H2 / H3 USAGE RULES

### Rule 1: One H1 Per Page

Every page must have exactly one `<h1>`. The H1 must contain the primary keyword.

| Page | H1 Content |
|------|-----------|
| Job detail | `{Job Title}` (verbatim from `title` field) |
| Category listing | `{Category Name} Jobs {Year}` |
| Latest Jobs | `Latest Government Jobs {Year}` |
| Result detail | `{Exam Name} Result {Year}` |
| Home | `Sarkari Naukri {Year} — Latest Government Jobs` |

### Rule 2: H2 Must Immediately Follow H1 on Listing Pages

Listing pages currently skip from H1 to table. This is wrong. Add H2:

```jsx
<h1>SSC Jobs 2025</h1>
<h2>Latest SSC Recruitment Notifications 2025 — Check Vacancies, Eligibility & Apply Online</h2>
<p>{count} notifications available. Updated daily.</p>
```

### Rule 3: H2 Usage on Detail Pages

Detail pages must use H2 for each major section:

```
H1: {Job Title}
H2: Important Dates & Application Deadline
H2: Application Fee
H2: Eligibility / Qualification
H2: Vacancy Breakdown
H2: Salary / Pay Scale
H2: How to Apply — Step-by-Step Guide
H2: Important Links
H2: Frequently Asked Questions
```

These H2s are rendered by the card components. The order matters for semantic flow and Google understanding.

### Rule 4: H3 Usage

H3 is for sub-sections within an H2. Examples:
```
H2: Eligibility / Qualification
  H3: Educational Qualification
  H3: Age Limit
  H3: Age Relaxation (SC/ST/OBC/PwBD)
```

### Rule 5: Never Skip Levels

Never go H1 → H3 (skipping H2). Never go H2 → H4 (skipping H3). This breaks semantic hierarchy and confuses Google's content understanding.

### Rule 6: H1 Must Match Title Tag

The page `<title>` tag and the `<h1>` must be the same (or near-identical). They should not be completely different topics.

---

## 9. CONTENT SIZE RULES (MIN/MAX)

### Job Detail Page

| Section | Minimum | Maximum | Notes |
|---------|---------|---------|-------|
| `shortDescription` | 120 chars | 200 chars | Used as meta description |
| MDX body (total text) | 400 words | 2,000 words | Google considers <300 words thin |
| `howToApply` steps | 5 steps | 15 steps | Each step: 10–100 chars |
| FAQ section | 3 Q&A pairs | 10 Q&A pairs | Auto-generated from content |
| `dates` entries | 2 | 10 | At minimum: begin date + last date |
| `vacancyBreakdown` | 1 row | 30 rows | Per-post breakup when available |

### Listing Page (Category/Latest)

| Element | Min | Max | Notes |
|---------|-----|-----|-------|
| Items shown per page | 20 | 50 | Pagination for rest |
| Category description text | 100 words | 300 words | Show above the table |
| H2 intro text | 30 chars | 150 chars | Keyword-rich |

### Result Page

| Section | Min | Max |
|---------|-----|-----|
| shortDescription | 120 chars | 200 chars |
| Content body | 300 words | 1,500 words |

### SEO Rewriter Output Rules

When the `seo_rewriter.py` agent processes a file, it must:
- NOT reduce total content below 400 words
- NOT change the `title`, `slug`, `category`, `dept`, `dates`, `fees`, `vacancyBreakdown`, or any structured data field
- Only modify: `shortDescription`, MDX body prose, FAQ section
- Ensure FAQ section has at least 3 Q&A pairs
- Ensure `shortDescription` is 120-200 chars
- Skip files where title is purely numeric or < 10 characters
- Skip files where `sourceUrl` is missing

---

## 10. METADATA RULES

### buildMetadata() — How It Works

Every page must call `buildMetadata()` from `lib/seo.ts`. This function:
1. Generates title with template: `{title} | Naukri Dhaba`
2. Sets canonical URL
3. Sets OG/Twitter tags
4. Sets robots: `{index: true, follow: true}`

### Pages Missing Metadata (Fix Required)

1. `/search/page.tsx` — MISSING. Add:
```typescript
export const metadata: Metadata = buildMetadata({
  title: "Search Government Jobs — SSC, Railway, Banking, UPSC",
  description: "Search across 4000+ latest government job notifications, results, and admit cards from SSC, Railway, Banking, UPSC and more.",
  path: "/search/",
});
```

2. `/about/page.tsx`, `/contact/page.tsx`, `/privacy/page.tsx`, `/disclaimer/page.tsx` — Verify these have proper metadata, not just generic titles.

### GSC (Google Search Console) HTML Verification Tag

`app/layout.tsx` line 27 appears to have an empty GSC verification tag. This must be filled in with the actual verification meta tag from Search Console.

---

## 11. STRUCTURED DATA (JSON-LD) RULES

### What's Already Implemented (Keep These)

| Schema Type | Pages | Status |
|-------------|-------|--------|
| `JobPosting` | Job detail pages | ✓ Implemented |
| `FAQPage` | All detail pages with **Q:**/**A:** pattern | ✓ Implemented |
| `BreadcrumbList` | All category + detail pages | ✓ Implemented |
| `LearningResource` | Result pages | ✓ Implemented |
| `Event` | Admit card pages | ✓ Implemented |
| `Course` | Syllabus pages | ✓ Implemented |
| `LearningResource` | Answer key pages | ✓ Implemented |
| `CollectionPage + ItemList` | Category listing pages | ✓ Implemented |
| `WebSite + Organization` | Homepage | ✓ Implemented |

### What Needs to be Added

**HiringOrganization sameAs for major orgs:**
```typescript
const MAJOR_ORG_URLS: Record<string, string> = {
  "Staff Selection Commission": "https://ssc.nic.in",
  "Railway Recruitment Board": "https://www.rrbcdg.gov.in",
  "Union Public Service Commission": "https://upsc.gov.in",
  "IBPS": "https://www.ibps.in",
  "State Bank of India": "https://sbi.co.in",
};
```
If `fm.organization` matches a key, add `sameAs` to the `HiringOrganization` in `JobPosting` schema.

**Review FAQ extraction fragility:**
- Current pattern requires exactly `**Q:**` and `**A:**`
- Add fallback: look for numbered Q&A in format "1. What is..." 
- If no FAQ pattern found, generate 3 default questions from frontmatter data

### Structured Data Validation Rules

- Always validate at https://search.google.com/test/rich-results after changes
- `publishedAt` and `updatedAt` must be in ISO-8601 (`YYYY-MM-DD`), not DD/MM/YYYY
- `baseSalary.value.minValue` must be a number (not a string with ₹ sign)
- `jobLocation.addressLocality` must be a real city name (not "India" or "Pan India")

---

## 12. INTERNAL LINKING STRATEGY

### Current State

- Breadcrumbs: ✓ (Home → Type → Category → Post)
- Navigation links: ✓ (Header to main sections)
- "View All" from homepage sections: ✓
- Related Posts: ✗ MISSING
- Topic clusters: ✗ MISSING
- "More in Category" on detail pages: ✗ MISSING

### What to Add

**1. Related Posts Widget** (high priority)
On every job/result/admit detail page, show 3-5 posts from the same category:
```
"More SSC Jobs"
→ SSC CHSL 2025 Recruitment (2500 posts)
→ SSC GD Constable 2025 (50000 posts)  
→ SSC JE 2025 Notification
```
Implementation: In `generateStaticParams`, pass same-category slugs as related posts.

**2. Cross-type Linking** (medium priority)
On a job page for "SSC CGL 2025", link to:
- "SSC CGL 2025 Result" (when available)
- "SSC CGL 2025 Admit Card" (when available)
- "SSC CGL Syllabus" (permanent link)
Implementation: Query content by matching title prefix or `dept` + year.

**3. Category Description Pages** (high priority for SEO)
Each category listing page (`/jobs/ssc/`) should have 100–200 words of intro text:
```html
<h2>Latest SSC Jobs 2025</h2>
<p>SSC (Staff Selection Commission) conducts various examinations like CGL, CHSL, 
MTS, GD Constable, and JE to recruit into Group B and C posts in central government 
departments. Below are the latest SSC job notifications...</p>
```
This text is indexed by Google and helps the category page rank for "SSC jobs 2025".

**4. State-Based Internal Links**
From state PSC job pages, add links to:
- All jobs from that state: `/state/{state-slug}/`
- Related state PSC results

### Internal Linking Rules

- Every page must link to its parent category page (via breadcrumb or explicit link)
- Every category page must link to the main hub (`/jobs/`, `/results/`, `/admit-cards/`)
- Job detail pages must link to the Apply URL with `rel="noopener"` (external, new tab)
- Official notification PDFs: link directly, no tracking wrapper needed
- Apply URL: use `/go/?url={encoded}` wrapper for click tracking

---

## 13. SCRAPER SYSTEM — ARCHITECTURE & RULES

### The Two-Phase Process

**Phase 1: Listing scrape** (runs first, faster)
- Fetches paginated listing pages from each source
- Produces items with: title, url, date_str, dept, page_type
- Items get `_seen_id` = `md5(title.lower() + dept.lower())[:14]`
- Cap: `MAX_PER_KIND` (400 jobs / 350 results / 350 admits / etc.)

**Phase 2: Sitemap backfill** (runs after listing, slower)
- Reads XML sitemaps from each source
- Discovers URLs not found in listing phase
- Items get `_seen_id` = `md5(url)[:14]`
- These fill gaps in listing coverage (older posts not on page 1-5 of listing)

**Phase 3: Detail fetch**
- Each item from phases 1 & 2 is fetched via CF Worker proxy
- Source-specific parser extracts structured data
- MDX generator writes the file
- `seen_items.json` is updated with `_seen_id`

### CF Worker Proxy — Why It's Needed

Cloudflare (the CDN used by sarkariresult.com and others) blocks requests from GitHub Actions IP ranges with 403 errors. The CF Worker proxy (our own Cloudflare Worker) acts as a middleman: the scraper sends requests to our worker, which relays to the target site, appearing as a legitimate browser from a different IP.

**Proxy URL:** `CF_WORKER_PROXY_URL` (GitHub Actions secret — NEVER hardcode)  
**Proxy secret:** `CF_WORKER_SECRET` (GitHub Actions secret — NEVER hardcode)

### GitHub Actions Configuration

**Timeout:** 80 minutes (`timeout-minutes: 80`)  
**Self-trigger:** On completion, the workflow dispatches itself again via `repository_dispatch` if targets not met  
**Schedule:** Daily at 00:00 UTC, plus manual trigger

### seen_items.json Maintenance Rules

1. NEVER add to seen at URL discovery time — only after successful MDX write
2. If a run is killed, the partial seen updates from within-run saves are acceptable (those items were already written)
3. The intermediate `save_seen()` calls every 50 items are correct behavior
4. To rebuild from scratch: `python scraper/rebuild_seen.py`
5. The file should have approximately: (total MDX files × 2) entries maximum
6. Current expected size: ~8,000–10,000 entries when site has ~4,000 MDX files

### Parser Rules

- Every parser `_extract_header()` must ALWAYS set `data.title = text` when h1/h2 found (not `if not data.title`)
- Never use numeric IDs as titles
- If no h1/h2 found, use the item's `title` from listing phase
- Slug must be regenerated from real title if initial slug was a bare integer
- dates must be normalized to `DD/MM/YYYY` format during extraction
- organization_full_name should be the full legal name, not an abbreviation

---

## 14. SCRAPER ALTERNATIVES (NON-GITHUB-ACTIONS)

GitHub Actions is unreliable for the scraper because:
1. 80-minute timeout kills long runs
2. GitHub IP blocks by Cloudflare on target sites
3. No persistent state between runs (seen_items.json must be committed)

### Option A: Local Laptop (Windows Task Scheduler / macOS launchd)

**Best for:** Running on your own machine, full control, no cloud costs.

**Setup:**
```bash
# Install dependencies
pip install -r scraper/requirements.txt

# Create a .env file (never commit this):
CF_WORKER_PROXY_URL=https://nd-proxy.awesomeashoksingh.workers.dev
CF_WORKER_SECRET=your-secret-here

# Run scraper directly:
cd /path/to/naukri-dhaba
python scraper/sarkari_scraper.py

# After run, commit and push:
git add content/ scraper/seen_items.json
git commit -m "chore: scrape $(date +%Y-%m-%d)"
git push origin main
```

**Windows Task Scheduler:**
Create a batch script `run_scraper.bat`:
```batch
cd C:\path\to\naukri-dhaba
python scraper\sarkari_scraper.py
git add content\ scraper\seen_items.json
git commit -m "chore: scrape auto"
git push origin main
```
Schedule: Daily, any time when laptop is on.

**macOS launchd / Linux cron:**
```cron
0 8 * * * cd /path/to/naukri-dhaba && python scraper/sarkari_scraper.py && git add content/ scraper/seen_items.json && git commit -m "chore: scrape $(date +%Y-%m-%d)" && git push origin main
```

**Pros:** No timeout, full bandwidth, easier debugging  
**Cons:** Laptop must be on, need to manage git credentials

### Option B: VPS / Dedicated Server

Any small VPS (DigitalOcean Droplet $6/month, Hetzner Cloud €4/month) can run the scraper on a cron schedule.

```bash
# On VPS:
git clone git@github.com:ashoksingh-ayodhya/naukri-dhaba.git
pip install -r naukri-dhaba/scraper/requirements.txt
# Set .env with secrets
crontab -e
# Add: 0 */6 * * * /usr/bin/python3 /root/naukri-dhaba/scraper/sarkari_scraper.py && cd /root/naukri-dhaba && git add content/ scraper/seen_items.json && git commit -m "chore: auto scrape" && git push
```

**Pros:** Always on, no laptop needed, faster  
**Cons:** Small cost, need to manage server

### Option C: Claude Code on Laptop (Current Fallback)

The current setup where you open Claude Code and trigger the scraper manually via GitHub Actions. This works but requires manual initiation.

**Improvement:** Keep GitHub Actions for deployment only. Add a "scraper dispatch" button in the repo's Actions tab for manual triggers when needed.

### Option D: GitHub Actions with Extended Timeout

**Current limit:** 80 minutes for free tier (GitHub Free)  
**GitHub Pro:** No difference for Actions minutes  
**GitHub Team:** 3,000 minutes/month (same timeout limit)

The timeout issue is inherent to Actions. The solution isn't a longer timeout — it's making the scraper faster (fixed with pre-cutoff seen marking).

### Recommendation

**Primary:** GitHub Actions (already set up, self-triggering, no cost)  
**Fallback:** Local laptop cron if GitHub Actions is blocked/failing  
**For heavy backfill runs:** Local laptop (no 80-min limit, can run 4+ hours)

---

## 15. CONTENT REWRITER RULES

The `agent/tasks/seo_rewriter.py` agent rewrites MDX content for SEO. These are its hard rules:

### What It CAN Change

- `shortDescription` (must stay 120-200 chars)
- MDX body prose paragraphs
- FAQ section (`**Q:** ... **A:** ...` format)
- Add/improve H2/H3 headings in body

### What It CANNOT Change (Immutable Fields)

- `title`
- `slug`
- `category`
- `dept`
- `type`
- `organization`
- `totalPosts`
- `lastDate`, `applicationBegin`, `examDate`
- `dates {}` (dict)
- `fees {}` (dict)
- `vacancyBreakdown []`
- `importantLinks []`
- `howToApply []`
- `applyUrl`, `notificationUrl`
- `publishedAt`
- `sourceUrl`

### Guard Conditions (Skip File If)

- `title` is purely numeric (all digits)
- `title` is fewer than 10 characters
- `sourceUrl` is missing or empty
- File was updated within last 24 hours (don't re-process fresh files)
- `shortDescription` is already > 150 chars AND content is > 500 words (already good)

### Quality Rules for Rewritten Content

- Describe the actual exam/organization/role — no generic "Recruitment 2026" without specifics
- Include at minimum: org name, number of posts (if known), eligibility, year
- Must NOT invent data: never say "500 vacancies" if not in frontmatter
- Must NOT add fake dates
- Use neutral, professional tone — no marketing language
- FAQ questions must be genuinely useful: "What is the age limit?", "What is the salary?", etc.
- All FAQ answers must be based ONLY on frontmatter data (never hallucinate)

### Frequency

- Run 3x per day (current setup via GitHub Actions)
- Re-process all files once every 30 days for freshness updates
- Always run on newly scraped files (within 24 hours of creation)

---

## 16. CMS SYSTEM DESIGN

### Current "CMS" = MDX Files + YAML Frontmatter

The current system is intentionally design-agnostic:
- **Content** is in MDX files with structured YAML frontmatter
- **Design** is in Next.js components that read the frontmatter
- Changing the design never requires touching content files

This is the correct architecture. The CMS is the MDX file system.

### How to Change Design Without Affecting Content

To completely redesign the site:
1. Rewrite `app/` and `components/` — content untouched
2. The `lib/content.ts` functions that read MDX stay the same
3. The frontmatter schema (defined in `lib/types.ts`) is the API contract

**Rule:** Never put design logic in MDX files. MDX body should be semantic text, not JSX components.

### Content Management Workflow

**Adding a single post manually:**
1. Create `content/{type}/{category}/{slug}.mdx` with all frontmatter fields
2. MDX body: paste official notification text + How to Apply steps
3. `git add content/{type}/{category}/{slug}.mdx`
4. `git commit -m "content: add {title}"`
5. `git push origin main`
6. Cloudflare Pages auto-deploys

**Editing an existing post:**
1. Edit the MDX file
2. Update `updatedAt: YYYY-MM-DD`
3. Git add + commit + push

**Deleting a post:**
1. `git rm content/{type}/{category}/{slug}.mdx`
2. Ensure the slug is added to a "deleted slugs" list so the sitemap doesn't reference it
3. If the page was indexed by Google, add a 410 (Gone) response — but since we're static, use a redirect from the old URL to the category page

### Future CMS (If Needed)

If manual content management becomes necessary at scale, consider:
- **Sanity.io** (free tier, 3 users): headless CMS with content studio
- **Contentlayer** (current MDX processor): already in use, no change needed
- **Tina CMS**: Git-based, writes directly to MDX files — ideal for this setup

The right choice is Tina CMS: it would give a visual editor that writes to the same MDX files, no backend change needed.

---

## 17. ADSENSE OPTIMIZATION RULES

### Ad Placement Strategy

**Job Detail Page** (highest-value pages):
```
Position 1: After H1 / before PostHeader cards (728×90 leaderboard)
Position 2: Middle of content, after "Important Dates" section (336×280 rectangle)
Position 3: After "How to Apply", before FAQ (728×90 or responsive)
Position 4: After FAQ / before Related Posts (300×250 or responsive)
```

**Category Listing Page:**
```
Position 1: Below H1/H2 intro text, above the table (728×90)
Position 2: After page 1 results, within the table (native/in-feed)
```

**Home Page:**
```
Position 1: After hero section, before latest jobs grid (728×90)
Position 2: Between "Latest Jobs" and "Latest Results" sections (300×250)
```

### CLS Prevention for Ads

All ad containers must have a fixed height or min-height to prevent layout shift:
```css
.ad-container {
  min-height: 90px;   /* for leaderboard */
  min-height: 280px;  /* for rectangle */
}
```

### AdSense Policy Rules

- ✓ No keyword stuffing
- ✓ Original content (official government notifications)
- ✓ Clear privacy policy
- ✗ Do NOT show more than 3 ad units per page (policy limit for older ad formats)
- ✗ Do NOT place ads next to content that could be mistaken for ads
- ✗ Do NOT use Pop-ups or interstitials
- Ensure "About", "Contact", "Privacy Policy", "Disclaimer" pages exist and are complete

### Competing Advertiser Exclusions

In AdSense settings, add these to "Sensitive Category" exclusions:
- Employment agencies / Job boards (to block competitor ads)

---

## 18. COMPONENT DOCUMENTATION

### lib/types.ts — Post Types

```typescript
type PostType = "job" | "result" | "admit" | "answer-key" | "syllabus"
```

All MDX files must have one of these exact values in the `type` field.

### lib/content.ts — Key Functions

| Function | Purpose | Input | Output |
|----------|---------|-------|--------|
| `getAllPosts(type)` | Get all posts of a type | `"job"` | `Post[]` |
| `getPostBySlug(type, category, slug)` | Get single post | type+cat+slug | `Post \| null` |
| `getPostsByCategory(type, category)` | Filter by category | type+category | `Post[]` |
| `sortByActiveFirst(posts)` | Sort active → expired | `Post[]` | sorted `Post[]` |
| `parseDDMMYYYY(dateStr)` | Parse DD/MM/YYYY or DD-MM-YYYY | string | `Date \| null` |
| `buildMetadata(opts)` | Generate Next.js Metadata | title+desc+path | `Metadata` |

### lib/seo.ts — Key Functions

| Function | Purpose |
|----------|---------|
| `buildJobJsonLd(post)` | Generate JobPosting schema |
| `buildListingPageJsonLd(posts, category)` | Generate CollectionPage schema |
| `buildResultJsonLd(post)` | Generate LearningResource schema |
| `buildAdmitJsonLd(post)` | Generate Event schema |
| `buildFaqJsonLd(content)` | Generate FAQPage from **Q:**/**A:** markers |
| `buildBreadcrumbJsonLd(items)` | Generate BreadcrumbList |
| `inferLocation(orgName)` | Map org name to Indian city |

### app/ — Page Routes

| Route | Page | Notes |
|-------|------|-------|
| `/` | Home | Latest jobs grid, categories, hero |
| `/jobs/` | Jobs hub | All 12 categories |
| `/jobs/[category]/` | Category listing | SSC/Railway/Banking/etc. |
| `/jobs/[category]/[slug]/` | Job detail | Full post |
| `/results/` | Results hub | |
| `/results/[category]/[slug]/` | Result detail | |
| `/admit-cards/` | Admits hub | |
| `/admit-cards/[category]/[slug]/` | Admit detail | |
| `/answer-keys/` | Answer keys hub | |
| `/answer-keys/[category]/[slug]/` | Answer key detail | |
| `/syllabus/` | Syllabus hub | |
| `/syllabus/[category]/[slug]/` | Syllabus detail | |
| `/latest-jobs/` | All latest jobs | Sorted active-first |
| `/search/` | Search page | Client-side search |
| `/state/[state]/` | State filter | Jobs by state |
| `/go/` | Redirect | noindex; apply link tracker |

### components/ — Key Components

| Component | Purpose | Notes |
|-----------|---------|-------|
| `JobCard` | Single job card | Mobile: card view; desktop: table row |
| `JobsTable` | Responsive table | Switches between card/table at md breakpoint |
| `PostHeader` | Detail page header | Title, org, advt number, badges |
| `ImportantDatesCard` | Dates section | Key → Value pairs from `dates{}` |
| `ApplicationFeeCard` | Fees section | From `fees{}` |
| `VacancyBreakdown` | Posts breakdown | From `vacancyBreakdown[]` |
| `ImportantLinksCard` | Links section | Apply, Notification, Result links |
| `HowToApplyCard` | Steps section | From `howToApply[]` |
| `Breadcrumb` | Navigation | Structured data included |
| `SearchBar` | Search input | Client-side, reads search-index.json |
| `LiveTicker` | News ticker | Latest notifications — lazy-load this |
| `AnimatedSection` | Scroll animation | Uses Framer Motion — lazy-load this |

---

## 19. SEO CHECKLIST — COMPLETE

### Technical SEO

- [x] robots.txt with sitemap URL
- [x] sitemap.xml dynamically generated
- [x] Canonical URLs on all pages
- [x] HTTPS (Cloudflare handles)
- [x] Trailing slash consistency (`trailingSlash: true`)
- [x] OG tags on all pages
- [x] Twitter card tags
- [ ] GSC verification tag (empty in layout.tsx line 27 — fill in)
- [ ] Submit sitemap to Google Search Console
- [ ] Submit sitemap to Bing Webmaster Tools
- [ ] Core Web Vitals: LCP < 2.5s, CLS < 0.1, INP < 200ms (audit needed)
- [ ] Fix unoptimized images (`images.unoptimized: true` in next.config.ts)
- [ ] Lazy-load Framer Motion and Three.js

### On-Page SEO

- [x] Unique title per page
- [x] Meta description per page
- [x] H1 on every page
- [ ] H2 on every listing page (currently missing)
- [x] H2-H6 hierarchy on detail pages (via card components)
- [ ] Category description text on category pages (missing — add 100-200 words)
- [ ] Related posts widget (missing)
- [ ] Cross-type links (job → result → admit for same exam, missing)

### Structured Data

- [x] JobPosting schema on job detail pages
- [x] LearningResource on result pages
- [x] Event on admit card pages
- [x] Course on syllabus pages
- [x] FAQPage when FAQ content present
- [x] BreadcrumbList on all detail pages
- [x] WebSite + Organization on homepage
- [x] CollectionPage on category listings
- [ ] HiringOrganization sameAs for major orgs (pending)
- [ ] AggregateRating (not applicable currently)

### Content Quality

- [x] 400+ words per detail page
- [x] Structured frontmatter (dates, fees, vacancies, how-to-apply)
- [x] Unique slugs (no duplicates)
- [ ] All shortDescriptions 120-200 chars (audit needed)
- [ ] No numeric IDs as titles (ongoing — fixed at source, reprocess old files)
- [ ] Keywords/tags field in frontmatter (pending addition)

### Indexing

- [x] All content pages are indexable (index: true)
- [x] `/go/` redirect is noindexed
- [ ] Search page in sitemap (missing — add to app/sitemap.ts)
- [ ] State pages verified to exist (check /app/state/)
- [ ] 404 page properly configured

---

## 20. IMMEDIATE ACTION ITEMS

Ordered by impact:

### This Week (Highest Impact)

1. **Add metadata to /search/ page** (5 min)
   - File: `app/search/page.tsx`
   - Add `export const metadata` with title + description + canonical

2. **Add /search/ to sitemap** (5 min)
   - File: `app/sitemap.ts`
   - Add to staticRoutes array

3. **Add H2 to all listing pages** (1-2 hours)
   - Files: `app/latest-jobs/page.tsx`, `app/jobs/[category]/page.tsx`, `app/results/page.tsx`, `app/admit-cards/page.tsx`
   - Add `<h2>` with keyword phrase after `<h1>`

4. **Add category description text** (2 hours)
   - Create a `lib/category-descriptions.ts` file with 100-200 word descriptions per category
   - Render in `app/jobs/[category]/page.tsx` above the jobs table

5. **Fill in GSC verification tag** (5 min)
   - File: `app/layout.tsx` line 27
   - Add actual Google Search Console verification meta tag

6. **Add HiringOrganization sameAs URLs** (30 min)
   - File: `lib/seo.ts`
   - Add major org URL map and use in buildJobJsonLd()

### Next 2 Weeks

7. **Fix image optimization** (2 hours)
   - Change `images: { unoptimized: false }` in `next.config.ts`
   - Test that build still works with Cloudflare Pages static export

8. **Lazy-load heavy components** (2 hours)
   - Wrap `LiveTicker`, `AnimatedSection`, and any Three.js components in `dynamic(() => import(...), { ssr: false })`

9. **Add Related Posts widget** (3 hours)
   - On detail pages: show 3-5 posts from same category
   - Preferably active jobs only; fallback to recent

10. **Implement seo_rewriter guard** (30 min)
    - Skip files with numeric/short titles
    - Skip files with no sourceUrl

11. **Add cross-type links** (4 hours)
    - On job pages: link to corresponding result/admit/syllabus if same exam exists
    - Query by matching title words + dept + year

### Month 2

12. **State pages audit** — verify `/app/state/[state]/page.tsx` exists with correct metadata
13. **RSS feed** — use existing `rss` package to generate `/feed.xml`
14. **Keywords field in frontmatter** — add `keywords: []` array and use in meta tags
15. **Location-based pages** — `/jobs/location/[city]/` for major cities (Delhi, Mumbai, etc.)
16. **Topic clusters** — `/exams/[exam-slug]/` hub pages linking job → result → syllabus

---

## APPENDIX: KEY FILES REFERENCE

| File | Purpose |
|------|---------|
| `scraper/sarkari_scraper.py` | Main scraper orchestrator |
| `scraper/seen_items.json` | Deduplication state |
| `scraper/mdx_generator.py` | MDX file writer |
| `scraper/detail_parser/base_parser.py` | Abstract parser base |
| `scraper/detail_parser/sarkariresult.py` | SarkariResult parser |
| `scraper/detail_parser/freejobalert.py` | FreeJobAlert parser |
| `scraper/detail_parser/sarkariexam.py` | SarkariExam parser |
| `scraper/detail_parser/models.py` | DetailData dataclass |
| `scraper/detail_parser/utils.py` | Shared parser utilities |
| `agent/tasks/seo_rewriter.py` | SEO content rewriter agent |
| `lib/content.ts` | Content reading/parsing functions |
| `lib/seo.ts` | SEO metadata + JSON-LD builders |
| `lib/types.ts` | TypeScript type definitions |
| `app/sitemap.ts` | Dynamic sitemap generation |
| `app/layout.tsx` | Root layout with global metadata |
| `public/robots.txt` | Crawler directives |
| `.github/workflows/daily-scraper.yml` | GitHub Actions scraper config |
| `CLAUDE.md` | Claude Code operating rules |
| `FOUNDATION.md` | **This file** — complete site foundation |

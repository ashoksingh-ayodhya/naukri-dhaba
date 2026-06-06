# Naukri Dhaba — Agent Knowledge Base

This file is the single source of truth the agent reads and enforces on every run.
All rules here are NON-NEGOTIABLE and must be applied continuously.

---

## 1. GOALS

### Content Targets
| Type | Target | Date Range |
|------|--------|-----------|
| Jobs | 3,000+ | 2023-01-01 to present |
| Results | 2,000+ | 2023-01-01 to present |
| Admit Cards | 1,500+ | 2023-01-01 to present |

Source: sarkariresult.com (scrape all content from 2023 onward, rewrite branding).

### SEO Targets
- Zero "Sarkari Result" branding in any page content (except `sourceUrl` field)
- Unique 200+ word `shortDescription` per job (not scraped copy — generated from data fields)
- Every page passes Google Rich Results Test
- Every page indexed in Google with appropriate rich result type

---

## 2. SEO RULES

### Meta Title (≤ 60 characters)
Format: `{Job Name} {Year} Apply Online | Naukri Dhaba`
- Primary keyword must be in the title
- Year must appear

### Meta Description (≤ 155 characters)
Must include: org name + vacancy count + last date
Example: `UPSC NDA 1 2026: 395 vacancies. Apply 11 Jan – 04 Feb 2026. Age 16.5–19.5 years. 10+2 pass eligible. Check notification at naukridhaba.in.`

### Content Rules
- `shortDescription`: 200–250 words, keyword density 2–3%, unique per job
- `howToApply`: 8-step guide branded as Naukri Dhaba (not sarkariresult)
- MDX body: lead paragraph (keyword ×3), key details table, eligibility section, numbered steps, 5-question FAQ
- Focus keyword: `{Org} {PostName} Recruitment {Year}` — appears in title, description, first paragraph, H2 headings

### Internal Linking
- Category listing pages link to all jobs
- Homepage links to latest 10 jobs
- Detail pages have breadcrumb (BreadcrumbList schema)

---

## 3. SCHEMA MARKUP REQUIREMENTS

### Required: `buildJobJsonLd()` — JobPosting schema
Applied to: `app/jobs/[category]/[slug]/page.tsx`

**Required fields** (all must be present in JSON-LD output):
```
@type: "JobPosting"
title: fm.title
description: (generated from frontmatter fields)
url: canonical URL
datePosted: ISO date (from publishedAt or updatedAt)
validThrough: ISO datetime (from lastDate)
employmentType: "FULL_TIME"
industry: "Government"
occupationalCategory: "Government Services"
hiringOrganization:
  @type: "Organization"
  name: fm.organization || fm.dept
  sameAs: fm.officialWebsite || google search URL
jobLocation:
  @type: "Place"
  address:
    @type: "PostalAddress"
    addressCountry: "IN"
    addressRegion: "India"
applicantLocationRequirements:
  @type: "Country"
  name: "India"
totalJobOpenings: (from totalPosts, if present)
baseSalary:
  @type: "MonetaryAmount"
  currency: "INR"
  value:
    @type: "QuantitativeValue"
    minValue: (parsed from salary field)
    maxValue: (parsed from salary field)
    unitText: "MONTH"
educationRequirements:
  @type: "EducationalOccupationalCredential"
  credentialCategory: (mapped from qualification)
  competencyRequired: fm.qualification
identifier:
  @type: "PropertyValue"
  name: "Advertisement Number"
  value: fm.advertisementNo
directApply: false (if applyUrl present)
```

**Status:** ✅ Implemented in `lib/seo.ts` → `buildJobJsonLd()`

---

### Required: `buildOrganizationJsonLd()` — Organization schema
Applied to: `app/layout.tsx` (site-wide)

**Required fields:**
```
@type: "Organization"
name: siteConfig.name
url: siteConfig.url
logo:
  @type: "ImageObject"   ← MUST be ImageObject, NOT a bare URL string
  url: siteConfig.url + "/logo.svg"
  width: 512
  height: 512
description: siteConfig.description
sameAs: [twitter, telegram]
```

**Known gap:** `logo` is currently a bare URL string — must be changed to ImageObject.
**Fix target:** `lib/seo.ts` → `buildOrganizationJsonLd()`

---

### Required: `buildResultJsonLd()` — NewsArticle schema
Applied to: `app/results/[category]/[slug]/page.tsx`

**Required fields:**
```
@type: "NewsArticle"
headline: fm.title
description: (generated)
url: canonical URL
datePublished: ISO date
dateModified: ISO date (if updatedAt present)
publisher: { @type: "Organization", name: siteConfig.name, logo: { @type: "ImageObject", url: logoUrl } }
author: { @type: "Organization", name: siteConfig.name }
inLanguage: "en-IN"
isAccessibleForFree: true
```

**Status:** ✅ Implemented and wired (changed from LearningResource on 2026-05-07)

---

### Required: `buildAdmitJsonLd()` — NewsArticle schema
Applied to: `app/admit-cards/[category]/[slug]/page.tsx`

**Required fields:**
```
@type: "NewsArticle"
headline: fm.title
description: (generated)
url: canonical URL
datePublished: ISO date
dateModified: ISO date (if updatedAt present)
publisher: { @type: "Organization", name: siteConfig.name, logo: { @type: "ImageObject", url: logoUrl } }
author: { @type: "Organization", name: siteConfig.name }
inLanguage: "en-IN"
isAccessibleForFree: true
```

**Status:** ✅ Implemented and wired (changed from Event schema on 2026-05-07 — Event schema had required fields Google stopped supporting for admit cards)

---

### Required: `buildAnswerKeyJsonLd()` — LearningResource schema
Applied to: `app/answer-keys/[slug]/page.tsx`

**Required fields:**
```
@type: "LearningResource"
name: fm.title
description: (generated)
url: canonical URL
datePublished: ISO date
provider: { @type: "Organization", name: orgName }
educationalUse: "Answer Key"
inLanguage: "en-IN"
isAccessibleForFree: true
```

**Status:** ✅ Function exists in `lib/seo.ts`
**Known gap:** NOT wired into `app/answer-keys/[slug]/page.tsx` — only BreadcrumbList is there.
**Fix target:** Wire `buildAnswerKeyJsonLd` into the answer-key detail page.

---

### Required: `buildSyllabusJsonLd()` — Course schema
Applied to: `app/syllabus/[slug]/page.tsx`

**Required fields:**
```
@type: "Course"
name: fm.title
description: (generated)
url: canonical URL
datePublished: ISO date
provider: { @type: "Organization", name: orgName }
educationalLevel: "Government Exam Preparation"
inLanguage: "en-IN"
isAccessibleForFree: true
teaches: fm.qualification || "Government Exam Syllabus"   ← MISSING
hasCourseInstance:
  @type: "CourseInstance"
  courseMode: "online"
  instructor: { @type: "Organization", name: orgName }
```

**Known gaps:** `teaches` field is missing. Also NOT wired into page.
**Fix target:** Add `teaches` to `lib/seo.ts` → `buildSyllabusJsonLd()` AND wire into `app/syllabus/[slug]/page.tsx`.

---

### Required: `buildHowToJsonLd()` — HowTo schema *(replaces deprecated FAQPage)*
Applied to: `app/jobs/[category]/[slug]/page.tsx`

> ⚠️ **FAQPage schema was deprecated by Google on 2026-05-07** and no longer triggers
> rich results. Do NOT use `buildFaqJsonLd` or FAQPage anywhere on the site.

Job detail pages emit HowTo schema using the `fm.howToApply` steps array:
```tsx
{fm.howToApply && fm.howToApply.length > 0 && (
  <script type="application/ld+json"
    dangerouslySetInnerHTML={{ __html: JSON.stringify(
      buildHowToJsonLd(`How to Apply for ${fm.title}`, fm.howToApply)
    ) }} />
)}
```

**Status:** ✅ `buildHowToJsonLd` wired into job detail page (wired 2026-05-07)
**Do NOT revert** to `buildFaqJsonLd` or re-add FAQPage blocks.

---

### Required: `buildListingPageJsonLd()` — CollectionPage + ItemList schema
Applied to:
- `app/jobs/[category]/page.tsx`
- `app/results/[category]/page.tsx`
- `app/admit-cards/[category]/page.tsx`

**Required fields:**
```
@type: "CollectionPage"
name: page title
url: canonical URL
mainEntity:
  @type: "ItemList"
  itemListElement: (array of ListItem with position, name, url)
```

**Status:** Function exists in `lib/seo.ts`. NOT wired into any listing page.
**Fix target:** Wire into all three category listing pages.

---

### Required: `buildWebSiteJsonLd()` — WebSite schema
Applied to: homepage `app/page.tsx`
**Status:** ✅ Wired

### Required: `buildBreadcrumbJsonLd()` — BreadcrumbList schema
Applied to: ALL detail pages
**Status:** ✅ Wired on job, result, admit-card, answer-key, syllabus pages

---

## 4. SCHEMA IMPLEMENTATION STATUS

| Schema Type | lib/seo.ts | Wired in page |
|-------------|-----------|----------------|
| JobPosting | ✅ | ✅ job detail |
| NewsArticle (result) | ✅ | ✅ result detail |
| NewsArticle (admit card) | ✅ | ✅ admit-card detail |
| LearningResource (answer key) | ✅ | ❌ NOT wired |
| Course (syllabus) | ✅ (gap: teaches) | ❌ NOT wired |
| HowTo (job apply steps) | ✅ | ✅ job detail (uses fm.howToApply) |
| FAQPage | ~~DEPRECATED 2026-05-07~~ | ~~DO NOT USE~~ |
| CollectionPage+ItemList | ✅ | ❌ NOT wired into listing pages |
| WebSite | ✅ | ✅ homepage |
| Organization | ✅ (gap: logo ImageObject) | ✅ homepage |
| BreadcrumbList | ✅ | ✅ all detail pages |

---

## 5. AGENT TASK LIST (in execution order)

| # | Task | File | Priority |
|---|------|------|---------|
| 0 | SEO rewrite all MDX files | `tasks/seo_rewriter.py` | CRITICAL |
| 1 | Branding fast-pass | `agent.py` | CRITICAL |
| 2 | Freshness audit (alert if no content in 24h) | `agent.py` | HIGH |
| 3+4 | Clear seen_items + trigger scraper | `agent.py` | HIGH |
| 5 | SEO field audit (missing frontmatter keys) | `agent.py` | MEDIUM |
| 6 | Check Copilot PRs → test build → merge | `agent.py` | HIGH |
| 7 | Live schema audit (fetch real URLs) | `tasks/schema_audit.py` | HIGH |
| 8 | Fix schema code gaps in lib/seo.ts + wire pages | `tasks/fix_schema.py` | HIGH |
| 9 | Problem board report | `agent.py` | LOW |

---

## 6. ESCALATION RULES

When the agent cannot fix something itself:
1. Create a GitHub issue with title, body describing the problem, error details
2. Assign to GitHub Copilot
3. Track issue number in `agent/state.json` → `copilot_issues[]`
4. On next run: check if Copilot opened a PR, run `npm run build`, merge if green

**Escalate if:**
- seo_rewriter.py crashes
- No content commits in 24h
- Content count drops
- Schema gaps found by live audit
- 20+ MDX files missing required frontmatter fields

**Fix directly if:**
- Known code gaps in lib/seo.ts (logo ImageObject, endDate, teaches, etc.)
- Missing schema wiring in page.tsx files
- Branding text in MDX files

---

## 7. CONTENT FRESHNESS RULES

- If no new content commits in last 24 hours → escalate to Copilot + clear seen_items + trigger scraper
- If content count drops vs previous run → escalate to Copilot immediately
- `seen_items.json` is cleared when stale to force full re-scrape
- Scraper runs at: 7AM, 1PM, 7PM, 1AM IST
- Agent writes `scraper/run-now` to trigger immediate scrape

---

## 8. BRANDING RULES

**NEVER allowed in any content (except sourceUrl field):**
- "Sarkari Result" (any case)
- "sarkariresult.com"
- "www.sarkariresult.com"

**Replace with:**
- "Sarkari Result" → "Naukri Dhaba"
- "sarkariresult.com" → "naukridhaba.in"

---

## 9. CODE STRUCTURE

```
lib/seo.ts              — All JSON-LD builder functions
app/.../page.tsx        — Pages wire JSON-LD via <script type="application/ld+json">
agent/agent.py          — Main agent orchestrator
agent/tasks/
  seo_rewriter.py       — Rewrites MDX content (branding + SEO)
  schema_audit.py       — Live URL fetcher + schema comparator
  fix_schema.py         — Fixes code gaps in lib/seo.ts + wires pages
agent/knowledge.md      — THIS FILE — agent reads this on every relevant task
agent/problems.json     — Problem board with goals and open issues
agent/state.json        — Runtime state (counts, copilot_issues, etc.)
```

---

## 10. KNOWN OPEN GAPS (as of 2026-06-03)

These must be fixed by the agent's `fix_schema` task:

1. **`buildOrganizationJsonLd`** — `logo` is bare string, must be `ImageObject`
2. **`buildSyllabusJsonLd`** — missing `teaches` field
3. **`app/answer-keys/[slug]/page.tsx`** — `buildAnswerKeyJsonLd` not wired
4. **`app/syllabus/[slug]/page.tsx`** — `buildSyllabusJsonLd` not wired
5. **`app/jobs/[category]/page.tsx`** — `buildListingPageJsonLd` not wired
6. **`app/results/[category]/page.tsx`** — `buildListingPageJsonLd` not wired
7. **`app/admit-cards/[category]/page.tsx`** — `buildListingPageJsonLd` not wired

**RESOLVED (do not re-open):**
- ~~`buildAdmitJsonLd` endDate/image~~ — schema changed to NewsArticle on 2026-05-07
- ~~`buildFaqJsonLd` not wired~~ — FAQPage deprecated by Google on 2026-05-07; replaced by HowTo schema (`buildHowToJsonLd`) using `fm.howToApply`

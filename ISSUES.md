# ISSUES LOG — Naukri Dhaba Foundation Build

Agents write their findings here. Format per issue:
```
| ID | Severity (1-10) | File:Line | Description | Impact |
```

Scale: 1-2=cosmetic, 3-4=minor, 5=medium (highlight and move on), 6+=critical (must fix before merging)

Agents log severity ≤5 here and move on. Severity ≥6 must be fixed immediately.

---

## AGENT-1: Search Page Refactor (search metadata + state page)
_Status: DONE_

| ID | Severity | File:Line | Description | Impact |
|----|----------|-----------|-------------|--------|
| A1-1 | 3 | app/search/SearchClient.tsx:56 | H1 in SearchClient says "Search Government Jobs" but the server page also renders a Breadcrumb above the Suspense boundary — the H1 is inside the client component, so it won't appear until JS hydrates. Visitors on slow connections see no heading until JS loads. | Low — cosmetic flash issue, does not affect SEO since metadata is now on server component |
| A1-2 | 2 | app/state/[state]/page.tsx:22 | generateMetadata uses `new Date().getFullYear()` — on a static export this will embed the build-time year, not the current year at request time. After 2026 rolls over the titles will say 2026 until next redeploy. | Low — normal for static sites, just needs annual redeploy or ISR |
| A1-3 | 3 | app/about/page.tsx:12 | Privacy Policy link inside about page body points to `/contact/` but is labelled "Contact page" — fine. However the about page `metadata.description` mentions "Updated daily from official sources" which may be inaccurate if scraper is not running. | Low — copy issue only |

---

## AGENT-2: Listing Pages H2 + Category Descriptions
_Status: DONE_

| ID | Severity | File:Line | Description | Impact |
|----|----------|-----------|-------------|--------|
| A2-1 | 4 | app/jobs/[category]/page.tsx:64 | `posts.length` shows total count of all posts for the category, but does not distinguish active vs expired notifications. Users may see "52 notifications found" but many could be past their last date. | Medium — UX issue, misleads users on how many opportunities are actually available |
| A2-2 | 3 | app/results/[category]/page.tsx:47 | H1 uses `cat.fullName` (e.g. "Staff Selection Commission") while breadcrumb uses `cat.label` (e.g. "SSC") — inconsistency in how the category name is presented across the page. | Low — minor copy consistency issue |
| A2-3 | 3 | app/latest-jobs/page.tsx:17 | `getAllPosts("job")` on the latest-jobs page fetches ALL job posts with no pagination. With thousands of posts this could cause slow static builds and a very large HTML payload. | Low — performance concern at scale, not critical today |
| A2-4 | 2 | app/jobs/[category]/page.tsx | CATEGORY_DESCRIPTIONS only covers 12 slugs. If a new category is added to CATEGORIES config without a corresponding entry in category-descriptions.ts, the H2/description block silently disappears (conditional render). | Low — would be caught when reviewing new category pages |

---

## AGENT-3: SEO.ts — Structured Data Fixes
_Status: DONE_

| ID | Severity | File:Line | Description | Impact |
|----|----------|-----------|-------------|--------|
| A3-1 | 4 | lib/seo.ts:65 | `buildDescription()` — when `fm.organization` and `fm.dept` are both empty, the org sentence is omitted; if remaining parts also produce a description < 50 chars, the fallback text lacks an org name ("Government of India recruitment notification"). Silent but produces impersonal copy. | Low — only affects posts missing both org and dept fields |
| A3-2 | 3 | lib/seo.ts:156 | `MAJOR_ORG_URLS` lookup in `buildJobJsonLd` requires exact match on `fm.organization`. Partial names like "SSC", "RRB", or "SBI" will not match and fall through to `fm.officialWebsite`. Fuzzy/partial-match logic would improve coverage. | Low — well-known orgs must be spelled exactly in scraped frontmatter |
| A3-3 | 2 | lib/seo.ts:414 | `buildFaqJsonLd` accepts an empty array silently — callers that omit the `buildDefaultFaqs` fallback will emit a FAQPage schema with zero questions, which Google will ignore or flag as invalid. No crash, but wasteful markup. | Low — caller responsibility; a guard or JSDoc note would help |

---

## AGENT-4: Scraper Rewriter Guard
_Status: DONE_

| ID | Severity | File:Line | Description | Impact |
|----|----------|-----------|-------------|--------|
| A4-1 | 3 | agent/tasks/seo_rewriter.py | Rewriter had no guards — would run on files with numeric/short titles and produce hallucinated content like "52433 Recruitment 2026". Added skip guards and title-change block. | Fixed — guards now prevent hallucinated rewrites |
| A4-2 | 2 | scraper/seen_items.json | File stores a JSON list of hashed IDs (not a dict), so boolean-value validation is not applicable. Structure is internally consistent. | None — working as designed |
| A4-3 | 2 | scraper/detail_parser/base_parser.py:50-63 | Slug regeneration after numeric slug works correctly — _initial_slug_is_numeric captured before _extract_header, regenerated after. No fix needed. | None — working as designed |
| A4-4 | 2 | scraper/detail_parser/freejobalert.py:44 | _extract_header unconditionally overrides data.title when h1/h2 found (correct). Short-title threshold is > 10 chars, consistent with the rewriter guard. | None — working as designed |

---

## MAIN AGENT: Issue Fixes (done after all agents complete)
_Status: PENDING_

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
_Status: IN PROGRESS_

---

## AGENT-3: SEO.ts — Structured Data Fixes
_Status: IN PROGRESS_

---

## AGENT-4: Scraper Rewriter Guard
_Status: IN PROGRESS_

---

## MAIN AGENT: Issue Fixes (done after all agents complete)
_Status: PENDING_

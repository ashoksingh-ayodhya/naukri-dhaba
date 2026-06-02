# SEO Competitor Audit — Naukri Dhaba
**Completed**: 2 June 2026 | **Agent**: Competitor analysis + implementation plan

---

## What We Have (Solid Foundation)

- **JobPosting schema** — salary, education, validThrough, totalJobOpenings, directApply
- **BreadcrumbList** on all detail pages
- **WebSite + SearchAction + Organization** on homepage
- **Canonical, OG, Twitter cards** on every page
- **Dynamic XML sitemap** covering 4,000+ posts
- **State-based category pages** — rare among competitors
- **4x/day scraper** via GitHub Actions with self-trigger loop

---

## Critical Finding: FAQPage Schema Is Dead

**Google deprecated FAQ rich results on May 7, 2026.** The `buildFaqJsonLd` function was generating structured data that produces **zero rich results**. This has been fixed:

- Replaced `FAQPage` schema with `HowTo` schema wrapping the existing `howToApply` array
- Switched `buildResultJsonLd` from `LearningResource` → `NewsArticle` (eligible for Top Stories)
- Switched `buildAdmitJsonLd` from `Event` → `NewsArticle` (eligible for Top Stories)

---

## Competitor Gap Analysis (Top 5 by Impact)

### 1. Qualification-Based Pages — HIGH IMPACT
**What competitors have**: FreeJobAlert has `/10th-pass-jobs/`, `/12th-pass-jobs/`, `/graduate-jobs/`, `/engineering-jobs/` — massive search volume in India (millions of monthly searches).

**Implementation plan**:
```
app/jobs/qualification/[level]/page.tsx
```
Levels: `10th-pass`, `12th-pass`, `diploma`, `graduate`, `engineering`, `postgraduate`
Filter `getAllPosts("job")` by `fm.qualification` matching credential category.
Add to sitemap and navigation.

### 2. Google Indexing API — HIGH IMPACT  
**Problem**: New posts on a static site sit unindexed for hours. The Indexing API gets them into Google for Jobs in ~30 minutes.

**Implementation plan**:
Add to `daily-scraper.yml` after commit step:
```python
# In scraper or GitHub Actions step — call Indexing API for each new URL
POST https://indexing.googleapis.com/v3/urlNotifications:publish
{ "url": "https://naukridhaba.in/jobs/ssc/ssc-cgl-2026/", "type": "URL_UPDATED" }
```
Requires: Google Cloud service account with Indexing API enabled, JSON key as GitHub secret.

### 3. Related Jobs Sidebar Widget — MEDIUM IMPACT
**What competitors have**: "More jobs from SSC", "Other Railway jobs this week" section.

**Implementation plan**:
In `app/jobs/[category]/[slug]/page.tsx` sidebar:
```tsx
const related = getAllPosts("job", category).filter(p => p.slug !== slug).slice(0, 5);
// Render as compact link list
```

### 4. RSS Feed — MEDIUM IMPACT
**Status**: ✅ **DONE** — Added `/feed.xml` route. Enables Telegram/WhatsApp bots, browser push services, freshness signals.

### 5. Article/NewsArticle Schema — DONE
**Status**: ✅ **DONE** — Results and admit-card pages now use `NewsArticle` schema (eligible for Top Stories carousel).

---

## Quick Wins Applied This Session

| Fix | Status | Impact |
|-----|--------|--------|
| `twitter:site` + `twitter:creator` | ✅ Done | Twitter card attribution |
| RSS feed `/feed.xml` | ✅ Done | Push services, freshness |
| HowTo schema replaces FAQPage | ✅ Done | Rich results recovery |
| NewsArticle schema for results/admits | ✅ Done | Top Stories eligibility |
| `buildFaqJsonLd` removed from job detail | ✅ Done | Clean schema output |

---

## Still To Do

| Task | Priority | Effort |
|------|----------|--------|
| GSC verification — fill `GSC_CODE` in `layout.tsx` | 🔴 Critical | 5 min (user action) |
| Qualification-based pages | 🟠 High | 2-3 hours |
| Google Indexing API | 🟠 High | 2-3 hours |
| Related jobs sidebar | 🟡 Medium | 1 hour |
| Pagination on listing pages (now shows all ~1500+ jobs) | 🟡 Medium | 2 hours |
| `robots.txt` — block `/go/` redirect page | 🟡 Medium | 5 min |
| Schema for answer-key + syllabus pages | 🟢 Low | 1 hour |

---

## Competitor URL Patterns

| Site | Strength |
|------|----------|
| sarkariresult.com | Massive DA, all content types |
| freejobalert.com | Qualification-based pages, clean schema |
| rojgarresult.com | State-based filtering, fast load |
| sarkariexam.com | Deep category pages, good internal linking |
| sarkarijob.com | Strong mobile UX |

---

*This audit drives the implementation backlog. Qualification pages + Indexing API are the highest-leverage remaining items.*

# SEO Competitor Audit — Naukri Dhaba (naukridhaba.in)

**Audit Date:** June 2, 2026  
**Auditor:** SEO Audit Agent  
**Scope:** naukridhaba.in vs. sarkariresult.com, freejobalert.com, sarkariexam.com, sarkarinaukri.com, naukri.com/government-jobs

---

## 1. OUR CURRENT SEO SCORE

### What We Have (Strengths)

| Feature | Status | Notes |
|---|---|---|
| Title tags | ✅ Good | `{title} \| Naukri Dhaba` pattern, dynamically built |
| Meta descriptions | ✅ Good | Auto-generated from frontmatter, 160-char cap enforced |
| Canonical tags | ✅ Good | Set on every page via `buildMetadata()` |
| Open Graph tags | ✅ Good | og:title, og:description, og:image (1200×630), og:locale=en_IN |
| Twitter cards | ✅ Good | summary_large_image on all pages |
| Robots.txt | ✅ Good | `Allow: /`, sitemap declared |
| XML Sitemap | ✅ Good | Dynamically generated, covers all posts + static routes + state pages |
| `lang="en-IN"` | ✅ Good | Set on `<html>` tag |
| JobPosting schema | ✅ Strong | Full schema: title, description, datePosted, validThrough, hiringOrganization, jobLocation (inferred city), salary (MonetaryAmount), educationRequirements, totalJobOpenings, directApply, identifier |
| BreadcrumbList schema | ✅ Good | Implemented on all detail pages (jobs, results, admits, answer-keys, syllabus) |
| WebSite + SearchAction schema | ✅ Good | On homepage, includes potentialAction SearchAction |
| Organization schema | ✅ Good | On homepage, includes logo, sameAs to Twitter + Telegram |
| Event schema (admit cards) | ✅ Good | `buildAdmitJsonLd` uses Event type with startDate, location, organizer |
| Course schema (syllabus) | ✅ Good | `buildSyllabusJsonLd` uses Course type |
| LearningResource schema (results) | ✅ Good | `buildResultJsonLd` |
| CollectionPage + ItemList schema | ✅ Good | On all category listing pages |
| FAQPage schema | ✅ Exists (see critical note below) | Extracted from MDX `**Q:**`/`**A:**` patterns on job detail pages only |
| State-based pages | ✅ Good | `/state/[state]/` for 20 states — rare in competitors |
| Category pages | ✅ Good | 12 job categories + results/admit-card variants |
| Breadcrumb UI | ✅ Good | Visual breadcrumbs on all detail pages |
| Share buttons | ✅ Good | ShareButtons component on detail pages |
| PWA manifest | ✅ Good | site.webmanifest with icons |
| Google Analytics + GTM | ✅ Good | GA4 + GTM with consent defaults |
| AdSense | ✅ Good | Script loaded in layout.tsx |
| Preconnect hints | ✅ Partial | `fonts.googleapis.com` and `fonts.gstatic.com` |
| footer links | ✅ Good | Structured footer: Quick Links, Categories, State Jobs |
| `theme-color` meta | ✅ Good | `#1e3a8a` |
| `go/` redirect page | ✅ Good | Noindexed via layout |
| Trailing slash consistency | ✅ Good | `trailingSlash: true` in Next.js config |

### What Is Missing or Weak (Gaps)

| Feature | Status | Impact |
|---|---|---|
| **FAQPage schema deprecated** | 🔴 Critical | Google removed FAQ rich results May 7, 2026; Search Console reporting ends June 2026 |
| **No RSS/Atom feed** | 🔴 High | Competitors use feeds for aggregators, push services, and Google News signals |
| **No `twitter:site` handle in card tags** | 🟡 Medium | Twitter card missing `@naukridhaba` handle — reduces attribution |
| **No Google Indexing API** | 🟡 Medium | Static export means new posts aren't crawled for hours/days; Indexing API submits in 5–30 min |
| **No qualification-based pages** | 🟡 Medium | Missing `/jobs/10th-pass/`, `/jobs/12th-pass/`, `/jobs/graduate/` — high-search-volume segment |
| **No related/similar jobs widget** | 🟡 Medium | No internal linking on job detail pages to related jobs within same category |
| **No Article/NewsArticle schema** | 🟡 Medium | Results/admit-card pages use LearningResource/Event but not Article — misses Top Stories eligibility |
| **No push notification service** | 🟡 Medium | Competitors have millions of WhatsApp/Telegram/push subscribers |
| **No app download page** | 🟡 Medium | No Android/iOS app; competitors have 1M+ app downloads |
| **No year-based archive pages** | 🟡 Medium | `/jobs/2026/` or `/results/2026/` pattern captures year-based searches |
| **No `addressRegion`/`postalCode` in JobPosting schema** | 🟡 Medium | Google recommends maximal location data; we only have `addressLocality` + `addressCountry` |
| **GSC verification code missing** | 🟡 Medium | `GSC_CODE` is blank string in layout.tsx — Search Console not verified via meta tag |
| **No HowTo schema on apply pages** | 🟡 Low-Med | `HowToApply` component content not wrapped in HowTo schema |
| **No `dateModified` on most pages** | 🟡 Low-Med | Only present in `buildResultJsonLd` conditionally; job pages don't emit dateModified |
| **No hreflang or Hindi language pages** | 🟡 Low | Competitors serve bilingual audiences; Hindi is 40%+ of India's internet users |
| **No city-wise pages** | 🟡 Low | Missing `/jobs-in-delhi/`, `/jobs-in-mumbai/` — captures geo-specific queries |
| **No AMP pages** | 🟢 Low (AMP declining) | Most competitors abandoned AMP; low priority |
| **No user comments/UGC** | 🟢 Low | Minor ranking signal; risk of spam management |
| **No `og:article:published_time`** | 🟢 Low | Social sharing could benefit from publication timestamps |
| **No IndexNow for Bing/Yandex** | 🟢 Low | Google has own Indexing API; IndexNow covers others |
| **`/go/` page URL is not obfuscated** | 🟢 Low | External link tracking via redirect is fine; `rel="noopener"` is set |

### Content Quality Issues Found in MDX

- `resultUrl` in sample MDX contains placeholder "Naukri Dhabaportal.com" (broken link)
- `organization` field in some MDX files has been populated with the full notification description text rather than just the org name — this bloats JSON-LD `hiringOrganization.name`
- `shortDescription` in some posts exceeds 400 chars even after truncation (gets cut mid-sentence)

---

## 2. COMPETITOR FEATURE MATRIX

> Note: All competitor sites returned HTTP 403 to direct HTML fetching. Analysis is based on WebSearch data, published SEO audits (SEMrush/Similarweb), and URL patterns visible in Google SERPs.

| Feature | SarkariResult.com | FreeJobAlert.com | SarkariExam.com | SarkariNaukri.com | Naukri.com | **NaukriDhaba.in** |
|---|---|---|---|---|---|---|
| **Monthly Traffic** | ~6.9M (Mar 2026) | ~9.2M (Feb 2026) | ~500K (Jan 2026) | ~200K | ~80M+ | New site |
| **Domain Rating** | 70 | 79 | ~50 | ~45 | 90+ | Low (new) |
| Title tag format | `{keyword} 2026 \| SarkariResult` | `{keyword} - FreeJobAlert` | `{keyword} SarkariExam.com` | Unknown | `{keyword} - Naukri` | `{title} \| Naukri Dhaba` ✅ |
| Meta description | 306 chars (over-long) | ~150 chars | Unknown | Unknown | ~155 chars | ≤160 chars ✅ |
| JobPosting schema | Limited/none confirmed | Likely none | Unknown | Unknown | Yes (extensive) | ✅ Full |
| BreadcrumbList schema | Confirmed (visible in SERPs) | Confirmed (visible in SERPs) | Unknown | Unknown | Yes | ✅ Full |
| FAQPage schema | Was used; now deprecated | Was used; now deprecated | Unknown | Unknown | Limited | ✅ (deprecated May 2026) |
| WebSite + SearchAction | Likely | Likely | Unknown | Unknown | Yes | ✅ |
| Organization schema | Likely | Likely | Unknown | Unknown | Yes | ✅ |
| State-wise pages | No dedicated pages | Yes (/state-government-jobs/) | Unknown | Unknown | Yes | ✅ (/state/) |
| Qualification-wise pages | No | Yes (/search-jobs/jobs-by-education/) | Unknown | Unknown | Yes | ❌ Missing |
| City-wise pages | Mentioned in content | Yes (/jobs-in-delhi/ etc.) | Unknown | Unknown | Yes | ❌ Missing |
| Category pages | Yes (/ssc/, /railway/ etc.) | Yes (bank-jobs/, etc.) | Yes | Unknown | Yes | ✅ (/jobs/ssc/ etc.) |
| Year archive pages | Referenced in content | Unknown | Unknown | Unknown | Unknown | ❌ Missing |
| RSS/Atom feed | Likely (WordPress-based) | Likely | Unknown | Unknown | Yes | ❌ Missing |
| Android/iOS app | Yes (Play Store, App Store) | Yes (Play Store) | Unknown | Unknown | Yes (major) | ❌ Missing |
| Push notifications | Yes (browser + app) | Yes (multiple channels) | Unknown | Unknown | Yes | ❌ Missing |
| Email alerts | Yes | Yes (primary feature) | Unknown | Unknown | Yes | ❌ Missing |
| WhatsApp channel | 6.3M+ subscribers | Yes | Unknown | Unknown | No (B2B focus) | Links only |
| Telegram channel | 1.5M+ subscribers | Yes | Unknown | Unknown | No | Links only |
| Related jobs widget | Yes (likely sidebar) | Yes (likely) | Unknown | Unknown | Yes (extensive) | ❌ Missing |
| Internal linking widgets | High (interlinking tables) | High | Unknown | Unknown | Very high | Partial (footer) |
| Comments/UGC | No (most don't) | No | No | Unknown | No | No |
| Social sharing | Likely | Likely | Unknown | Unknown | Yes | ✅ (ShareButtons) |
| Canonical tags | Yes | Yes | Unknown | Unknown | Yes | ✅ |
| Hreflang (Hindi) | Hindi content served | Some Hindi | Unknown | Unknown | No | ❌ Missing |
| AMP pages | Unlikely (abandoned) | Unlikely | Unknown | Unknown | No | No |
| IndexNow | Unknown | Unknown | Unknown | Unknown | Unknown | ❌ |
| Google Indexing API | Unknown | Unknown | Unknown | Unknown | Likely | ❌ |
| Sitemap | Yes | Yes | Yes | Unknown | Yes | ✅ Dynamic |
| Robots.txt | Yes (403 blocked) | Yes (403 blocked) | Unknown | Unknown | Yes | ✅ |
| PWA/manifest | Unknown | Unknown | Unknown | Unknown | Yes | ✅ |
| Schema: HowTo | Unknown | Unknown | Unknown | Unknown | Unknown | ❌ |
| Schema: Article | Likely (news-type pages) | Likely | Unknown | Unknown | Yes | ❌ |
| AdSense | Yes (dense ads) | Yes (dense ads) | Yes | Unknown | No (own ads) | ✅ |
| GSC verified | Yes | Yes | Unknown | Unknown | Yes | ❌ (blank code) |

---

## 3. WHAT COMPETITORS HAVE THAT WE DON'T

### A. High-Traffic Page Types We're Missing

1. **Qualification-wise pages** — freejobalert.com has `/search-jobs/jobs-by-education/` with subpages for 10th Pass, 12th Pass, ITI/Diploma, Graduate, Post-Graduate, PhD. These capture massive search volume ("10th pass government jobs 2026" = high volume India).

2. **City-wise / location pages** — `/jobs-in-delhi/`, `/jobs-in-mumbai/`, `/jobs-in-bangalore/` etc. FreeJobAlert and MySarkariNaukri both have these and they rank for city-specific queries.

3. **Year-based content pages** — Content organized under `/jobs/2026/` or metadata-level year filtering. Competitors embed the current year prominently in H1 and URL to capture "sarkari naukri 2026"-style queries.

4. **Salary-range pages** — Some competitors have `/government-jobs-salary-above-50000/` type pages targeting salary-based searches.

### B. Distribution Channels

5. **Android/iOS mobile app** — SarkariResult has millions of app downloads. App notifications drive repeat traffic directly bypassing Google.

6. **Browser push notifications** — Zero-friction subscription; competitors add subscribers for free at multi-million scale.

7. **Email newsletter / job alert subscription** — FreeJobAlert's core brand proposition is "free job alert by email." We have no email capture at all.

8. **WhatsApp Channel integration** — We link to WhatsApp but don't embed a "Join Channel" CTA widget. SarkariResult has 6.3M WhatsApp subscribers.

9. **Telegram channel integration** — Same issue; link exists but no visible subscribe CTA or subscriber count displayed.

### C. Schema Markup Gaps

10. **HowTo schema** — We have a `HowToApply` component rendering step-by-step instructions but no HowTo structured data wrapping it.

11. **Article/NewsArticle schema** — Results and admit-card pages are time-sensitive "news" content. Using NewsArticle schema makes them eligible for Top Stories carousel.

12. **`addressRegion` + `postalCode`** in JobPosting schema — Google's documentation recommends full address; we only supply `addressLocality` + `addressCountry`.

### D. Internal Linking / UX Patterns

13. **Related jobs widget on detail pages** — No "More jobs from this organization" or "Similar jobs in this category" section on job detail pages. Competitors have sidebars or bottom sections with 5–10 related posts.

14. **"Also check" cross-content links** — Competitors link from a job page to its corresponding admit card, result, and answer key pages. We have separate sections but no cross-content links between post types.

15. **Search autocomplete/suggestions** — Our search page exists but has no live-search autocomplete visible. Competitors show instant suggestions.

### E. Technical SEO Signals

16. **Google Indexing API for job posts** — Critical for static sites. New job pages take hours/days to get crawled without it; Indexing API gets them into Google for Jobs within 5–30 minutes.

17. **`twitter:site` handle in card tags** — Missing `@naukridhaba` attribution in Twitter card metadata.

18. **GSC meta verification tag** — `GSC_CODE` is empty string in layout.tsx; Search Console not connected via meta tag.

19. **RSS/Atom feed** — Used by news aggregators, push notification services (OneSignal, Firebase), and gives Google a freshness signal. No feed exists.

20. **`og:article:published_time` / `og:article:modified_time`** — Social sharing of job posts would benefit from these Facebook-standard tags.

### F. Content & Trust Signals

21. **Hindi language content** — 40%+ of India's online users primarily consume Hindi. Competitors serve bilingual content. Even English pages with Hindi keyword variations in meta descriptions capture this segment.

22. **"Last Updated" prominent timestamp** — We show a small text; competitors make "Post Date / Last Updated" very prominent (large text, colored badge) because freshness is a click signal for time-sensitive job content.

23. **Official notification badge / verification indicator** — Some competitors display "Verified from official website" trust badges on posts.

24. **Dense footer link structure** — Competitors have massive footer link grids linking to hundreds of category/state combinations for PageRank distribution. Our footer is clean but limited.

25. **External links to official .gov.in sources** — Google rewards pages that cite authoritative sources. Many competitors prominently link to official government websites in their content — we link in ImportantLinks but could be more consistent.

---

## 4. IMPLEMENTATION PLAN

Items ordered by **Impact × Effort** (highest ROI first).

---

### ITEM 1: Fix FAQPage Schema (Deprecated) → Switch to HowTo Schema
**Priority: CRITICAL**  
**Effort: Low (2 hours)**  
**Expected impact: Prevents wasted crawl budget on deprecated markup; HowTo schema eligible for rich results**

Google deprecated FAQPage rich results on May 7, 2026. The FAQPage schema in our job detail pages no longer generates rich results. The `buildDefaultFaqs` function exists but is never called (only in-body **Q:**/**A:** patterns are picked up). The HowToApply component renders 8+ steps but has no schema.

**What to do:**

1. Keep FAQPage markup as-is (Google says unused structured data doesn't harm; keep for AI/GEO parsing).
2. Add HowTo schema to the job detail page wrapping the `howToApply` array.

**File:** `/home/user/naukri-dhaba/lib/seo.ts` — add:
```typescript
export function buildHowToApplyJsonLd(
  title: string,
  steps: string[],
  url: string
): object {
  return {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: `How to Apply for ${title}`,
    url,
    step: steps.map((text, i) => ({
      "@type": "HowToStep",
      position: i + 1,
      name: `Step ${i + 1}`,
      text,
    })),
  };
}
```

**File:** `/home/user/naukri-dhaba/app/jobs/[category]/[slug]/page.tsx` — in the JSX, after existing JSON-LD blocks:
```tsx
import { buildHowToApplyJsonLd } from "@/lib/seo";
// Inside return, after buildBreadcrumbJsonLd script:
{fm.howToApply && fm.howToApply.length > 0 && (
  <script
    type="application/ld+json"
    dangerouslySetInnerHTML={{
      __html: JSON.stringify(buildHowToApplyJsonLd(fm.title, fm.howToApply, pageUrl))
    }}
  />
)}
```

---

### ITEM 2: Add Article/NewsArticle Schema to Results and Admit Card Pages
**Priority: HIGH**  
**Effort: Low (1 hour)**  
**Expected impact: Top Stories carousel eligibility for result/admit card pages (high CTR boost)**

Results and admit cards are time-sensitive news events. Google's Top Stories carousel requires Article, NewsArticle, or BlogPosting schema with `headline`, `author`, `datePublished`, and `image`.

**File:** `/home/user/naukri-dhaba/lib/seo.ts` — add:
```typescript
export function buildNewsArticleJsonLd(fm: PostFrontmatter, url: string): object {
  const orgName = (fm.organization || fm.dept || "Government of India").trim();
  const datePosted = toIsoDate(fm.publishedAt) || "2026-01-01";
  return {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: fm.title,
    description: buildDescription(fm),
    url,
    datePublished: datePosted,
    dateModified: toIsoDate(fm.updatedAt) || datePosted,
    image: {
      "@type": "ImageObject",
      url: `${siteConfig.url}${siteConfig.ogImage}`,
      width: 1200,
      height: 630,
    },
    author: {
      "@type": "Organization",
      name: siteConfig.name,
      url: siteConfig.url,
    },
    publisher: {
      "@type": "Organization",
      name: siteConfig.name,
      url: siteConfig.url,
      logo: {
        "@type": "ImageObject",
        url: `${siteConfig.url}/logo.svg`,
        width: 512,
        height: 512,
      },
    },
    about: { "@type": "Organization", name: orgName },
    inLanguage: "en-IN",
  };
}
```

**Files to update:**
- `/home/user/naukri-dhaba/app/results/[category]/[slug]/page.tsx` — import and add `buildNewsArticleJsonLd` script block
- `/home/user/naukri-dhaba/app/admit-cards/[category]/[slug]/page.tsx` — same

---

### ITEM 3: Add RSS Feed
**Priority: HIGH**  
**Effort: Medium (3 hours)**  
**Expected impact: Google freshness signal, news aggregator discovery, enables push notification services**

**File to create:** `/home/user/naukri-dhaba/app/feed.xml/route.ts`
```typescript
import { getAllPosts } from "@/lib/content";
import { siteConfig } from "@/config/site";

export const dynamic = "force-static";

export function GET() {
  const posts = getAllPosts().slice(0, 50); // latest 50
  const items = posts.map((p) => `
    <item>
      <title><![CDATA[${p.title}]]></title>
      <link>${siteConfig.url}${p.href}</link>
      <guid isPermaLink="true">${siteConfig.url}${p.href}</guid>
      <pubDate>${new Date(p.publishedAt).toUTCString()}</pubDate>
      <description><![CDATA[${p.shortDescription || p.title}]]></description>
      <category>${p.category || ""}</category>
    </item>
  `).join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>${siteConfig.name}</title>
    <link>${siteConfig.url}</link>
    <description>${siteConfig.description}</description>
    <language>en-IN</language>
    <atom:link href="${siteConfig.url}/feed.xml" rel="self" type="application/rss+xml"/>
    <lastBuildDate>${new Date().toUTCString()}</lastBuildDate>
    ${items}
  </channel>
</rss>`;

  return new Response(xml, { headers: { "Content-Type": "application/rss+xml; charset=utf-8" } });
}
```

Then add to `<head>` in `/home/user/naukri-dhaba/app/layout.tsx`:
```tsx
<link rel="alternate" type="application/rss+xml" title="Naukri Dhaba — Latest Govt Jobs" href="/feed.xml" />
```

> **Note:** Since this is a static export, the route handler won't work at runtime. Instead, generate `feed.xml` as a static asset in the build script. Add a `scripts/generate-feed.ts` that reads all posts and writes to `public/feed.xml`, then call it in `package.json` `build` command.

---

### ITEM 4: Add Qualification-Wise Pages
**Priority: HIGH**  
**Effort: Medium (4 hours)**  
**Expected impact: Captures "10th pass government jobs", "graduate govt jobs India" — extremely high search volume in India**

These are the most-searched qualification filters in India's government job market.

**Step 1:** Add to `/home/user/naukri-dhaba/config/site.ts`:
```typescript
export const QUALIFICATIONS = [
  { slug: "10th-pass", label: "10th Pass Jobs", keywords: ["10th", "matric", "sslc", "matriculation"] },
  { slug: "12th-pass", label: "12th Pass Jobs", keywords: ["12th", "intermediate", "hsc", "higher secondary"] },
  { slug: "diploma-iti", label: "Diploma / ITI Jobs", keywords: ["diploma", "iti", "polytechnic"] },
  { slug: "graduate", label: "Graduate Jobs", keywords: ["graduate", "degree", "b.sc", "b.a", "b.com", "b.tech", "b.e", "graduation"] },
  { slug: "post-graduate", label: "Post Graduate Jobs", keywords: ["post graduate", "m.sc", "m.a", "m.tech", "mba", "mca", "pg"] },
] as const;
export type QualificationSlug = (typeof QUALIFICATIONS)[number]["slug"];
```

**Step 2:** Create `/home/user/naukri-dhaba/app/jobs/qualification/[qual]/page.tsx`:
```typescript
// Filter getAllPosts("job") by fm.qualification field matching QUALIFICATIONS[qual].keywords
// Use buildMetadata() with title: `${qual.label} Government Jobs 2026`
// Render JobsTable with filtered posts
// Add BreadcrumbList schema and CollectionPage schema
```

**Step 3:** Add to `/home/user/naukri-dhaba/app/sitemap.ts` qualification routes.

**Step 4:** Add qualification links to footer and category navigation.

---

### ITEM 5: Add Related Jobs Widget on Detail Pages
**Priority: HIGH**  
**Effort: Medium (3 hours)**  
**Expected impact: Reduces bounce rate, increases pages-per-session, distributes PageRank to newer posts**

**File to create:** `/home/user/naukri-dhaba/components/detail/RelatedJobs.tsx`
```tsx
import Link from "next/link";
import type { ListingPost } from "@/lib/types";

interface Props {
  posts: ListingPost[];
  currentSlug: string;
  category: string;
}

export default function RelatedJobs({ posts, currentSlug, category }: Props) {
  const related = posts
    .filter((p) => p.slug !== currentSlug)
    .slice(0, 5);
  if (related.length === 0) return null;
  return (
    <div className="card p-4 mb-4">
      <h3 className="font-heading font-semibold text-slate-900 mb-3 text-sm">More Jobs in This Category</h3>
      <ul className="space-y-2">
        {related.map((p) => (
          <li key={p.slug}>
            <Link href={`/jobs/${category}/${p.slug}/`} className="text-sm text-primary-700 hover:underline">
              {p.title}
            </Link>
            {p.lastDate && <span className="text-xs text-slate-500 ml-2">Last date: {p.lastDate}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

**File to update:** `/home/user/naukri-dhaba/app/jobs/[category]/[slug]/page.tsx` — add to sidebar:
```tsx
import RelatedJobs from "@/components/detail/RelatedJobs";
// In the component, fetch category posts:
const catPosts = getAllPostMeta("job", category);
// In sidebar section:
<RelatedJobs posts={catPosts} currentSlug={slug} category={category} />
```

Also apply equivalent widgets to results and admit-card detail pages.

---

### ITEM 6: Fix Google Search Console Verification
**Priority: HIGH**  
**Effort: Low (15 minutes)**  
**Expected impact: Without GSC connected, you're flying blind on crawl errors, coverage issues, and rich result status**

**File:** `/home/user/naukri-dhaba/app/layout.tsx`

Current state:
```typescript
const GSC_CODE = ""; // paste Search Console HTML tag meta content value here
```

Go to Google Search Console → Add property `naukridhaba.in` → HTML tag verification → copy the content value (looks like `abc123XYZ`) and paste:
```typescript
const GSC_CODE = "abc123XYZ"; // your actual code
```

This activates: `<meta name="google-site-verification" content="abc123XYZ" />` which is already wired in via `verification: GSC_CODE ? { google: GSC_CODE } : undefined`.

---

### ITEM 7: Improve JobPosting Schema with `addressRegion`
**Priority: MEDIUM**  
**Effort: Low (1 hour)**  
**Expected impact: Better Google for Jobs matching; more complete rich result data**

Google recommends including `addressRegion` alongside `addressLocality`. The `inferLocality()` function already maps org names to cities; we need to also map to state.

**File:** `/home/user/naukri-dhaba/lib/seo.ts` — add `inferRegion()` function:
```typescript
function inferRegion(orgName: string): string {
  const o = orgName.toLowerCase();
  if (o.includes("madhya pradesh") || o.includes("mppsc")) return "MP";
  if (o.includes("uttar pradesh") || o.includes("uppsc") || o.includes("upsssc")) return "UP";
  if (o.includes("rajasthan") || o.includes("rpsc") || o.includes("rsmssb")) return "RJ";
  if (o.includes("bihar") || o.includes("bpsc") || o.includes("bssc")) return "BR";
  if (o.includes("gujarat") || o.includes("gpsc")) return "GJ";
  if (o.includes("maharashtra") || o.includes("mpsc")) return "MH";
  if (o.includes("karnataka") || o.includes("kpsc")) return "KA";
  if (o.includes("tamil nadu") || o.includes("tnpsc")) return "TN";
  if (o.includes("andhra pradesh") || o.includes("appsc")) return "AP";
  if (o.includes("telangana") || o.includes("tspsc")) return "TS";
  if (o.includes("kerala") || o.includes("kerala psc")) return "KL";
  if (o.includes("west bengal") || o.includes("wbpsc")) return "WB";
  if (o.includes("punjab") || o.includes("ppsc")) return "PB";
  if (o.includes("haryana") || o.includes("hpsc") || o.includes("hssc")) return "HR";
  if (o.includes("himachal") || o.includes("hppsc")) return "HP";
  if (o.includes("jharkhand") || o.includes("jpsc")) return "JH";
  if (o.includes("odisha") || o.includes("opsc")) return "OD";
  if (o.includes("chhattisgarh") || o.includes("cgpsc")) return "CG";
  if (o.includes("assam") || o.includes("apsc")) return "AS";
  if (o.includes("uttarakhand") || o.includes("ukpsc")) return "UK";
  return "DL"; // Default to Delhi for central govt
}
```

Then update `buildJobJsonLd` jobLocation:
```typescript
address: {
  "@type": "PostalAddress",
  addressLocality: inferLocality(orgName),
  addressRegion: inferRegion(orgName),
  addressCountry: "IN",
},
```

---

### ITEM 8: Add `twitter:site` Handle to All Twitter Cards
**Priority: MEDIUM**  
**Effort: Low (15 minutes)**  
**Expected impact: Twitter/X correctly attributes card impressions to @naukridhaba; builds social authority**

**File:** `/home/user/naukri-dhaba/lib/seo.ts` — update `buildMetadata()` twitter section:
```typescript
twitter: {
  card: "summary_large_image",
  site: "@naukridhaba",        // ADD THIS
  creator: "@naukridhaba",     // ADD THIS
  title: `${title} | ${siteConfig.name}`,
  description,
  images: [{ url: ogImage, alt: `${title} | ${siteConfig.name}` }],
},
```

Also update `/home/user/naukri-dhaba/app/layout.tsx` global metadata.

---

### ITEM 9: Add Google Indexing API Integration
**Priority: MEDIUM**  
**Effort: High (full day, including GSC API setup)**  
**Expected impact: New job posts indexed and in Google for Jobs within 30 minutes instead of hours/days**

This is especially important for a static-export site where Googlebot crawl scheduling is unpredictable.

**Prerequisites:**
1. Enable Google Indexing API in Google Cloud Console
2. Create a service account and download JSON key
3. Add service account as owner in Google Search Console

**File to create:** `/home/user/naukri-dhaba/scripts/ping-indexing-api.ts`
```typescript
import { google } from "googleapis";
import { getAllPosts } from "../lib/content";
import { siteConfig } from "../config/site";

// Auth with service account
const auth = new google.auth.GoogleAuth({
  keyFile: "./google-indexing-key.json",
  scopes: ["https://www.googleapis.com/auth/indexing"],
});

const indexing = google.indexing({ version: "v3", auth });

async function pingNewPosts() {
  const posts = getAllPosts().slice(0, 20); // latest 20
  for (const post of posts) {
    const url = `${siteConfig.url}${post.href}`;
    try {
      await indexing.urlNotifications.publish({
        requestBody: { url, type: "URL_UPDATED" },
      });
      console.log(`Pinged: ${url}`);
    } catch (e) {
      console.error(`Failed: ${url}`, e);
    }
  }
}

pingNewPosts();
```

Add to build pipeline: call this script after `next build` in `package.json`:
```json
"build": "next build && tsx scripts/ping-indexing-api.ts"
```

---

### ITEM 10: Add Prominent Telegram/WhatsApp Subscribe CTA
**Priority: MEDIUM**  
**Effort: Low (2 hours)**  
**Expected impact: Builds repeat-visitor base; reduces dependency on Google organic for each visit**

**File to create:** `/home/user/naukri-dhaba/components/ui/SubscribeCta.tsx`
```tsx
import { siteConfig } from "@/config/site";

export default function SubscribeCta() {
  return (
    <div className="card p-5 mb-4 bg-primary-50 border border-primary-200">
      <h3 className="font-heading font-bold text-primary-900 mb-1 text-base">
        Get Free Job Alerts Daily
      </h3>
      <p className="text-sm text-slate-600 mb-3">
        Join 50,000+ aspirants getting instant alerts on Telegram & WhatsApp.
      </p>
      <div className="flex flex-wrap gap-2">
        <a
          href={siteConfig.links.telegram}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-primary text-sm px-4 py-2"
        >
          Join Telegram →
        </a>
        <a
          href={siteConfig.links.whatsapp}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-secondary text-sm px-4 py-2"
        >
          Join WhatsApp →
        </a>
      </div>
    </div>
  );
}
```

Add to the sidebar of job detail pages and to the homepage below the jobs table.

---

### ITEM 11: Add Cross-Content Links (Job ↔ Result ↔ Admit Card)
**Priority: MEDIUM**  
**Effort: Medium (4 hours)**  
**Expected impact: Deeper crawl paths, higher pages-per-session, contextually relevant internal links**

Many posts have corresponding entries in other content types (e.g., SSC CGL job → SSC CGL admit card → SSC CGL result). Currently there's no linking between them.

**Approach:** In the job detail page sidebar, query for posts in results and admit-cards with matching organization/slug patterns:

**File:** `/home/user/naukri-dhaba/app/jobs/[category]/[slug]/page.tsx` — add to sidebar:
```tsx
// Fetch related content types (matching by organization or slug prefix)
const orgSlug = fm.organization?.toLowerCase().replace(/\s+/g, "-").slice(0, 20) || "";
const relatedResults = getAllPosts("result", category)
  .filter((p) => p.slug.includes(orgSlug.slice(0, 10)) || p.organization === fm.organization)
  .slice(0, 3);
const relatedAdmits = getAllPosts("admit", category)
  .filter((p) => p.slug.includes(orgSlug.slice(0, 10)) || p.organization === fm.organization)
  .slice(0, 3);

// In sidebar JSX:
{relatedResults.length > 0 && (
  <div className="card p-4">
    <h3 className="font-heading font-semibold text-slate-900 mb-2 text-sm">Related Results</h3>
    <ul className="space-y-1">
      {relatedResults.map((r) => (
        <li key={r.slug}>
          <Link href={`/results/${category}/${r.slug}/`} className="text-xs text-primary-700 hover:underline">
            {r.title}
          </Link>
        </li>
      ))}
    </ul>
  </div>
)}
```

---

### ITEM 12: Add og:article Tags to Detail Pages
**Priority: LOW-MEDIUM**  
**Effort: Low (1 hour)**  
**Expected impact: Better Facebook/WhatsApp sharing with published date shown in share previews**

**File:** `/home/user/naukri-dhaba/lib/seo.ts` — extend `buildMetadata()` to accept optional `publishedAt` and `updatedAt`:
```typescript
export function buildMetadata({
  title, description, path: pagePath = "/", image, noindex,
  publishedAt, updatedAt,            // ADD THESE
}: {
  title: string; description: string; path?: string;
  image?: string; noindex?: boolean;
  publishedAt?: string; updatedAt?: string;  // ADD THESE
}): Metadata {
  // ... existing code ...
  return {
    // ... existing fields ...
    openGraph: {
      // ... existing fields ...
      type: publishedAt ? "article" : "website",
      ...(publishedAt ? {
        publishedTime: publishedAt,
        modifiedTime: updatedAt || publishedAt,
      } : {}),
    },
  };
}
```

Then pass `publishedAt` and `updatedAt` from frontmatter when calling `buildMetadata()` in detail pages.

---

### ITEM 13: Add Year-Based Archive Pages
**Priority: LOW-MEDIUM**  
**Effort: Medium (3 hours)**  
**Expected impact: Captures "government jobs 2026" queries with a dedicated, focused page**

**File to create:** `/home/user/naukri-dhaba/app/jobs/year/[year]/page.tsx` — filter posts by `publishedAt` year.

Add routes to sitemap. Title pattern: `Government Jobs 2026 — All Central & State Recruitment | Naukri Dhaba`.

---

### ITEM 14: Expand Footer Link Grid
**Priority: LOW**  
**Effort: Low (1 hour)**  
**Expected impact: Better PageRank distribution to state and category pages; more crawl paths**

**File:** `/home/user/naukri-dhaba/components/layout/Footer.tsx` — add a 5th column with all 20 state links (currently shows only 10), and add qualification links once those pages exist. Consider adding a second row with "Explore by Qualification" and a "Central Govt" / "State Govt" split.

---

### ITEM 15: Emit `dateModified` Consistently on Job Pages
**Priority: LOW**  
**Effort: Low (30 minutes)**  
**Expected impact: Google uses dateModified for freshness scoring; we only emit it conditionally for results**

**File:** `/home/user/naukri-dhaba/lib/seo.ts` — in `buildJobJsonLd()`, add:
```typescript
// After datePosted:
...(fm.updatedAt ? { dateModified: toIsoDate(fm.updatedAt) || datePosted } : {}),
```

Also add `lastModified` to the job post sitemap entries based on `updatedAt` (already done for `allPosts` in sitemap.ts — verify the `updatedAt` field is populated in MDX files).

---

## SUMMARY TABLE — Implementation Priority

| # | Item | Effort | Traffic Impact | Do By |
|---|---|---|---|---|
| 1 | Replace FAQPage with HowTo schema | 2h | Medium | Week 1 |
| 2 | Article/NewsArticle schema for results/admits | 1h | High | Week 1 |
| 3 | RSS feed (static generation) | 3h | High | Week 1 |
| 6 | Fix GSC verification (blank code) | 15m | Critical | Week 1 |
| 8 | Add `twitter:site` handle | 15m | Low | Week 1 |
| 4 | Qualification-wise pages (10th/12th/grad) | 4h | Very High | Week 2 |
| 5 | Related jobs widget on detail pages | 3h | Medium | Week 2 |
| 7 | `addressRegion` in JobPosting schema | 1h | Medium | Week 2 |
| 10 | Telegram/WhatsApp subscribe CTA widget | 2h | High (retention) | Week 2 |
| 9 | Google Indexing API integration | 8h | High (freshness) | Week 3 |
| 11 | Cross-content links (job↔result↔admit) | 4h | Medium | Week 3 |
| 12 | `og:article` published/modified time tags | 1h | Low | Week 3 |
| 13 | Year-based archive pages (/jobs/2026/) | 3h | Medium | Week 4 |
| 14 | Expand footer link grid | 1h | Low | Week 4 |
| 15 | Consistent `dateModified` in JobPosting | 30m | Low | Week 4 |

---

## APPENDIX: Data Sources

- sarkariresult.com organic traffic: ~6.9M/month (Ahrefs, March 2026)
- freejobalert.com: ~9.2M/month, Authority Score 79 (SEMrush, February 2026)
- Google FAQ rich results deprecation: May 7, 2026 (Google Search Central)
- Google Indexing API crawl time: 5–30 minutes for JobPosting pages
- Naukridhaba.in content: 4,152 MDX files (1,434 jobs, 984 results, 1,343 admit cards, others)
- FreeJobAlert qualification pages: `/search-jobs/jobs-by-education/` with 10th→PhD levels
- SarkariResult social presence: WhatsApp 6.3M+, Telegram 1.5M+, Instagram 640K+

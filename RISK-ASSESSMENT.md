# Risk Assessment — Naukri Dhaba
**Date**: June 2026 | **Reviewed by**: Claude Code

---

## How to read this document

Each risk is rated on two axes:
- **Likelihood**: Low / Medium / High (how often could this happen)
- **Impact**: Low / Medium / High / Critical (how badly does it hurt if it does)

**Priority = Likelihood × Impact.** Fix Critical + High-impact risks first regardless of likelihood.

---

## 1. Infrastructure

### 1.1 GitHub Actions as Scraper Runtime
**What we do**: Run the Python scraper 4x/day via GitHub Actions. It writes MDX files, commits them to main, and pushes.

**Risks**:
| Risk | Likelihood | Impact | Notes |
|------|-----------|--------|-------|
| GitHub Actions outage | Low | High | Site stops getting new content. Scraper auto-retries via `repository_dispatch`, but if GitHub itself is down, nothing runs. |
| 80-min workflow timeout | Medium | Medium | Scraper hits timeout mid-run. Already handles partial runs — seen_items.json saves progress so next run continues from where it stopped. |
| Two scraper runs overlapping | Medium | Medium | `concurrency: group: scraper` prevents this — second run waits. But if both fire at same second, one may fail to push due to race on seen_items.json. No file locking exists. |
| GitHub Actions minutes quota | Low | Medium | Free tier: 2000 min/month. We use ~320 min/month (4 runs × 80 min × 30 days / 3 runs per day ≈ OK). If targets aren't met and self-trigger fires aggressively, could exceed quota. |

**Ideal approach**:
- Move scraper to **GCP Cloud Run** (scheduled via Cloud Scheduler). No timeout, no quota, different IPs, runs 24/7. GCP trial credits available (~₹94K).
- Keep GitHub Actions as backup trigger only.

---

### 1.2 Cloudflare Pages as Host
**What we do**: Static Next.js export deployed to Cloudflare Pages free tier.

**Risks**:
| Risk | Likelihood | Impact | Notes |
|------|-----------|--------|-------|
| Cloudflare Pages outage | Very Low | Critical | Site goes down globally. No fallback. Cloudflare has 99.9%+ uptime historically. |
| Free tier build limit (500/month) | High | High | We trigger a build on every scrape commit. 4 scrapes/day = 120 builds/month now, but self-triggering could spike this to 500+ quickly. Already happened once. |
| Build time explosion as content grows | High | High | Currently ~1500 MDX files. At 3000+, Next.js static generation reads every file at build time. Build could take 10+ min and hit Cloudflare's 20-min build timeout. |
| 20,000 file limit (Cloudflare free) | Medium | Critical | Free tier allows max 20,000 files per deployment. At 1500 posts × ~3 pages each = 4500 HTML files now. At 3000 posts = 9000 files. At 7000 posts, we hit the limit. |
| Malformed MDX breaks build | Medium | High | One bad frontmatter field causes `gray-matter` parse error → entire build fails → site reverts to last good deploy. |

**Ideal approach**:
- Add `[skip ci]` to all scraper commits that already have it (done).
- Upgrade to Cloudflare Pages Pro ($25/month) when build count approaches 500/month — removes the limit.
- Add MDX validation step in scraper before committing (check required fields: title, slug, type, category).
- Monitor file count. At 15,000 files, evaluate moving to Cloudflare Workers + R2 (no file limit).

---

### 1.3 Git Repo as Database
**What we do**: All 4000+ MDX content files live in the GitHub repo. Every post is a file.

**Risks**:
| Risk | Likelihood | Impact | Notes |
|------|-----------|--------|-------|
| Repo size grows unbounded | High | Medium | MDX files are text, so growth is slow (~1KB/file). At 10,000 posts = 10MB of content — fine for git. seen_items.json grows too; currently manageable. |
| Accidental `git push --force` wipes content | Low | Critical | Would destroy all scraped content. No `--force` protection on main branch currently. |
| Merge conflicts on concurrent scraper commits | Medium | Low | Handled by `-X ours` strategy — always keeps our version. Rarely causes data loss. |
| No search/filter at scale | High | High | All filtering is done in Next.js at build time. Client-side search loads all post titles into memory. At 10,000 posts, the search index JSON will be several MB. |

**Ideal approach**:
- Enable **branch protection on main**: require PR for direct pushes, but allow bot pushes via token. This prevents accidental force-push.
- Long-term: move to a proper database (Turso/SQLite, PlanetScale, or Supabase) when post count exceeds 5000. MDX stays for templates; metadata goes into DB.

---

## 2. Scraper

### 2.1 Source Site Changes
**What we do**: Scrape 5+ government job portals (SarkariResult, FreeJobAlert, SarkariExam, etc.) by parsing HTML structure.

**Risks**:
| Risk | Likelihood | Impact | Notes |
|------|-----------|--------|-------|
| Source site changes HTML structure | High | High | Any class/selector change breaks the parser silently — scraper runs but produces empty/wrong data. Can go unnoticed for days. |
| Source site blocks GitHub Actions IPs | High | High | Already happened. Handled via CF Worker proxy, but if CF Worker is also blocked, scraper stops entirely. |
| CF Worker proxy gets rate-limited | Medium | Medium | CF free tier: 100,000 requests/day. Each scraper run fetches ~200-500 pages. Well within limits. |
| Source site goes down | Low | Low | Only affects that one source. Other 4 sources still run. |
| Scraped content contains errors/garbage | Medium | Medium | Numeric-only titles, age limits as qualifications, junk data. Partially handled by seo_rewriter guards. Still produces some bad MDX. |

**Ideal approach**:
- Add **parser health checks**: after each scrape, assert that at least N new posts were found per source. If a source returns 0, send a GitHub issue alert.
- Add **content validation** before commit: check that `title.length > 10`, `slug` is non-numeric, `type` is valid.
- Diversify to 3+ proxy sources so if one is blocked, others work.

### 2.2 seen_items.json Poisoning
**What we do**: Store MD5 hashes of scraped URLs in a JSON list to avoid re-scraping.

**Risks**:
| Risk | Likelihood | Impact | Notes |
|------|-----------|--------|-------|
| Hash collision | Very Low | Low | MD5 truncated to 14 chars. Collision probability negligible at our scale. |
| File grows unbounded | Medium | Low | Each hash is ~20 bytes. At 100,000 entries = 2MB. Git handles this fine. |
| File corrupted during concurrent write | Medium | High | Two simultaneous scraper runs (if concurrency guard fails) both write seen_items.json → one overwrites the other → items re-scraped. No file locking. |
| Wrong items poisoned (pre-cutoff bug) | Low | Medium | Was fixed. MIN_POST_DATE guard prevents items before 2022-01-01 from being poisoned. |

**Ideal approach**:
- Add file locking (`fcntl.flock`) around seen_items.json read/write in the Python scraper.
- Long-term: replace with SQLite DB (`scraper/seen.db`) — atomic writes, concurrent-safe, faster lookup.

---

## 3. SEO & Content

### 3.1 Content Quality
**What we do**: Scrape structured data from gov job portals and generate MDX files. The SEO rewriter agent adds descriptions and removes branding.

**Risks**:
| Risk | Likelihood | Impact | Notes |
|------|-----------|--------|-------|
| Thin/duplicate content triggers Google penalty | Medium | Critical | If our descriptions are too similar to source sites, Google may sandbox us. The seo_rewriter adds unique descriptions but quality varies. |
| Outdated jobs (expired deadlines) remaining on site | High | Medium | We show "Closed" badge but don't remove expired jobs. Users landing on expired job pages = bad UX. May harm bounce rate signals. |
| Schema markup errors | Low | Medium | If `validThrough` format is wrong, Google discards the JobPosting rich result. Already fixed date parsing but new formats could break it. |
| AI-generated content detection | Medium | Medium | Google is getting better at detecting AI text. Our descriptions are AI-generated. Low risk currently for factual job data but could become an issue. |

**Ideal approach**:
- Add a **content freshness score** to each MDX: if `lastDate` is >6 months ago and `updatedAt` is >3 months ago, mark `noindex: true`. Keeps index clean.
- Run **schema validation** (Schema.org validator) on a sample of pages weekly in the health-check workflow.
- Focus SEO rewriter on factual differentiation (specific vacancy counts, state names, exact qualifications) rather than generic filler text.

### 3.2 Google Algorithm Changes
**What we do**: Currently ranking on long-tail government job queries.

**Risks**:
| Risk | Likelihood | Impact | Notes |
|------|-----------|--------|-------|
| Google HCU (Helpful Content Update) targets scraped sites | Medium | Critical | If Google decides our content is "not helpful enough," organic traffic drops 80%+. Happened to many job aggregators in 2023-2024. |
| FAQPage deprecation impact | Done | None | Already handled — replaced with HowTo schema. |
| Core Web Vitals failure | Medium | Medium | Listing pages were showing 1500+ rows — now paginated (30/page). But homepage loads all latest posts. Need to audit CWV scores. |

**Ideal approach**:
- Add **unique content** that competitors don't have: state-wise pages, qualification pages (done), salary range filters.
- Build **topical authority**: add exam preparation guides, syllabus summaries — content Google considers "helpful."
- Monitor GSC for manual actions weekly.

---

## 4. Security

### 4.1 Secrets & Credentials
**What we do**: Store CF Worker URL/secret and Google service account key as GitHub Secrets.

**Risks**:
| Risk | Likelihood | Impact | Notes |
|------|-----------|--------|-------|
| Service account JSON exposed in chat ⚠️ | **Already happened** | High | The full private key was shared in this Claude Code session. Should be rotated immediately. |
| CF_WORKER_SECRET leaked in logs | Low | Medium | GitHub Actions masks secrets in logs, but if accidentally echoed in a bash script, it could appear. |
| GitHub token misuse | Low | Medium | `GITHUB_TOKEN` used for scraper commits has write access to the repo. If compromised, attacker could push malicious content. |
| Cloudflare API token exposed | Low | High | Not currently stored — Cloudflare Pages deploys via GitHub integration (no API token needed). |

**Ideal approach**:
- **Rotate the Google service account key immediately** — the JSON was visible in this conversation. Go to GCP Console → Service Accounts → delete the old key → create a new one → update the GitHub Secret.
- Add secret scanning to the repo (GitHub already does this for common patterns, but custom secrets need `git-secrets` or similar).
- Principle of least privilege: service account should only have Indexing API scope, not broad Google Cloud access.

### 4.2 Content Injection
**What we do**: Scrape HTML from external sites and render it via MDX on our site.

**Risks**:
| Risk | Likelihood | Impact | Notes |
|------|-----------|--------|-------|
| Scraped content contains XSS payloads | Low | High | If a source site embeds `<script>` in job titles, and our MDX renderer doesn't escape it, visitors could be attacked. React escapes JSX by default — `dangerouslySetInnerHTML` is used only for structured data JSON-LD (low risk). |
| Scraped URLs redirect to malicious sites | Low | Medium | `applyUrl` and `notificationUrl` from scraped data link externally. If a source site is compromised, we could be routing users to phishing pages. |

**Ideal approach**:
- Sanitize all scraped text fields (strip HTML tags) before writing MDX. Already done in most parsers but audit `importantLinks` URLs.
- Add `rel="noopener noreferrer"` to all external links (already present in ImportantLinks component).
- Add a URL allowlist: only pass `applyUrl` values that match `*.gov.in`, `*.nic.in`, or known recruitment portals.

---

## 5. Revenue & Business

### 5.1 AdSense
**What we do**: Google AdSense ads displayed site-wide via GTM.

**Risks**:
| Risk | Likelihood | Impact | Notes |
|------|-----------|--------|-------|
| AdSense account suspended | Medium | Critical | Automated content/scraping can trigger AdSense policy violations. If account is suspended, all ad revenue stops immediately. |
| Low RPM on govt job content | High | Low | Government job content typically earns ₹10-50 RPM (very low). Need high traffic volume to generate meaningful revenue. |
| Ad blindness on government job audience | High | Medium | Job seekers are task-focused — they find the listing and leave. Low CTR on display ads. |

**Ideal approach**:
- Diversify revenue: add affiliate links to resume-building services, online course platforms (Unacademy, Testbook) for relevant exams.
- Add a **"Set Alert"** feature (email/WhatsApp notification for new jobs in a category) — this builds a subscriber list with long-term value beyond AdSense.
- Consider AdSense alternatives: Media.net, Ezoic (requires 10K+ monthly sessions).

---

## 6. Summary Risk Matrix

| Risk | Likelihood | Impact | Priority | Action |
|------|-----------|--------|----------|--------|
| Cloudflare 20K file limit | Medium | Critical | 🔴 P1 | Monitor file count; upgrade plan at 15K files |
| Google HCU penalty | Medium | Critical | 🔴 P1 | Add unique content, avoid thin pages |
| Service account key exposed | **Done** | High | 🔴 P1 | **Rotate key immediately** |
| Build count exceeds 500/month | High | High | 🟠 P2 | Ensure [skip ci] on all scraper commits |
| Parser breaks on source HTML change | High | High | 🟠 P2 | Add per-source health assertions |
| AdSense suspension | Medium | Critical | 🟠 P2 | Ensure content policy compliance |
| Scraper runs overlap / seen_items race | Medium | High | 🟠 P2 | Add file locking to scraper |
| Build time explosion at 3000+ posts | High | High | 🟠 P2 | Move to GCP Cloud Run, incremental builds |
| No branch protection on main | Medium | Critical | 🟡 P3 | Enable branch protection (allow bot pushes) |
| Client-side search index too large | High | Medium | 🟡 P3 | Add search result pagination |
| Expired jobs hurting UX | High | Medium | 🟡 P3 | Auto-noindex posts >6 months expired |
| CF Worker proxy blocked | Medium | Medium | 🟡 P3 | Add backup proxy (Hetzner VPS / GCP) |
| seen_items.json no file locking | Medium | Medium | 🟡 P3 | Add fcntl.flock or move to SQLite |

---

## 7. Immediate Actions (do this week)

1. **Rotate the Google service account key** — the JSON was exposed in chat. Takes 5 min in GCP Console.
2. **Monitor Cloudflare build count** — if approaching 400/month, upgrade to Pro or reduce self-trigger frequency.
3. **Add MDX validation to scraper** — reject commits where `title.length < 10` or `slug.isdigit()`.
4. **Check AdSense policy** — verify scraped-content site is compliant with current AdSense terms.

---

*This document should be reviewed monthly as the site grows. Key thresholds to watch: 15,000 Cloudflare files, 3,000 posts (build time), 400 GitHub Actions builds/month.*

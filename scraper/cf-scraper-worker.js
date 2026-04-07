/**
 * Naukri Dhaba — Cloudflare Worker Scraper
 *
 * Runs on Cloudflare Workers with Cron Triggers, replacing (or
 * complementing) the Python GitHub Actions scraper. This file is pure
 * JavaScript and deploys with `wrangler deploy`.
 *
 * WHY THIS EXISTS:
 *   The Python sarkari_scraper.py cannot run on Cloudflare Workers
 *   (Workers only support JavaScript / WebAssembly). This file provides
 *   the same functionality entirely in JavaScript.
 *
 * HOW TO DEPLOY:
 *   1. Install Wrangler: npm install -g wrangler
 *   2. Login:            wrangler login
 *   3. Create KV ns:     wrangler kv:namespace create SEEN_ITEMS
 *   4. Update wrangler.toml with the KV namespace ID from step 3
 *   5. Add secrets:
 *        wrangler secret put GITHUB_TOKEN
 *        wrangler secret put TRIGGER_SECRET    (optional, for manual HTTP triggers)
 *   6. Deploy:           wrangler deploy
 *
 * REQUIRED BINDINGS (set in wrangler.toml):
 *   KV namespace : SEEN_ITEMS     — tracks scraped item hashes
 *
 * REQUIRED SECRETS (set via `wrangler secret put`):
 *   GITHUB_TOKEN    — GitHub personal access token with `contents: write`
 *   TRIGGER_SECRET  — optional; protects the manual HTTP POST trigger
 *
 * OPTIONAL ENV VARS (set in wrangler.toml [vars]):
 *   GITHUB_OWNER    default: ashoksingh-ayodhya
 *   GITHUB_REPO     default: naukri-dhaba
 *   SITE_URL        default: https://naukridhaba.in
 *   SITE_NAME       default: Naukri Dhaba
 *   MAX_ITEMS_PER_RUN  default: 20  (limit per cron run to stay within CPU limits)
 *
 * CRON SCHEDULE:
 *   Configured in wrangler.toml — fires daily at 04:30 UTC (10:00 AM IST).
 */

// ──────────────────────────────────────────────────────────────────────────────
// CONFIGURATION
// ──────────────────────────────────────────────────────────────────────────────

const SOURCES = [
  {
    name: 'sarkariresult',
    base: 'https://www.sarkariresult.com',
    urls: {
      job:    'https://www.sarkariresult.com/latestjob.php',
      result: 'https://www.sarkariresult.com/result.php',
      admit:  'https://www.sarkariresult.com/admitcard.php',
    },
  },
];

const FETCH_HEADERS = {
  'User-Agent':      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
  'Accept':          'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
  'Cache-Control':   'no-cache',
};

const GITHUB_API = 'https://api.github.com';

// ──────────────────────────────────────────────────────────────────────────────
// WORKER ENTRY POINT
// ──────────────────────────────────────────────────────────────────────────────

export default {
  /** Cron trigger: fires on schedule defined in wrangler.toml */
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(runScraper(env));
  },

  /** HTTP trigger: POST to the worker URL to kick off a manual run */
  async fetch(request, env, ctx) {
    if (request.method === 'POST') {
      const provided = request.headers.get('X-Trigger-Secret') ?? '';
      const expected = env.TRIGGER_SECRET ?? '';
      if (expected && provided !== expected) {
        return new Response('Forbidden', { status: 403 });
      }
      ctx.waitUntil(runScraper(env));
      return jsonResponse({ status: 'started', message: 'Scraper triggered. Check Cloudflare logs.' });
    }
    // Health-check / info
    return new Response(
      'Naukri Dhaba Scraper Worker\n\nPOST to this URL with X-Trigger-Secret header to run manually.\nCheck wrangler.toml for cron schedule.',
      { status: 200, headers: { 'Content-Type': 'text/plain' } },
    );
  },
};

// ──────────────────────────────────────────────────────────────────────────────
// MAIN SCRAPER LOOP
// ──────────────────────────────────────────────────────────────────────────────

async function runScraper(env) {
  const cfg = getConfig(env);
  const stats = { jobs: 0, results: 0, admits: 0, skipped: 0 };
  let itemsProcessed = 0;

  console.log(`[NaukriDhaba] Scraper started — max ${cfg.maxItems} items per run`);

  for (const source of SOURCES) {
    for (const [pageType, listUrl] of Object.entries(source.urls)) {
      if (itemsProcessed >= cfg.maxItems) break;

      console.log(`[NaukriDhaba] Fetching ${pageType} listing: ${listUrl}`);
      const html = await fetchPage(listUrl);
      if (!html) {
        console.warn(`[NaukriDhaba] Could not fetch ${listUrl}`);
        continue;
      }

      const items = parseListing(html, pageType, source.base);
      console.log(`[NaukriDhaba]   Found ${items.length} items in ${pageType} listing`);

      for (const item of items) {
        if (itemsProcessed >= cfg.maxItems) break;

        const key = itemKey(item);
        const alreadySeen = await isSeen(key, env);
        if (alreadySeen) {
          stats.skipped++;
          continue;
        }

        // Fetch detail page
        const detailHtml = await fetchPage(item.detailUrl);
        if (!detailHtml) {
          console.warn(`[NaukriDhaba]   Could not fetch detail: ${item.detailUrl}`);
          continue;
        }

        const rich = parseDetail(detailHtml, item, source.base);

        // Generate HTML and push to GitHub
        const { path: filePath, html: pageHtml } = buildPage(rich, pageType, cfg);
        const pushed = await pushToGitHub(filePath, pageHtml, cfg, env);

        if (pushed) {
          await markSeen(key, env);
          if (pageType === 'job')    stats.jobs++;
          if (pageType === 'result') stats.results++;
          if (pageType === 'admit')  stats.admits++;
          console.log(`[NaukriDhaba]   ✓ Published: ${filePath}`);
        }

        itemsProcessed++;
        // Respectful delay between requests
        await sleep(1000);
      }
    }
  }

  const total = stats.jobs + stats.results + stats.admits;
  console.log(`[NaukriDhaba] Done — Jobs:${stats.jobs} Results:${stats.results} Admits:${stats.admits} Skipped:${stats.skipped}`);

  // Trigger post-processing workflow in GitHub Actions (updates listing pages,
  // state pages, and sitemap now that new pages have been pushed to the repo).
  if (total > 0) {
    await triggerPostProcessing(cfg, env, stats);
  }

  return { ...stats, total };
}

// ──────────────────────────────────────────────────────────────────────────────
// HTTP FETCH
// ──────────────────────────────────────────────────────────────────────────────

async function fetchPage(url, retries = 3) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const resp = await fetch(url, {
        headers: FETCH_HEADERS,
        redirect: 'follow',
        cf: { cacheTtl: 0, cacheEverything: false },
      });
      if (!resp.ok) {
        console.warn(`[NaukriDhaba] HTTP ${resp.status} for ${url} (attempt ${attempt})`);
        if (attempt < retries) await sleep(2000 * attempt);
        continue;
      }
      return await resp.text();
    } catch (err) {
      console.warn(`[NaukriDhaba] Fetch error for ${url}: ${err.message} (attempt ${attempt})`);
      if (attempt < retries) await sleep(2000 * attempt);
    }
  }
  return null;
}

// ──────────────────────────────────────────────────────────────────────────────
// LISTING PAGE PARSER
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Parse a sarkariresult.com listing page and return an array of items.
 * The listing pages use a <table> with <tr> rows containing:
 *   - 2-col: <td><a href="...">Title</a></td> <td>Date</td>
 *   - 3-col: <td>Dept</td> <td><a href="...">Title</a></td> <td>Date</td>
 */
function parseListing(html, pageType, sourceBase) {
  const items = [];

  // Match all <tr>...</tr> blocks (non-greedy, case-insensitive)
  const trPattern = /<tr[^>]*>([\s\S]*?)<\/tr>/gi;
  let trMatch;

  while ((trMatch = trPattern.exec(html)) !== null) {
    const rowHtml = trMatch[1];

    // Find all <td> cells in this row
    const tds = extractTds(rowHtml);
    if (tds.length < 1) continue;

    let title = '';
    let href  = '';
    let dept  = '';
    let dateStr = '';

    if (tds.length >= 3) {
      // 3-col: dept | title+link | date
      dept    = stripTags(tds[0]).trim();
      const linkData = extractLink(tds[1]);
      href  = linkData.href;
      title = linkData.text;
      dateStr = stripTags(tds[2]).trim();
    } else if (tds.length === 2) {
      // 2-col: title+link | date
      const linkData = extractLink(tds[0]);
      href  = linkData.href;
      title = linkData.text;
      dateStr = stripTags(tds[1]).trim();
      dept  = inferDept(title);
    } else if (tds.length === 1) {
      const linkData = extractLink(tds[0]);
      if (!linkData.href) continue;
      href  = linkData.href;
      title = linkData.text;
      const dm = /(\d{1,2}\/\d{1,2}\/\d{4})/.exec(stripTags(tds[0]));
      dateStr = dm ? dm[1] : '';
      dept  = inferDept(title);
    }

    title = decodeHtmlEntities(title).trim();
    if (!title || title.length < 8) continue;
    if (!href) continue;
    if (isNavTitle(title)) continue;
    if (!kindMatchesTitle(title, pageType)) continue;

    const detailUrl = toAbsoluteUrl(href, sourceBase);
    const parsedDate = parseDateStr(dateStr);
    // Skip items older than the previous year (dynamic cutoff so it stays current)
    const cutoffYear = new Date().getFullYear() - 1;
    if (parsedDate && parsedDate.getFullYear() < cutoffYear) continue;

    items.push({
      title,
      dept,
      date:      parsedDate,
      dateStr,
      detailUrl,
      sourceBase,
    });
  }

  return items;
}

// ──────────────────────────────────────────────────────────────────────────────
// DETAIL PAGE PARSER
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Parse a detail page and merge with listing item data.
 * Extracts: dates, fees, age, qualification, vacancies, CTA links.
 */
function parseDetail(html, item, sourceBase) {
  const rich = { ...item };

  // Extract text content (strip all HTML for field extraction)
  const textContent = stripTags(html).replace(/\s+/g, ' ');

  // Important dates
  rich.lastDate      = extractField(textContent, ['last date', 'last date to apply', 'closing date']) || '';
  rich.startDate     = extractField(textContent, ['start date', 'online start', 'application start']) || '';
  rich.resultDate    = extractField(textContent, ['result date', 'result expected']) || '';
  rich.examDate      = extractField(textContent, ['exam date', 'written exam date']) || '';
  rich.admitDate     = extractField(textContent, ['admit card date', 'admit card available', 'hall ticket']) || '';

  // Eligibility / details
  rich.vacancy       = extractField(textContent, ['total post', 'total vacancy', 'vacancies', 'total vacancies', 'no of posts', 'number of post']) || '';
  rich.qualification = extractField(textContent, ['qualification', 'educational qualification', 'education']) || '';
  rich.ageLimit      = extractField(textContent, ['age limit', 'age relaxation', 'upper age', 'minimum age']) || '';
  rich.salary        = extractField(textContent, ['salary', 'pay scale', 'pay band', 'stipend', 'remuneration']) || '';
  rich.fee           = extractField(textContent, ['application fee', 'registration fee', 'exam fee']) || '';

  // CTA links — extract from raw HTML, filter for official/gov domains
  rich.applyUrl        = extractOfficialLink(html, sourceBase, ['apply', 'online form', 'apply online']) || '';
  rich.notificationUrl = extractOfficialLink(html, sourceBase, ['notification', 'advertisement', 'official notice']) || '';
  rich.resultUrl       = extractOfficialLink(html, sourceBase, ['result', 'merit list', 'selection list']) || '';
  rich.admitUrl        = extractOfficialLink(html, sourceBase, ['admit card', 'hall ticket', 'call letter']) || '';

  return rich;
}

// ──────────────────────────────────────────────────────────────────────────────
// HTML PAGE BUILDER
// ──────────────────────────────────────────────────────────────────────────────

function buildPage(item, pageType, cfg) {
  const title = normalizeTitle(item.title);
  const dept  = item.dept || 'Government';
  const cat   = getCategory(dept);
  const slug  = slugify(title);

  let filePath, canon, pageHtml;

  if (pageType === 'job') {
    filePath = `jobs/${cat}/${slug}.html`;
    canon    = `${cfg.siteUrl}/${filePath}`;
    pageHtml = buildJobHtml(item, title, dept, cat, slug, canon, cfg);
  } else if (pageType === 'result') {
    const rSlug = slug.includes('result') ? slug : `${slug}-result`;
    filePath = `results/${cat}/${rSlug}.html`;
    canon    = `${cfg.siteUrl}/${filePath}`;
    pageHtml = buildResultHtml(item, title, dept, cat, rSlug, canon, cfg);
  } else {
    const aSlug = slug.includes('admit') ? slug : `${slug}-admit-card`;
    filePath = `admit-cards/${cat}/${aSlug}.html`;
    canon    = `${cfg.siteUrl}/${filePath}`;
    pageHtml = buildAdmitHtml(item, title, dept, cat, aSlug, canon, cfg);
  }

  return { path: filePath, html: pageHtml };
}

// ── Job page ────────────────────────────────────────────────────────────────

function buildJobHtml(item, title, dept, cat, slug, canon, cfg) {
  const desc = buildJobDesc(item, title, dept, cfg);
  const depth = '../..';

  const applyUrl = item.applyUrl || googleSearchUrl(title, 'apply online official site');
  const notifUrl = item.notificationUrl || googleSearchUrl(title, 'notification PDF official');

  const jsonLd = JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'JobPosting',
    title,
    description: desc,
    identifier: { '@type': 'PropertyValue', name: dept, value: slug },
    datePosted: todayIso(),
    validThrough: toIsoDate(item.lastDate) || new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    employmentType: 'FULL_TIME',
    hiringOrganization: {
      '@type': 'Organization',
      name: dept,
      sameAs: cfg.siteUrl || 'https://naukridhaba.in',
      logo: `${cfg.siteUrl || 'https://naukridhaba.in'}/img/og-default.png`,
    },
    jobLocation: {
      '@type': 'Place',
      address: {
        '@type': 'PostalAddress',
        streetAddress: 'Government of India',
        addressLocality: 'New Delhi',
        addressRegion: 'Delhi',
        postalCode: '110001',
        addressCountry: 'IN',
      },
    },
    applicantLocationRequirements: { '@type': 'Country', name: 'India' },
    baseSalary: {
      '@type': 'MonetaryAmount',
      currency: 'INR',
      value: {
        '@type': 'QuantitativeValue',
        value: (item.salary && item.salary !== 'Check Notification') ? item.salary : 'As per Government Norms',
        unitText: 'MONTH',
      },
    },
    url: canon,
  });

  return pageTemplate({
    title,
    desc,
    canon,
    dept,
    depth,
    cfg,
    jsonLd,
    body: jobBodyHtml(item, title, dept, cat, canon, applyUrl, notifUrl, cfg),
  });
}

function buildJobDesc(item, title, dept, cfg) {
  const parts = [`${title} — official recruitment notification from ${dept}.`];
  if (item.lastDate) parts.push(`Last date: ${item.lastDate}.`);
  if (item.qualification && item.qualification !== 'Check Notification') {
    parts.push(`Qualification: ${item.qualification.slice(0, 80)}.`);
  }
  parts.push(`Apply online at ${cfg.siteName}.`);
  return parts.join(' ');
}

function jobBodyHtml(item, title, dept, _cat, canon, applyUrl, notifUrl, cfg) {
  const rows = [
    ['Post Name', esc(title)],
    ['Department', esc(dept)],
    item.vacancy       ? ['Total Posts',   esc(item.vacancy)]       : null,
    item.lastDate      ? ['Last Date',     esc(item.lastDate)]       : null,
    item.startDate     ? ['Start Date',    esc(item.startDate)]      : null,
    item.qualification ? ['Qualification', esc(item.qualification)]  : null,
    item.ageLimit      ? ['Age Limit',     esc(item.ageLimit)]       : null,
    item.salary        ? ['Salary / Pay',  esc(item.salary)]         : null,
    item.fee           ? ['Application Fee', esc(item.fee)]          : null,
  ].filter(Boolean);

  return `
<main class="container detail-page" itemscope itemtype="https://schema.org/JobPosting">
  <nav class="breadcrumb" aria-label="breadcrumb">
    <a href="${cfg.siteUrl}/">${esc(cfg.siteName)}</a> &rsaquo;
    <a href="${cfg.siteUrl}/latest-jobs.html">Latest Jobs</a> &rsaquo;
    <span>${esc(title)}</span>
  </nav>

  <h1 class="detail-title" itemprop="title">${esc(title)}</h1>
  <p class="detail-dept"><strong>Organisation:</strong> <span itemprop="hiringOrganization" itemscope itemtype="https://schema.org/Organization"><span itemprop="name">${esc(dept)}</span></span></p>

  <table class="detail-table">
    <tbody>
      ${rows.map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join('\n      ')}
    </tbody>
  </table>

  <div class="cta-buttons">
    <a href="${esc(applyUrl)}" class="btn btn-primary" target="_blank" rel="noopener noreferrer">Apply Online</a>
    <a href="${esc(notifUrl)}" class="btn btn-secondary" target="_blank" rel="noopener noreferrer">Download Notification</a>
  </div>

  <p class="disclaimer"><em>Always verify details from the official website before applying. ${esc(cfg.siteName)} aggregates information for convenience only.</em></p>
</main>`;
}

// ── Result page ──────────────────────────────────────────────────────────────

function buildResultHtml(item, title, dept, _cat, _slug, canon, cfg) {
  const desc = `${title}: Result declared. Check your result at ${cfg.siteName}.`;
  const depth = '../..';

  const resultUrl = item.resultUrl || googleSearchUrl(title, 'result official site');

  const jsonLd = JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'Event',
    name: title,
    description: desc,
    startDate: todayIso(),
    location: { '@type': 'Place', name: 'India' },
    url: canon,
  });

  return pageTemplate({
    title, desc, canon, dept, depth, cfg, jsonLd,
    body: resultBodyHtml(item, title, dept, canon, resultUrl, cfg),
  });
}

function resultBodyHtml(item, title, dept, _canon, resultUrl, cfg) {
  const rows = [
    ['Post Name',    esc(title)],
    ['Organisation', esc(dept)],
    item.resultDate  ? ['Result Date',   esc(item.resultDate)]  : null,
    item.examDate    ? ['Exam Date',     esc(item.examDate)]    : null,
    item.vacancy     ? ['Total Posts',   esc(item.vacancy)]     : null,
  ].filter(Boolean);

  return `
<main class="container detail-page">
  <nav class="breadcrumb" aria-label="breadcrumb">
    <a href="${cfg.siteUrl}/">${esc(cfg.siteName)}</a> &rsaquo;
    <a href="${cfg.siteUrl}/results.html">Results</a> &rsaquo;
    <span>${esc(title)}</span>
  </nav>

  <h1 class="detail-title">${esc(title)}</h1>
  <p class="detail-dept"><strong>Organisation:</strong> ${esc(dept)}</p>

  <table class="detail-table">
    <tbody>
      ${rows.map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join('\n      ')}
    </tbody>
  </table>

  <div class="cta-buttons">
    <a href="${esc(resultUrl)}" class="btn btn-primary" target="_blank" rel="noopener noreferrer">Check Result</a>
  </div>

  <p class="disclaimer"><em>Always verify details from the official website. ${esc(cfg.siteName)} aggregates information for convenience only.</em></p>
</main>`;
}

// ── Admit card page ──────────────────────────────────────────────────────────

function buildAdmitHtml(item, title, dept, _cat, _slug, canon, cfg) {
  const desc = `${title}: Admit card available. Download your hall ticket at ${cfg.siteName}.`;
  const depth = '../..';

  const admitUrl = item.admitUrl || googleSearchUrl(title, 'admit card download official site');

  const jsonLd = JSON.stringify({
    '@context': 'https://schema.org',
    '@type': 'Event',
    name: title,
    description: desc,
    startDate: todayIso(),
    location: { '@type': 'Place', name: 'India' },
    url: canon,
  });

  return pageTemplate({
    title, desc, canon, dept, depth, cfg, jsonLd,
    body: admitBodyHtml(item, title, dept, canon, admitUrl, cfg),
  });
}

function admitBodyHtml(item, title, dept, _canon, admitUrl, cfg) {
  const rows = [
    ['Post Name',    esc(title)],
    ['Organisation', esc(dept)],
    item.examDate  ? ['Exam Date',        esc(item.examDate)]  : null,
    item.admitDate ? ['Admit Card Date',  esc(item.admitDate)] : null,
    item.vacancy   ? ['Total Posts',      esc(item.vacancy)]   : null,
  ].filter(Boolean);

  return `
<main class="container detail-page">
  <nav class="breadcrumb" aria-label="breadcrumb">
    <a href="${cfg.siteUrl}/">${esc(cfg.siteName)}</a> &rsaquo;
    <a href="${cfg.siteUrl}/admit-cards.html">Admit Cards</a> &rsaquo;
    <span>${esc(title)}</span>
  </nav>

  <h1 class="detail-title">${esc(title)}</h1>
  <p class="detail-dept"><strong>Organisation:</strong> ${esc(dept)}</p>

  <table class="detail-table">
    <tbody>
      ${rows.map(([k, v]) => `<tr><th>${k}</th><td>${v}</td></tr>`).join('\n      ')}
    </tbody>
  </table>

  <div class="cta-buttons">
    <a href="${esc(admitUrl)}" class="btn btn-primary" target="_blank" rel="noopener noreferrer">Download Admit Card</a>
  </div>

  <p class="disclaimer"><em>Always verify details from the official website. ${esc(cfg.siteName)} aggregates information for convenience only.</em></p>
</main>`;
}

// ── Shared page shell ─────────────────────────────────────────────────────────

function pageTemplate({ title, desc, canon, dept, depth, cfg, jsonLd, body }) {
  const escapedTitle = esc(title);
  const escapedDesc  = esc(desc);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapedTitle} | ${esc(cfg.siteName)}</title>
  <meta name="description" content="${escapedDesc}">
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
  <meta name="author" content="${esc(cfg.siteName)}">
  <link rel="canonical" href="${esc(canon)}">
  <!-- Open Graph -->
  <meta property="og:type" content="article">
  <meta property="og:title" content="${escapedTitle} | ${esc(cfg.siteName)}">
  <meta property="og:description" content="${escapedDesc}">
  <meta property="og:url" content="${esc(canon)}">
  <meta property="og:site_name" content="${esc(cfg.siteName)}">
  <meta property="og:locale" content="en_IN">
  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="${escapedTitle} | ${esc(cfg.siteName)}">
  <meta name="twitter:description" content="${escapedDesc}">
  <!-- India Geo -->
  <meta name="geo.region" content="IN">
  <meta name="geo.placename" content="India">
  <link rel="stylesheet" href="${depth}/css/style.css">
  <script type="application/ld+json">${jsonLd}</script>
  <script src="${depth}/js/header-footer.js" defer></script>
</head>
<body>
<header class="header"></header>
${body}
<footer class="footer"></footer>
</body>
</html>`;
}

// ──────────────────────────────────────────────────────────────────────────────
// GITHUB API
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Create or update a file in the GitHub repository.
 * Uses the GitHub Contents API (PUT /repos/{owner}/{repo}/contents/{path}).
 */
async function pushToGitHub(filePath, content, cfg, env) {
  const token = env.GITHUB_TOKEN;
  if (!token) {
    console.error('[NaukriDhaba] GITHUB_TOKEN not set — cannot push files');
    return false;
  }

  const apiUrl = `${GITHUB_API}/repos/${cfg.owner}/${cfg.repo}/contents/${filePath}`;
  const encoded = btoa(unescape(encodeURIComponent(content))); // UTF-8 → base64

  // Check if the file already exists.
  // If it does, skip writing — the Python scraper owns existing V2 detail pages.
  // The CF worker only creates NEW pages to avoid overwriting enriched V2 content
  // with its simpler template, which would revert the site to the issue fixed in #105.
  let sha;
  try {
    const existing = await fetch(apiUrl, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
      },
    });
    if (existing.ok) {
      const data = await existing.json();
      sha = data.sha;
      // Page already exists — skip to prevent overwriting V2 enriched content.
      console.log(`[NaukriDhaba]   Skipping (already exists): ${filePath}`);
      return false;
    }
  } catch (_) { /* file does not exist yet — proceed to create */ }

  // Create the file (new pages only)
  const body = {
    message: `Auto-scrape: ${filePath}`,
    content: encoded,
    branch: cfg.branch,
  };

  try {
    const resp = await fetch(apiUrl, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'X-GitHub-Api-Version': '2022-11-28',
      },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      const err = await resp.text();
      console.error(`[NaukriDhaba] GitHub API error for ${filePath}: ${resp.status} ${err}`);
      return false;
    }
    return true;
  } catch (err) {
    console.error(`[NaukriDhaba] GitHub push failed for ${filePath}: ${err.message}`);
    return false;
  }
}

/**
 * Dispatch the post-scrape-update GitHub Actions workflow so it can rebuild
 * listing pages, state pages, and the sitemap after new pages are pushed.
 *
 * Requires GITHUB_TOKEN to have `actions: write` scope in addition to
 * `contents: write`.  The workflow file must exist at
 * .github/workflows/post-scrape-update.yml.
 */
async function triggerPostProcessing(cfg, env, stats) {
  const token = env.GITHUB_TOKEN;
  if (!token) {
    console.warn('[NaukriDhaba] Skipping post-processing trigger — GITHUB_TOKEN not set');
    return;
  }

  const workflow = env.POST_PROCESS_WORKFLOW ?? 'post-scrape-update.yml';
  const apiUrl   = `${GITHUB_API}/repos/${cfg.owner}/${cfg.repo}/actions/workflows/${workflow}/dispatches`;

  try {
    const resp = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'X-GitHub-Api-Version': '2022-11-28',
      },
      body: JSON.stringify({
        ref: cfg.branch,
        inputs: {
          triggered_by: 'cf-scraper-worker',
          jobs_added:    String(stats.jobs),
          results_added: String(stats.results),
          admits_added:  String(stats.admits),
        },
      }),
    });

    if (resp.status === 204) {
      console.log('[NaukriDhaba] Post-processing workflow dispatched successfully.');
    } else {
      const body = await resp.text();
      console.warn(`[NaukriDhaba] Workflow dispatch returned ${resp.status}: ${body}`);
    }
  } catch (err) {
    console.warn(`[NaukriDhaba] Could not trigger post-processing workflow: ${err.message}`);
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// KV STATE — SEEN ITEMS
// ──────────────────────────────────────────────────────────────────────────────

function itemKey(item) {
  // Stable hash of the item URL — used as the KV key
  return 'seen:' + simpleHash(item.detailUrl);
}

async function isSeen(key, env) {
  if (!env.SEEN_ITEMS) return false;
  const val = await env.SEEN_ITEMS.get(key);
  return val !== null;
}

async function markSeen(key, env) {
  if (!env.SEEN_ITEMS) return;
  // TTL: 90 days — automatically expires old entries
  await env.SEEN_ITEMS.put(key, '1', { expirationTtl: 90 * 24 * 3600 });
}

// ──────────────────────────────────────────────────────────────────────────────
// HTML PARSING UTILITIES
// ──────────────────────────────────────────────────────────────────────────────

/** Extract all <td> inner HTML blocks from a <tr> row HTML. */
function extractTds(rowHtml) {
  const tds = [];
  const pattern = /<td[^>]*>([\s\S]*?)<\/td>/gi;
  let m;
  while ((m = pattern.exec(rowHtml)) !== null) {
    tds.push(m[1]);
  }
  return tds;
}

/** Extract the first <a href> and its text from an HTML fragment. */
function extractLink(html) {
  const m = /<a[^>]+href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i.exec(html);
  if (!m) return { href: '', text: '' };
  return { href: m[1].trim(), text: stripTags(m[2]).trim() };
}

/** Strip all HTML tags from a string. */
function stripTags(html) {
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

/** Decode common HTML entities. Decodes &amp; last to prevent double-decode. */
function decodeHtmlEntities(s) {
  return s
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#039;/g, "'")
    .replace(/&nbsp;/g, ' ')
    .replace(/&ndash;/g, '–')
    .replace(/&mdash;/g, '—')
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n))
    .replace(/&amp;/g, '&')  // must be last — prevents double-decode of &amp;lt; → <
    .trim();
}

/** Escape a string for safe embedding in HTML attributes / text nodes. */
function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Extract an official / government link from a detail page.
 * Tries to find an anchor whose visible text matches one of the keywords,
 * and whose href points to an official (.gov.in, .nic.in) or major domain.
 */
function extractOfficialLink(html, sourceBase, keywords) {
  const sourceHost = new URL(sourceBase).hostname;
  const linkPattern = /<a[^>]+href=["']([^"'#]+)["'][^>]*>([\s\S]*?)<\/a>/gi;
  let m;

  while ((m = linkPattern.exec(html)) !== null) {
    const href    = m[1].trim();
    const linkText = stripTags(m[2]).toLowerCase();

    // Skip links back to the source site itself
    if (href.includes(sourceHost)) continue;
    // Skip javascript links
    if (href.toLowerCase().startsWith('javascript')) continue;

    const matched = keywords.some(kw => linkText.includes(kw));
    if (!matched) continue;

    const absUrl = href.startsWith('http') ? href : toAbsoluteUrl(href, sourceBase);

    // Prefer official government domains
    if (/\.(gov\.in|nic\.in|ac\.in|edu\.in|org\.in)/.test(absUrl)) {
      return absUrl;
    }
    // Return any non-source external link
    if (!absUrl.includes(sourceHost)) {
      return absUrl;
    }
  }
  return null;
}

/**
 * Extract a field value from plain text using keyword hints.
 * Looks for patterns like "Last Date : 28/02/2026" or "Last Date 28 February 2026".
 */
function extractField(text, keywords) {
  const lower = text.toLowerCase();
  for (const kw of keywords) {
    const idx = lower.indexOf(kw);
    if (idx === -1) continue;
    // Extract up to 120 chars after the keyword
    const snippet = text.slice(idx + kw.length, idx + kw.length + 120);
    // Look for a value after optional : or whitespace
    const m = /^[\s:–-]*([A-Za-z0-9 \/\-,.()]{3,80})/.exec(snippet);
    if (m) {
      const val = m[1].trim();
      // Exclude if the value starts with another keyword (false positive)
      if (val.length < 3) continue;
      return val;
    }
  }
  return '';
}

// ──────────────────────────────────────────────────────────────────────────────
// TITLE / URL UTILITIES
// ──────────────────────────────────────────────────────────────────────────────

const NAV_TITLES = new Set([
  'post name', 'latest jobs', 'results', 'admit card', 'admit cards',
  'home', 'sarkari result', 'sarkari naukri', '#', '', 'click here',
  'more details', 'check here', 'view details',
]);

function isNavTitle(title) {
  return NAV_TITLES.has(title.toLowerCase().trim());
}

const JOB_PATTERNS    = [/appl/i, /recruit/i, /vacanc/i, /bharti/i, /form/i, /naukri/i, /job/i];
const RESULT_PATTERNS = [/result/i, /merit list/i, /score card/i, /final list/i, /selection list/i];
const ADMIT_PATTERNS  = [/admit/i, /hall ticket/i, /call letter/i, /e-ticket/i];

function kindMatchesTitle(title, pageType) {
  if (pageType === 'result') return RESULT_PATTERNS.some(p => p.test(title));
  if (pageType === 'admit')  return ADMIT_PATTERNS.some(p => p.test(title));
  // For jobs: exclude result / admit patterns, then include if job keywords match
  if (RESULT_PATTERNS.some(p => p.test(title)) || ADMIT_PATTERNS.some(p => p.test(title))) {
    return false;
  }
  return JOB_PATTERNS.some(p => p.test(title)) || true; // job is the default catch-all
}

const DEPT_PATTERNS = [
  [/upsc/i,         'UPSC'],
  [/rrb|railway/i,  'Railway'],
  [/ssc/i,          'SSC'],
  [/ibps|sbi|rbi|bank/i, 'Banking'],
  [/police/i,       'Police'],
  [/army|navy|airforce|defence|military/i, 'Defence'],
  [/nta|jee|neet|cuet|ugc/i, 'NTA/Education'],
  [/upsssc|bpsc|mpsc|rpsc|jpsc|hpsc/i, 'State PSC'],
  [/teaching|teacher|tgt|pgt|prt/i, 'Teaching'],
];

function inferDept(title) {
  for (const [pattern, name] of DEPT_PATTERNS) {
    if (pattern.test(title)) return name;
  }
  return 'Government';
}

const CAT_PATTERNS = [
  [/upsc/i,            'upsc'],
  [/rrb|railway/i,     'railway'],
  [/ssc/i,             'ssc'],
  [/bank|ibps|sbi|rbi/i, 'banking'],
  [/police/i,          'police'],
  [/army|navy|airforce|defence|military/i, 'defence'],
];

function getCategory(dept) {
  const d = dept.toLowerCase();
  for (const [pattern, cat] of CAT_PATTERNS) {
    if (pattern.test(d)) return cat;
  }
  return 'government';
}

function slugify(title) {
  return title
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 80);
}

function normalizeTitle(title) {
  return title
    .replace(/\s+/g, ' ')
    .replace(/\b(sarkariresult|sarkari result|sarkari exam|freejobalert|rojgarresult)\b/gi, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function toAbsoluteUrl(href, base) {
  try {
    return new URL(href, base).href;
  } catch (_) {
    return href;
  }
}

function googleSearchUrl(title, suffix) {
  const q = encodeURIComponent(`${title} ${suffix}`);
  return `https://www.google.com/search?q=${q}`;
}

// ──────────────────────────────────────────────────────────────────────────────
// DATE UTILITIES
// ──────────────────────────────────────────────────────────────────────────────

const MONTHS = {
  jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
  jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11,
  january: 0, february: 1, march: 2, april: 3, june: 5,
  july: 6, august: 7, september: 8, october: 9, november: 10, december: 11,
};

function parseDateStr(s) {
  if (!s) return null;
  s = s.trim();

  // DD/MM/YYYY
  let m = /(\d{1,2})\/(\d{1,2})\/(\d{4})/.exec(s);
  if (m) return new Date(+m[3], +m[2] - 1, +m[1]);

  // DD-MM-YYYY
  m = /(\d{1,2})-(\d{1,2})-(\d{4})/.exec(s);
  if (m) return new Date(+m[3], +m[2] - 1, +m[1]);

  // DD Month YYYY
  m = /(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})/.exec(s);
  if (m) {
    const mo = MONTHS[m[2].toLowerCase()];
    if (mo !== undefined) return new Date(+m[3], mo, +m[1]);
  }

  // Month DD, YYYY
  m = /([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})/.exec(s);
  if (m) {
    const mo = MONTHS[m[1].toLowerCase()];
    if (mo !== undefined) return new Date(+m[3], mo, +m[2]);
  }

  return null;
}

function toIsoDate(s) {
  if (!s) return '';
  const d = parseDateStr(s);
  if (!d || isNaN(d)) return '';
  return d.toISOString().slice(0, 10);
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

// ──────────────────────────────────────────────────────────────────────────────
// MISC UTILITIES
// ──────────────────────────────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** Simple non-cryptographic hash for deduplication keys. */
function simpleHash(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(31, h) + str.charCodeAt(i) | 0;
  }
  return (h >>> 0).toString(16);
}

function getConfig(env) {
  return {
    owner:    env.GITHUB_OWNER    ?? 'ashoksingh-ayodhya',
    repo:     env.GITHUB_REPO     ?? 'naukri-dhaba',
    branch:   env.GITHUB_BRANCH   ?? 'main',
    siteUrl:  (env.SITE_URL       ?? 'https://naukridhaba.in').replace(/\/$/, ''),
    siteName: env.SITE_NAME       ?? 'Naukri Dhaba',
    maxItems: parseInt(env.MAX_ITEMS_PER_RUN ?? '20', 10),
  };
}

/**
 * Naukri Dhaba — Cloudflare Fetch Proxy Worker
 *
 * Deploys on Cloudflare Workers (free tier: 100,000 req/day).
 * Acts as a fetch relay so GitHub Actions can scrape sites
 * that block GitHub's IP ranges.
 *
 * HOW TO DEPLOY:
 *   1. Go to https://dash.cloudflare.com → Workers & Pages → Create
 *   2. Paste this entire file → Deploy
 *   3. Copy the Worker URL (e.g. https://nd-proxy.YOUR-NAME.workers.dev)
 *   4. Add to GitHub repo secrets:
 *        CF_WORKER_PROXY_URL = https://nd-proxy.YOUR-NAME.workers.dev
 *        CF_WORKER_SECRET    = (leave blank — no PROXY_SECRET binding needed)
 *   Note: PROXY_SECRET binding is optional. If not set, all requests are allowed.
 *
 * USAGE (called by scraper automatically):
 *   GET https://nd-proxy.YOUR-NAME.workers.dev/?url=https://www.sarkariresult.com/latestjob.php
 *   Header: X-Proxy-Secret: <your secret>
 */

const ALLOWED_HOSTS = [
  'sarkariresult.com',
  'www.sarkariresult.com',
  'freejobalert.com',
  'www.freejobalert.com',
  'rojgarresult.com',
  'www.rojgarresult.com',
  'sarkariexam.com',
  'www.sarkariexam.com',
];

export default {
  async fetch(request, env) {
    // ── Secret check ──────────────────────────────────────
    const secret = env.PROXY_SECRET;
    if (secret) {
      const provided = request.headers.get('X-Proxy-Secret') || '';
      if (provided !== secret) {
        return new Response('Forbidden', { status: 403 });
      }
    }

    // ── Parse target URL ──────────────────────────────────
    const { searchParams } = new URL(request.url);
    const targetUrl = searchParams.get('url');
    if (!targetUrl) {
      return new Response('Missing ?url= parameter', { status: 400 });
    }

    // ── Validate host is in allowed list ──────────────────
    let targetHost;
    try {
      targetHost = new URL(targetUrl).hostname;
    } catch {
      return new Response('Invalid URL', { status: 400 });
    }
    if (!ALLOWED_HOSTS.includes(targetHost)) {
      return new Response(`Host not allowed: ${targetHost}`, { status: 403 });
    }

    // ── Fetch from Cloudflare edge ────────────────────────
    try {
      const response = await fetch(targetUrl, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
          'Accept-Encoding': 'gzip, deflate, br',
          'Cache-Control': 'no-cache',
          'Referer': `https://${targetHost}/`,
        },
        redirect: 'follow',
        cf: { cacheTtl: 0, cacheEverything: false },
      });

      const body = await response.arrayBuffer();
      return new Response(body, {
        status: response.status,
        headers: {
          'Content-Type': response.headers.get('Content-Type') || 'text/html; charset=utf-8',
          'X-Proxied-By': 'cf-worker',
          'X-Origin-Status': String(response.status),
        },
      });
    } catch (err) {
      return new Response(`Fetch error: ${err.message}`, { status: 502 });
    }
  },
};

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

// Strings that appear in Cloudflare challenge pages — not real content
const CHALLENGE_MARKERS = [
  'cf-browser-verification',
  'cf_chl_opt',
  'challenge-platform',
  'jschl_vc',
  'jschl-answer',
  '__cf_chl',
  'Ray ID',
  'Checking if the site connection is secure',
  'DDoS protection by Cloudflare',
  'Enable JavaScript and cookies to continue',
  // Cloudflare Turnstile / newer challenge variants
  'cf-turnstile',
  'challenges.cloudflare.com',
  'turnstile.cloudflare.com',
  // hCaptcha
  'hcaptcha.com',
  'h-captcha',
  // Generic bot-protection pages (minimal content returned when blocked)
  'Access denied',
  'Please wait',
  'Just a moment',
  'Verifying you are human',
  'Please enable JavaScript',
  'Please enable cookies',
  'Your request has been blocked',
  'Too many requests',
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
      return new Response('Host not allowed: ' + targetHost, { status: 403 });
    }

    // ── Fetch from Cloudflare edge with realistic headers ─
    // Try up to 3 times with progressively different headers
    const attempts = [
      {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-IN,en;q=0.9,hi;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://' + targetHost + '/',
      },
      {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'hi-IN,hi;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
      },
      // Third attempt: mobile Safari UA — some sites serve simpler HTML to mobile
      {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-IN,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
      },
    ];

    let lastError = null;

    for (let i = 0; i < attempts.length; i++) {
      try {
        const response = await fetch(targetUrl, {
          headers: attempts[i],
          redirect: 'follow',
          cf: { cacheTtl: 0, cacheEverything: false },
        });

        const body = await response.text();

        // ── Detect challenge page ─────────────────────────
        const isChallenge = CHALLENGE_MARKERS.some(marker => body.includes(marker));
        if (isChallenge) {
          // If this is the last attempt, tell the scraper it's a challenge
          if (i === attempts.length - 1) {
            return new Response(
              JSON.stringify({ error: 'cloudflare_challenge', attempt: i + 1, status: response.status }),
              {
                status: 503,
                headers: { 'Content-Type': 'application/json', 'X-Challenge-Detected': '1' },
              }
            );
          }
          // Otherwise try next set of headers
          await new Promise(r => setTimeout(r, 800));
          continue;
        }

        // ── Return actual content ─────────────────────────
        return new Response(body, {
          status: response.status,
          headers: {
            'Content-Type': response.headers.get('Content-Type') || 'text/html; charset=utf-8',
            'X-Proxied-By': 'cf-worker',
            'X-Origin-Status': String(response.status),
            'X-Attempt': String(i + 1),
          },
        });

      } catch (err) {
        lastError = err;
        // Wait 1s before retry
        if (i < attempts.length - 1) await new Promise(r => setTimeout(r, 1000));
      }
    }

    return new Response('Fetch error: ' + (lastError?.message || 'unknown'), { status: 502 });
  },
};

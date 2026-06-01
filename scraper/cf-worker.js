/**
 * Naukri Dhaba — Cloudflare Worker HTTP proxy
 *
 * Forwards requests to sarkariresult.com and related sites using Cloudflare
 * edge IPs (which are never blocked by other Cloudflare-protected sites).
 *
 * DEPLOY (one-time, free):
 *   1.  npm install -g wrangler
 *   2.  wrangler login
 *   3.  cd scraper && wrangler deploy cf-worker.js --name naukri-proxy
 *   4.  Note the URL printed (e.g. https://naukri-proxy.<your>.workers.dev)
 *   5.  (Optional) wrangler secret put PROXY_SECRET  → enter any random string
 *   6.  Add to GitHub Actions secrets:
 *         CF_WORKER_PROXY_URL = https://naukri-proxy.<your>.workers.dev
 *         CF_WORKER_SECRET    = (the secret you set above, or leave empty)
 *
 * Usage: GET https://your-worker.workers.dev/?url=<encoded-target-url>
 */

const ALLOWED_HOSTS = new Set([
  "sarkariresult.com",
  "www.sarkariresult.com",
  "freejobalert.com",
  "www.freejobalert.com",
  "rojgarresult.com",
  "www.rojgarresult.com",
  "sarkariexam.com",
  "www.sarkariexam.com",
  "employmentnews.gov.in",
  "www.employmentnews.gov.in",
]);

const BROWSER_HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  Accept:
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
  "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
  "Accept-Encoding": "gzip, deflate, br",
  "Cache-Control": "no-cache",
  "Sec-Fetch-Dest": "document",
  "Sec-Fetch-Mode": "navigate",
  "Sec-Fetch-Site": "none",
  "Sec-Fetch-User": "?1",
  "Upgrade-Insecure-Requests": "1",
  "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
  "sec-ch-ua-mobile": "?0",
  "sec-ch-ua-platform": '"Windows"',
};

export default {
  async fetch(request, env) {
    // ── Auth check ────────────────────────────────────────────────────
    const secret = env.PROXY_SECRET || "";
    if (secret) {
      const clientSecret = request.headers.get("X-Proxy-Secret") || "";
      if (clientSecret !== secret) {
        return new Response("Unauthorized", { status: 401 });
      }
    }

    // ── Parse target URL ──────────────────────────────────────────────
    const incoming = new URL(request.url);
    const targetRaw = incoming.searchParams.get("url");
    if (!targetRaw) {
      return new Response(
        'Pass ?url=<encoded-url>  e.g. ?url=' +
          encodeURIComponent("https://www.sarkariresult.com/latestjob.php"),
        { status: 400 }
      );
    }

    let targetUrl;
    try {
      targetUrl = new URL(targetRaw);
    } catch {
      return new Response("Invalid url parameter", { status: 400 });
    }

    // ── Host allowlist ────────────────────────────────────────────────
    if (!ALLOWED_HOSTS.has(targetUrl.hostname)) {
      return new Response(
        `Host '${targetUrl.hostname}' not in allowlist`,
        { status: 403 }
      );
    }

    // ── Proxy the request ─────────────────────────────────────────────
    try {
      const resp = await fetch(targetUrl.toString(), {
        method: "GET",
        headers: BROWSER_HEADERS,
        redirect: "follow",
      });

      const body = await resp.arrayBuffer();
      const ct = resp.headers.get("Content-Type") || "text/html; charset=utf-8";
      // Forward Content-Encoding so the Python client can auto-decompress.
      // Without this, the client sees raw gzip bytes with no hint to decompress.
      const ce = resp.headers.get("Content-Encoding") || "";

      const outHeaders = {
        "Content-Type": ct,
        "X-Proxied-Status": String(resp.status),
        "X-Proxied-Host": targetUrl.hostname,
        "X-Origin-Status": String(resp.status),
        "Access-Control-Allow-Origin": "*",
      };
      if (ce) outHeaders["Content-Encoding"] = ce;

      return new Response(body, {
        status: resp.status,
        headers: outHeaders,
      });
    } catch (err) {
      return new Response(`Proxy fetch error: ${err.message}`, { status: 502 });
    }
  },
};

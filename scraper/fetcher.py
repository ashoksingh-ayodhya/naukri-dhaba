"""HTTP fetching with the Cloudflare Worker proxy first, then browser-impersonating fallbacks."""

from __future__ import annotations

import logging
import os
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("NaukriDhaba")

for _var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(_var, None)

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Connection": "keep-alive",
}
TIMEOUT = 25
DELAY = float(os.environ.get("SCRAPER_DELAY", "1.0"))

WORKER_URL = os.environ.get("CF_WORKER_PROXY_URL", "").rstrip("/")
WORKER_SECRET = os.environ.get("CF_WORKER_SECRET", "")

_session = requests.Session()
_session.trust_env = False
_session.headers.update(HEADERS)

try:  # Chrome TLS fingerprint — gets past most bot checks without a proxy
    from curl_cffi import requests as _cffi
    _cffi_session = _cffi.Session(impersonate="chrome124")
except Exception:  # noqa: BLE001
    _cffi_session = None

try:
    import cloudscraper
    _cs_session = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows", "mobile": False})
    _cs_session.trust_env = False
except Exception:  # noqa: BLE001
    _cs_session = None

dead_urls: set[str] = set()
stats = {"ok": 0, "fail": 0, "dead": 0}


class FetchError(Exception):
    pass


def _looks_like_challenge(text: str) -> bool:
    head = text[:4000].lower()
    return ("just a moment" in head and "cloudflare" in head) or "checking your browser" in head \
        or "attention required" in head or "captcha" in head and "cf-" in head


def _via_worker(url: str) -> str | None:
    proxy = f"{WORKER_URL}/?url={quote(url, safe='')}"
    headers = {"Accept-Encoding": "identity"}
    if WORKER_SECRET:
        headers["X-Proxy-Secret"] = WORKER_SECRET
    r = _session.get(proxy, headers=headers, timeout=TIMEOUT)
    origin = r.headers.get("X-Origin-Status", str(r.status_code))
    if origin in ("404", "410") or r.status_code in (404, 410):
        dead_urls.add(url)
        return None
    if r.status_code != 200:
        raise FetchError(f"worker HTTP {r.status_code} (origin {origin})")
    text = r.content.decode("utf-8", errors="replace")
    if _looks_like_challenge(text):
        raise FetchError("challenge page via worker")
    return text


def _direct(url: str) -> str | None:
    errors: list[str] = []
    for name, sess in (("curl_cffi", _cffi_session), ("cloudscraper", _cs_session), ("requests", _session)):
        if sess is None:
            continue
        try:
            r = sess.get(url, timeout=TIMEOUT)
            if r.status_code in (404, 410):
                dead_urls.add(url)
                return None
            if r.status_code != 200:
                errors.append(f"{name}: HTTP {r.status_code}")
                continue
            text = r.content.decode("utf-8", errors="replace") if hasattr(r, "content") else r.text
            if _looks_like_challenge(text):
                errors.append(f"{name}: challenge page")
                continue
            return text
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc.__class__.__name__}")
    raise FetchError("; ".join(errors) or "no HTTP client available")


def fetch_text(url: str, retries: int = 2) -> str | None:
    """Return the page body, None if the target is confirmed gone, or raise FetchError."""
    if url in dead_urls:
        return None
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            if WORKER_URL:
                try:
                    text = _via_worker(url)
                    if text is None:
                        stats["dead"] += 1
                        return None
                    stats["ok"] += 1
                    time.sleep(DELAY)
                    return text
                except FetchError as exc:
                    log.debug("worker failed for %s: %s — trying direct", url, exc)
            text = _direct(url)
            if text is None:
                stats["dead"] += 1
                return None
            stats["ok"] += 1
            time.sleep(DELAY)
            return text
        except (FetchError, requests.RequestException) as exc:
            last_err = exc
            if attempt < retries:
                time.sleep(DELAY * attempt * 2)
    stats["fail"] += 1
    raise FetchError(str(last_err))


def fetch_soup(url: str, retries: int = 2) -> BeautifulSoup | None:
    text = fetch_text(url, retries)
    if text is None:
        return None
    soup = BeautifulSoup(text, "lxml")
    if len(soup.find_all("a", href=True)) < 3 and len(text) > 2000:
        raise FetchError("suspicious page: almost no links")
    return soup

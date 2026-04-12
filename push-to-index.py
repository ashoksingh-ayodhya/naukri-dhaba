#!/usr/bin/env python3
"""
============================================================
NAUKRI DHABA — FAST INDEXING TOOL
File: push-to-index.py
============================================================

Submits URLs to search engines for instant crawling:

  Layer 1 — Google Indexing API  (fastest, <minutes for JobPosting pages)
  Layer 2 — IndexNow             (instant for Bing, DuckDuckGo, Yandex,
                                   also picked up by Perplexity)
  Layer 3 — Sitemap ping         (handled by generate-sitemap.py separately)

USAGE:
  # Push all job/result/admit-card pages
  python3 push-to-index.py

  # Push only pages that changed in the last commit (CI mode)
  python3 push-to-index.py --changed-only

  # Dry-run: print URLs without submitting
  python3 push-to-index.py --dry-run

  # Push a single URL
  python3 push-to-index.py --url https://naukridhaba.in/jobs/banking/ibps-clerk-2026.html

ENVIRONMENT VARIABLES / GITHUB SECRETS:
  GOOGLE_INDEXING_SA_KEY   — JSON content of a Google service-account key
                             that has the "Indexing API" role.
                             (Optional; Layer 1 is skipped if not set)
  INDEXNOW_KEY             — Your IndexNow API key string.
                             (Optional; falls back to auto-generated key)
  SITE_URL                 — Override base URL (default: https://naukridhaba.in)

SETUP (one-time):
  1. In Google Search Console → Settings → Ownership verification → add
     your service account email as a "Verified owner".
  2. Enable "Web Search Indexing API" in Google Cloud Console.
  3. Download the service-account JSON key, paste its content into the
     GitHub secret GOOGLE_INDEXING_SA_KEY.
  4. For IndexNow: generate a random hex key, save as INDEXNOW_KEY, and
     ensure the file api/indexnow-<key>.txt exists (this script creates it).
============================================================
"""

import os
import re
import sys
import json
import time
import logging
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# ── Deps (requests is already in scraper/requirements.txt) ──
try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests

# ── Optional: google-auth for Indexing API ─────────────────
try:
    import google.auth
    import google.auth.transport.requests
    from google.oauth2 import service_account
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False

SITE_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(SITE_ROOT))
from site_config import SITE_URL

# ══════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════
INDEXING_API_ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"
INDEXNOW_ENDPOINT     = "https://api.indexnow.org/indexnow"
INDEXNOW_KEY_FILE_DIR = SITE_ROOT / "api"
INDEXNOW_BATCH_SIZE   = 100   # IndexNow allows up to 10,000 but smaller batches are polite

# Only push these content directories (not tool pages, CSS, etc.)
PUSHABLE_DIRS = {"jobs", "results", "admit-cards"}

# Google Indexing API rate limit: 200 req/day total, 20 req/second
GOOGLE_BATCH_DELAY = 0.1   # seconds between requests (10 req/s is safe)
GOOGLE_DAILY_LIMIT = 190   # stay safely under 200

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("PushToIndex")


# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

def _get_indexnow_key() -> str:
    """Return IndexNow key from env or the existing key file."""
    env_key = os.environ.get("INDEXNOW_KEY", "").strip()
    if env_key:
        return env_key
    # Look for existing key file
    for f in INDEXNOW_KEY_FILE_DIR.glob("indexnow-*.txt"):
        return f.stem.replace("indexnow-", "")
    # Generate a new random key
    import secrets
    return secrets.token_hex(16)


def _ensure_indexnow_key_file(key: str) -> Path:
    """Create the IndexNow verification file if it doesn't exist."""
    INDEXNOW_KEY_FILE_DIR.mkdir(exist_ok=True)
    key_file = INDEXNOW_KEY_FILE_DIR / f"indexnow-{key}.txt"
    if not key_file.exists():
        key_file.write_text(key)
        log.info(f"Created IndexNow key file: {key_file.relative_to(SITE_ROOT)}")
    return key_file


def _get_google_credentials():
    """Return Google OAuth2 credentials for the Indexing API, or None."""
    if not HAS_GOOGLE_AUTH:
        log.warning("google-auth not installed — skipping Google Indexing API.")
        log.warning("  Install: pip install google-auth google-auth-httplib2")
        return None
    sa_key_json = os.environ.get("GOOGLE_INDEXING_SA_KEY", "").strip()
    if not sa_key_json:
        log.warning("GOOGLE_INDEXING_SA_KEY not set — skipping Google Indexing API.")
        return None
    try:
        sa_info = json.loads(sa_key_json)
    except json.JSONDecodeError:
        log.error("GOOGLE_INDEXING_SA_KEY is not valid JSON.")
        return None
    scopes = ["https://www.googleapis.com/auth/indexing"]
    try:
        creds = service_account.Credentials.from_service_account_info(sa_info, scopes=scopes)
        # Refresh to get access token
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        return creds
    except Exception as exc:
        log.error(f"Failed to create Google credentials: {exc}")
        return None


# ══════════════════════════════════════════════════════════
# URL DISCOVERY
# ══════════════════════════════════════════════════════════

def get_all_pushable_urls() -> list[str]:
    """Return absolute URLs for all job/result/admit-card pages."""
    urls = []
    for d in PUSHABLE_DIRS:
        for p in sorted((SITE_ROOT / d).rglob("*.html")):
            if p.name == "index.html":
                continue
            rel = p.relative_to(SITE_ROOT).as_posix()
            urls.append(f"{SITE_URL}/{rel}")
    # Also include listing pages and homepage
    for static in ("index.html", "latest-jobs.html", "results.html", "admit-cards.html"):
        if (SITE_ROOT / static).exists():
            urls.append(f"{SITE_URL}/{static}")
    return urls


def get_changed_urls() -> list[str]:
    """Return URLs for pages that changed in the last git commit."""
    try:
        result = subprocess.run(
            ["git", "--no-pager", "diff", "HEAD~1", "--name-only"],
            capture_output=True, text=True, check=True,
            cwd=str(SITE_ROOT)
        )
        changed_files = result.stdout.strip().splitlines()
    except subprocess.CalledProcessError:
        log.warning("Could not run git diff — will push all URLs.")
        return get_all_pushable_urls()

    urls = []
    for f in changed_files:
        p = Path(f)
        if p.suffix != ".html":
            continue
        top = p.parts[0] if p.parts else ""
        if top in PUSHABLE_DIRS or p.name in ("index.html", "latest-jobs.html", "results.html", "admit-cards.html"):
            urls.append(f"{SITE_URL}/{p.as_posix()}")
    return urls


# ══════════════════════════════════════════════════════════
# LAYER 1 — GOOGLE INDEXING API
# ══════════════════════════════════════════════════════════

def push_google(urls: list[str], dry_run: bool = False) -> int:
    """Submit URLs to Google Indexing API.

    Returns number of URLs successfully submitted.
    """
    creds = None if dry_run else _get_google_credentials()
    if not creds and not dry_run:
        log.info("Skipping Google Indexing API (no credentials).")
        return 0

    submitted = 0
    capped = urls[:GOOGLE_DAILY_LIMIT]
    if len(urls) > GOOGLE_DAILY_LIMIT:
        log.warning(f"Google API limit: only pushing first {GOOGLE_DAILY_LIMIT} of {len(urls)} URLs.")

    log.info(f"[Google Indexing API] Submitting {len(capped)} URLs ...")
    for url in capped:
        if dry_run:
            log.info(f"  [DRY-RUN] GOOGLE: {url}")
            submitted += 1
            continue
        payload = json.dumps({"url": url, "type": "URL_UPDATED"}).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {creds.token}",
        }
        try:
            req = Request(INDEXING_API_ENDPOINT, data=payload, headers=headers, method="POST")
            with urlopen(req, timeout=10) as resp:
                resp_body = resp.read().decode()
                log.debug(f"  Google OK: {url} → {resp_body[:80]}")
            submitted += 1
        except HTTPError as exc:
            body = exc.read().decode() if hasattr(exc, 'read') else ''
            log.warning(f"  Google HTTP {exc.code} for {url}: {body[:120]}")
            if exc.code == 429:
                log.warning("  Rate-limited by Google. Stopping.")
                break
        except URLError as exc:
            log.warning(f"  Google URLError for {url}: {exc}")
        time.sleep(GOOGLE_BATCH_DELAY)

    log.info(f"[Google Indexing API] Done: {submitted}/{len(capped)} submitted.")
    return submitted


# ══════════════════════════════════════════════════════════
# LAYER 2 — INDEXNOW (Bing / Yandex / DuckDuckGo)
# ══════════════════════════════════════════════════════════

def push_indexnow(urls: list[str], dry_run: bool = False) -> int:
    """Submit URLs to IndexNow API (Bing, Yandex, DuckDuckGo, Perplexity).

    Returns number of URLs successfully submitted.
    """
    key = _get_indexnow_key()
    if not dry_run:
        _ensure_indexnow_key_file(key)

    host = urlparse(SITE_URL).netloc
    submitted = 0

    # Submit in batches
    for i in range(0, len(urls), INDEXNOW_BATCH_SIZE):
        batch = urls[i: i + INDEXNOW_BATCH_SIZE]
        payload = {
            "host": host,
            "key": key,
            "keyLocation": f"{SITE_URL}/api/indexnow-{key}.txt",
            "urlList": batch,
        }

        if dry_run:
            log.info(f"  [DRY-RUN] INDEXNOW batch {i//INDEXNOW_BATCH_SIZE + 1}: {len(batch)} URLs")
            submitted += len(batch)
            continue

        log.info(f"[IndexNow] Batch {i//INDEXNOW_BATCH_SIZE + 1}: submitting {len(batch)} URLs ...")
        try:
            resp = requests.post(
                INDEXNOW_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=15,
            )
            if resp.status_code in (200, 202):
                log.info(f"  IndexNow OK: {resp.status_code}")
                submitted += len(batch)
            elif resp.status_code == 422:
                log.warning(f"  IndexNow 422: URL validation failed — {resp.text[:120]}")
            elif resp.status_code == 429:
                log.warning("  IndexNow rate-limited. Stopping.")
                break
            else:
                log.warning(f"  IndexNow {resp.status_code}: {resp.text[:120]}")
        except requests.RequestException as exc:
            log.warning(f"  IndexNow request failed: {exc}")
        time.sleep(0.5)

    log.info(f"[IndexNow] Done: {submitted}/{len(urls)} submitted.")
    return submitted


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Push Naukri Dhaba pages to Google Indexing API and IndexNow for fast crawling.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--changed-only", action="store_true",
                        help="Only push URLs that changed in the last git commit (CI mode).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print URLs without actually submitting them.")
    parser.add_argument("--url", metavar="URL",
                        help="Push a single specific URL.")
    parser.add_argument("--no-google", action="store_true",
                        help="Skip Google Indexing API.")
    parser.add_argument("--no-indexnow", action="store_true",
                        help="Skip IndexNow.")
    args = parser.parse_args()

    # ── Collect URLs ──────────────────────────────────────
    if args.url:
        urls = [args.url]
        log.info(f"Pushing single URL: {args.url}")
    elif args.changed_only:
        urls = get_changed_urls()
        log.info(f"Changed pages in last commit: {len(urls)}")
    else:
        urls = get_all_pushable_urls()
        log.info(f"Total pushable pages: {len(urls)}")

    if not urls:
        log.info("No URLs to push. Exiting.")
        return

    log.info(f"Base URL: {SITE_URL}")
    log.info(f"Dry run: {args.dry_run}")

    # ── Layer 1: Google Indexing API ──────────────────────
    g_submitted = 0
    if not args.no_google:
        g_submitted = push_google(urls, dry_run=args.dry_run)
    else:
        log.info("Skipping Google Indexing API (--no-google).")

    # ── Layer 2: IndexNow ─────────────────────────────────
    i_submitted = 0
    if not args.no_indexnow:
        i_submitted = push_indexnow(urls, dry_run=args.dry_run)
    else:
        log.info("Skipping IndexNow (--no-indexnow).")

    # ── Summary ───────────────────────────────────────────
    log.info("=" * 50)
    log.info(f"SUMMARY")
    log.info(f"  Total URLs targeted : {len(urls)}")
    log.info(f"  Google API submitted: {g_submitted}")
    log.info(f"  IndexNow submitted  : {i_submitted}")
    log.info("=" * 50)
    if args.dry_run:
        log.info("Dry run complete — no requests were made.")


if __name__ == "__main__":
    main()

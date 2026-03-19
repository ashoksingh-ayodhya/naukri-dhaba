#!/usr/bin/env python3
"""
Pre-flight check: verify that at least one source site is reachable
before running the full scraper.

Exit codes:
  0 – one or more sources are accessible  → proceed with scraper
  1 – ALL sources are unreachable         → send alert, skip scraper
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import logging
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from site_config import SOURCES

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

TIMEOUT = 15          # seconds per request
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


CF_WORKER_URL    = os.environ.get("CF_WORKER_PROXY_URL", "").rstrip("/")
CF_WORKER_SECRET = os.environ.get("CF_WORKER_SECRET", "")


def check_url(url: str) -> tuple[bool, str]:
    """Return (reachable, reason). Uses CF Worker proxy if configured."""
    # Try via Cloudflare Worker first
    if CF_WORKER_URL:
        try:
            from urllib.parse import quote
            proxy_url = f"{CF_WORKER_URL}/?url={quote(url, safe='')}"
            proxy_headers = dict(HEADERS)
            if CF_WORKER_SECRET:
                proxy_headers["X-Proxy-Secret"] = CF_WORKER_SECRET
            req = Request(proxy_url, headers=proxy_headers, method="GET")
            with urlopen(req, timeout=TIMEOUT) as resp:
                if resp.status < 400:
                    return True, f"HTTP {resp.status} (via CF Worker)"
        except Exception:
            pass  # fall through to direct check

    # Direct fetch fallback
    try:
        req = Request(url, headers=HEADERS, method="GET")
        with urlopen(req, timeout=TIMEOUT) as resp:
            status = resp.status
            if status < 400:
                return True, f"HTTP {status}"
            return False, f"HTTP {status}"
    except HTTPError as e:
        return False, f"HTTP {e.code} {e.reason}"
    except URLError as e:
        return False, str(e.reason)
    except Exception as e:
        return False, str(e)


def main() -> int:
    log.info("=" * 50)
    log.info("SOURCE ACCESSIBILITY CHECK")
    log.info("=" * 50)

    accessible: list[str] = []
    unreachable: list[str] = []

    for source in SOURCES:
        name = source["name"]
        # Only probe the first URL per source (job listing) as a health check
        probe_url = next(iter(source["urls"].values()))
        log.info(f"Checking {name} → {probe_url}")
        ok, reason = check_url(probe_url)
        if ok:
            log.info(f"  ✓ {name}: {reason}")
            accessible.append(name)
        else:
            log.warning(f"  ✗ {name}: {reason}")
            unreachable.append(name)
        time.sleep(1)

    log.info("-" * 50)
    log.info(f"Accessible : {accessible or 'none'}")
    log.info(f"Unreachable: {unreachable or 'none'}")
    log.info("=" * 50)

    if not accessible:
        log.error("ALL sources are unreachable. Scraper will not run.")
        # Print a machine-readable marker for the workflow to pick up
        print("ALL_SOURCES_DOWN=true")
        return 1

    log.info(f"{len(accessible)} source(s) accessible. Proceeding with scraper.")
    print("ALL_SOURCES_DOWN=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

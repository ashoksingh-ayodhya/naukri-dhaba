"""
URL resolution and deduplication for scraped links.

Wraps the existing functions from sarkari_scraper.py so the detail parser
can resolve source-site redirect URLs to official destinations.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import from sarkari_scraper
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

log = logging.getLogger("NaukriDhaba")


def resolve_links(data) -> None:
    """Resolve all URLs in a DetailData object using the main scraper's helpers.

    This function modifies data in-place:
    - Resolves source-site redirects in important_links to official URLs
    - Resolves primary CTA URLs (apply, notification, result, admit, scorecard)
    - Converts URLs to public format via go.html redirect handler
    """
    try:
        from scraper.sarkari_scraper import (
            normalize_url,
            is_source_url,
            is_official_url,
            official_url_or_empty,
            to_public_url,
            primary_cta_url,
            _extract_embedded_official_url,
            _resolve_source_redirect,
        )
    except ImportError:
        log.warning("[link_resolver] Could not import sarkari_scraper helpers — skipping URL resolution")
        return

    source_detail_url = data.source_detail_url

    # Resolve important_links
    resolved_links = []
    seen_urls = set()
    for link in data.important_links:
        raw = link.get("url", "")
        if not raw or raw == "#":
            continue

        # Try to resolve source-site URLs to official ones
        url = normalize_url(raw)
        if is_source_url(url):
            resolved = official_url_or_empty(url)
            if not resolved:
                resolved = _extract_embedded_official_url(url)
            if not resolved:
                resolved = _resolve_source_redirect(url)
            url = resolved or url

        # Skip source-site URLs that couldn't be resolved
        if is_source_url(url):
            continue

        if url not in seen_urls:
            seen_urls.add(url)
            resolved_links.append({
                "label": link.get("label", ""),
                "url": url,
                "link_type": link.get("link_type", "other"),
            })

    data.important_links = resolved_links

    # Resolve primary CTA URLs
    if data.apply_url and data.apply_url != "#":
        data.apply_url = primary_cta_url(data.apply_url, source_detail_url) or data.apply_url
    if data.result_url and data.result_url != "#":
        data.result_url = primary_cta_url(data.result_url, source_detail_url) or data.result_url
    if data.admit_url and data.admit_url != "#":
        data.admit_url = primary_cta_url(data.admit_url, source_detail_url) or data.admit_url
    if data.notification_url:
        data.notification_url = to_public_url(data.notification_url) or data.notification_url
    if data.scorecard_url:
        data.scorecard_url = to_public_url(data.scorecard_url) or data.scorecard_url

    # Resolve extra_links
    public_links = []
    public_seen = set()
    for lnk in data.extra_links:
        url = to_public_url(lnk.get("url", ""))
        if not url:
            continue
        key = (lnk.get("label", ""), url)
        if key not in public_seen:
            public_seen.add(key)
            public_links.append({"label": lnk.get("label", "Official Link"), "url": url})
    data.extra_links = public_links

    # Resolve download_links
    dl_seen = set()
    unique_dls = []
    for dl in data.download_links:
        raw = dl.get("url", "")
        resolved = official_url_or_empty(raw) or _extract_embedded_official_url(raw) or _resolve_source_redirect(raw) or raw
        if resolved and resolved != "#" and resolved not in dl_seen and not is_source_url(resolved):
            dl_seen.add(resolved)
            unique_dls.append({"label": dl.get("label", "Download"), "url": resolved})
    data.download_links = unique_dls

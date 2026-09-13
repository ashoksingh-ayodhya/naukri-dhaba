"""Drop aggregator/social links and resolve embedded official targets on a DetailData."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from urls import clean_link_url  # noqa: E402


def resolve_links(data) -> None:
    base = data.source_detail_url or None
    kept: list[dict] = []
    seen: set[str] = set()
    for link in data.important_links:
        url = clean_link_url(link.get("url"), base)
        if url and url not in seen:
            seen.add(url)
            kept.append({"label": link.get("label", ""), "url": url, "link_type": link.get("link_type", "other")})
    data.important_links = kept
    for attr in ("apply_url", "notification_url", "result_url", "admit_url", "official_website_url", "scorecard_url"):
        setattr(data, attr, clean_link_url(getattr(data, attr), base) or "")
    data.extra_links = [l for l in ({"label": l.get("label", ""), "url": clean_link_url(l.get("url"), base)}
                                    for l in data.extra_links) if l["url"]]
    data.download_links = [l for l in ({"label": l.get("label", "Download"), "url": clean_link_url(l.get("url"), base)}
                                       for l in data.download_links) if l["url"]]

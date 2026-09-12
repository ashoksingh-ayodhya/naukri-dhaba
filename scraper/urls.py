"""URL policy: which links may appear on the site, and how to repair scraped ones."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlparse

SOURCE_HOST_SUFFIXES = (
    "sarkariresult.com", "sarkariresults.com", "sarkariresult.org.in", "sarkariresults.org.in",
    "freejobalert.com", "rojgarresult.com", "sarkariexam.com", "naukridhaba.in",
)
SOCIAL_HOST_SUFFIXES = (
    "instagram.com", "facebook.com", "fb.com", "twitter.com", "x.com", "t.me", "telegram.me",
    "telegram.org", "whatsapp.com", "youtube.com", "youtu.be", "tinyurl.com", "bit.ly",
    "play.google.com", "apps.apple.com", "linkedin.com", "pinterest.com", "sharechat.com",
)

_CORRUPT_BRAND_RE = re.compile(r"(?i)Naukri\s*Dhaba")
_OFFICIAL_PARAMS = ("url", "target", "redirect", "link", "go", "u", "r", "to", "q")


def host_of(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower().split(":")[0]
    except ValueError:
        return ""


def _host_matches(host: str, suffixes: tuple[str, ...]) -> bool:
    return any(host == s or host.endswith("." + s) for s in suffixes)


_SOURCE_NAME_RE = re.compile(r"sarkari|freejobalert|rojgar|naukridhaba|naukri\s*dhaba|jobalert|govtjob|examresult", re.I)


def is_source_host(url: str) -> bool:
    host = host_of(url)
    return _host_matches(host, SOURCE_HOST_SUFFIXES) or bool(_SOURCE_NAME_RE.search(host))


def is_social(url: str) -> bool:
    return _host_matches(host_of(url), SOCIAL_HOST_SUFFIXES)


def restore_brand_corruption(url: str) -> str:
    """Undo an earlier regex pass that wrote our brand name into aggregator URLs."""
    if "Naukri Dhaba" not in url and "naukridhaba" not in url.lower():
        return url
    u = re.sub(r"(?i)https?://(?:www\.)?naukridhaba\.in", "https://www.sarkariresult.com", url)
    u = re.sub(r"(?i)doc\.naukridhaba\.in", "doc.sarkariresult.com", u)
    # In host position the old pass swallowed the TLD too ("www.Naukri Dhaba/upload/x.pdf").
    u = re.sub(r"(?i)^(https?://(?:www\.)?)Naukri\s*Dhaba(?=/|$)", r"\1sarkariresult.com", u)
    u = _CORRUPT_BRAND_RE.sub("sarkariresult", u)
    return u


def embedded_official_url(url: str) -> str:
    """Extract an official target from an aggregator redirect like /go?url=https://ssc.nic.in."""
    try:
        qs = parse_qs(urlparse(url).query)
    except ValueError:
        return ""
    for p in _OFFICIAL_PARAMS:
        for v in qs.get(p, []):
            v = v.strip()
            if v.startswith("http") and not is_source_host(v) and not is_social(v):
                return v
    return ""


def clean_link_url(raw: str | None, base: str | None = None) -> str | None:
    """Return a publishable absolute URL or None.

    Rejects blob:/javascript:/mailto:/anchors, resolves relative links against *base*,
    repairs brand-corrupted aggregator URLs and then drops aggregator/social hosts
    (an embedded official target is kept when present).
    """
    if not raw:
        return None
    u = str(raw).strip().strip('"').strip("'")
    if not u or u == "#":
        return None
    low = u.lower()
    if low.startswith(("blob:", "javascript:", "mailto:", "tel:", "data:", "#", "about:")):
        return None
    u = restore_brand_corruption(u)
    if " " in u or len(re.findall(r"https?://", u.split("?", 1)[0])) > 1:  # two URLs glued together
        return None
    if not re.match(r"^https?://", u, re.I):
        if u.startswith("//"):
            u = "https:" + u
        elif base:
            u = urljoin(base, u)
        else:
            return None
    if not re.match(r"^https?://[^/]+\.[a-z]{2,}", u, re.I):
        return None
    u = re.sub(r"(?<!:)/{2,}", "/", u)
    if is_source_host(u):
        emb = embedded_official_url(u)
        return emb or None
    if is_social(u):
        return None
    return u

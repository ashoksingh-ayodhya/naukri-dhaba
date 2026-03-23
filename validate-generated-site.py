#!/usr/bin/env python3
"""Validate generated static site output before publish."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from site_config import REDIRECT_PATH, SITE_URL, SOURCE_HOSTS

ROOT = Path(__file__).parent
TRACKING_CONFIG_PATH = ROOT / "tracking-config.json"
PLACEHOLDERS = {
    "GTM-XXXXXXX",
    "G-XXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
}


def html_files() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*.html")
        if ".git" not in str(path)
    )


def decode_redirect_target(url: str) -> str | None:
    if REDIRECT_PATH not in url:
        return None

    parsed = urlparse(url)
    if parsed.path != REDIRECT_PATH and not url.startswith(REDIRECT_PATH):
        return None

    query = parsed.query
    if not query and "?" in url:
        query = url.split("?", 1)[1]
    target = parse_qs(query).get("target", [None])[0]
    if not target:
        return None
    return unquote(target)


def validate_redirect_target(target: str) -> str | None:
    parsed = urlparse(target)
    if parsed.scheme not in ("http", "https"):
        return f"redirect target has invalid scheme: {target}"
    if not parsed.netloc:
        return f"redirect target is missing host: {target}"
    if " " in parsed.netloc:
        return f"redirect target host contains spaces: {target}"
    if "naukri%20dhaba" in target.lower() or "naukri dhaba.com" in target.lower():
        return f"redirect target contains malformed host: {target}"
    if parsed.netloc.lower() in SOURCE_HOSTS:
        return f"redirect target still points to source host: {target}"
    return None


def load_tracking_config() -> dict:
    if not TRACKING_CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(TRACKING_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


TRACKING_CONFIG = load_tracking_config()


def is_enabled_with_value(section: str, field: str) -> bool:
    value = ((TRACKING_CONFIG.get(section) or {}).get(field) or "").strip()
    enabled = bool((TRACKING_CONFIG.get(section) or {}).get("enabled"))
    return enabled and value not in PLACEHOLDERS


def validate_html(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(ROOT).as_posix()
    errors: list[str] = []
    skip_redirect_checks = path.name == "go.html"

    if re.search(r'href="#"\s+[^>]*class="btn', content, flags=re.IGNORECASE):
        errors.append(f"{rel}: contains button link with href=\"#\"")

    if re.search(rf"{re.escape(REDIRECT_PATH)}\?target=.*{re.escape(REDIRECT_PATH)}%3Ftarget", content, flags=re.IGNORECASE):
        errors.append(f"{rel}: contains nested redirect target")

    # Detect extensionless pretty routes that won't load on GitHub Pages
    _PRETTY_ROUTE_PAT = re.compile(
        r'href=["\'](?:https://naukridhaba\.in)?/(?:latest-jobs|results|admit-cards|resources|previous-papers|eligibility-calculator|study-planner)["\']',
        re.IGNORECASE,
    )
    if _PRETTY_ROUTE_PAT.search(content):
        errors.append(f"{rel}: contains extensionless pretty route (use .html suffix)")

    if re.search(r"www\.Naukri Dhaba\.com|Naukri Dhaba\.com|naukri%20dhaba", content, flags=re.IGNORECASE):
        errors.append(f"{rel}: contains malformed host text")

    for source_host in SOURCE_HOSTS:
        if re.search(rf'''(?:href|src)=["'][^"']*{re.escape(source_host)}''', content, flags=re.IGNORECASE):
            errors.append(f"{rel}: contains direct source host link: {source_host}")

    if path.name != "go.html":
        if '<meta name="description"' not in content:
            errors.append(f"{rel}: missing meta description")
        if 'property="og:title"' not in content:
            errors.append(f"{rel}: missing og:title")
        if 'property="og:description"' not in content:
            errors.append(f"{rel}: missing og:description")
        if 'property="og:url"' not in content:
            errors.append(f"{rel}: missing og:url")
        if 'name="twitter:title"' not in content:
            errors.append(f"{rel}: missing twitter:title")
        if 'name="twitter:description"' not in content:
            errors.append(f"{rel}: missing twitter:description")

    if not skip_redirect_checks:
        for match in re.finditer(r'''(?:href|src)=["']([^"']+)["']''', content, flags=re.IGNORECASE):
            url = match.group(1)
            if REDIRECT_PATH not in url:
                continue
            target = decode_redirect_target(url)
            if not target:
                errors.append(f"{rel}: redirect URL missing target param: {url}")
                continue
            problem = validate_redirect_target(target)
            if problem:
                errors.append(f"{rel}: {problem}")

    canonical_matches = list(
        re.finditer(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', content, flags=re.IGNORECASE)
    )
    if not canonical_matches:
        errors.append(f"{rel}: missing canonical link")
    for match in canonical_matches:
        canonical = match.group(1)
        if not canonical.startswith(SITE_URL):
            errors.append(f"{rel}: canonical does not use {SITE_URL}: {canonical}")

    if any(part in rel for part in ("jobs/", "results/", "admit-cards/")) and 'application/ld+json' not in content:
        errors.append(f"{rel}: missing JSON-LD")

    if is_enabled_with_value("googleSearchConsole", "verificationCode") and 'name="google-site-verification"' not in content:
        errors.append(f"{rel}: missing Google Search Console verification meta")

    if path.name != "go.html" and is_enabled_with_value("googleTagManager", "containerId"):
        if "googletagmanager.com/gtm.js" not in content:
            errors.append(f"{rel}: missing GTM head script")
        if "googletagmanager.com/ns.html" not in content:
            errors.append(f"{rel}: missing GTM noscript iframe")

    if path.name != "go.html" and bool((TRACKING_CONFIG.get("consentMode") or {}).get("enabled")):
        if 'consent", "default"' not in content and "consent', 'default'" not in content:
            errors.append(f"{rel}: missing consent mode default command")

    if (
        path.name != "go.html"
        and not is_enabled_with_value("googleTagManager", "containerId")
        and is_enabled_with_value("googleAnalytics4", "measurementId")
        and "googletagmanager.com/gtag/js" not in content
    ):
        errors.append(f"{rel}: missing GA4 gtag script")

    if '/jobs/' in rel and 'class="job-detail"' in content:
        if 'Role Snapshot' not in content or 'How to Apply' not in content:
            errors.append(f"{rel}: job detail page still uses incomplete legacy layout")

    if '/results/' in rel and 'class="result-detail"' in content:
        if 'Result Snapshot' not in content or 'How to Check Result' not in content:
            errors.append(f"{rel}: result detail page still uses incomplete legacy layout")

    if '/admit-cards/' in rel and 'class="admit-detail"' in content:
        if 'Admit Card Snapshot' not in content or 'Exam Day Checklist' not in content:
            errors.append(f"{rel}: admit-card detail page still uses incomplete legacy layout")

    return errors


def validate_sitemap() -> list[str]:
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        return ["sitemap.xml: file is missing"]
    content = sitemap.read_text(encoding="utf-8", errors="replace")
    errors: list[str] = []
    for loc in re.findall(r"<loc>(.*?)</loc>", content):
        if not loc.startswith(SITE_URL):
            errors.append(f"sitemap.xml: loc does not use {SITE_URL}: {loc}")
    return errors


def main() -> int:
    errors: list[str] = []
    for path in html_files():
        errors.extend(validate_html(path))
    errors.extend(validate_sitemap())

    if errors:
        print("Generated site validation failed:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("Generated site validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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


_SKIP_DIRS = {"backup-main", "demo", "node_modules", ".git"}


def html_files() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*.html")
        if not any(part in _SKIP_DIRS for part in path.relative_to(ROOT).parts)
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
    is_detail = any(part in rel for part in ("jobs/", "results/", "admit-cards/"))
    # SEO-critical pages: detail pages, listing pages, homepage, state pages
    _SEO_CRITICAL_FILES = {"index.html", "latest-jobs.html", "results.html", "admit-cards.html"}
    is_seo_critical = is_detail or path.name in _SEO_CRITICAL_FILES or rel.startswith("state/")

    if re.search(r'href="#"\s+[^>]*class="btn', content, flags=re.IGNORECASE):
        errors.append(f"{rel}: contains button link with href=\"#\"")

    # Detect extensionless pretty routes that won't load on GitHub Pages
    _PRETTY_ROUTE_PAT = re.compile(
        r'href=["\'](?:https://naukridhaba\.in)?/(?:latest-jobs|results|admit-cards|resources|previous-papers|eligibility-calculator|study-planner)["\']',
        re.IGNORECASE,
    )
    if _PRETTY_ROUTE_PAT.search(content):
        errors.append(f"{rel}: contains extensionless pretty route (use .html suffix)")

    if re.search(rf"{re.escape(REDIRECT_PATH)}\?target=.*{re.escape(REDIRECT_PATH)}%3Ftarget", content, flags=re.IGNORECASE):
        errors.append(f"{rel}: contains nested redirect target")

    if re.search(r"www\.Naukri Dhaba\.com|Naukri Dhaba\.com|naukri%20dhaba", content, flags=re.IGNORECASE):
        errors.append(f"{rel}: contains malformed host text")

    for source_host in SOURCE_HOSTS:
        if re.search(rf'''(?:href|src)=["'][^"']*{re.escape(source_host)}''', content, flags=re.IGNORECASE):
            errors.append(f"{rel}: contains direct source host link: {source_host}")

    # ── Core SEO meta tags ──────────────────────────────────────────
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

    # Strict og:image and twitter:card enforcement on SEO-critical pages
    if is_seo_critical:
        if 'property="og:image"' not in content:
            errors.append(f"{rel}: missing og:image")

        # Enforce single summary_large_image twitter:card — no duplicates
        tc_matches = re.findall(r'name="twitter:card"\s+content="([^"]+)"', content)
        if not tc_matches:
            errors.append(f"{rel}: missing twitter:card meta tag")
        elif len(tc_matches) > 1:
            errors.append(f"{rel}: duplicate twitter:card meta tags ({', '.join(tc_matches)})")
        elif tc_matches[0] != "summary_large_image":
            errors.append(f"{rel}: twitter:card should be summary_large_image, got {tc_matches[0]}")

    # ── Preconnect / dns-prefetch hints for performance ─────────────
    if is_detail:
        if 'rel="preconnect"' not in content:
            errors.append(f"{rel}: missing preconnect hints (required for detail pages)")
        if 'rel="dns-prefetch"' not in content:
            errors.append(f"{rel}: missing dns-prefetch hints (required for detail pages)")

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

    # ── JSON-LD structured data checks ──────────────────────────────
    if is_detail and 'application/ld+json' not in content:
        errors.append(f"{rel}: missing JSON-LD")

    if '/jobs/' in rel and 'application/ld+json' in content:
        if '"JobPosting"' not in content:
            errors.append(f"{rel}: job page missing JobPosting JSON-LD schema")
        else:
            if '"identifier"' not in content:
                errors.append(f"{rel}: JobPosting missing identifier field (required for Google Jobs)")
            if '"applicantLocationRequirements"' not in content:
                errors.append(f"{rel}: JobPosting missing applicantLocationRequirements (required for Google Jobs)")

    if '/jobs/' in rel and '"BreadcrumbList"' not in content:
        errors.append(f"{rel}: job page missing BreadcrumbList JSON-LD")

    if '/jobs/' in rel and '"FAQPage"' not in content:
        errors.append(f"{rel}: job page missing FAQPage JSON-LD")

    # Homepage must have Organization + WebSite schemas
    if rel == "index.html":
        if '"Organization"' not in content:
            errors.append(f"{rel}: homepage missing Organization JSON-LD schema")
        if '"WebSite"' not in content:
            errors.append(f"{rel}: homepage missing WebSite JSON-LD schema")

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

    # ── V2 template design consistency ──────────────────────────────
    # All detail pages must use the V2 template (.detail-page wrapper)
    if is_detail and 'class="detail-page"' not in content:
        errors.append(f"{rel}: detail page not using V2 template (missing .detail-page wrapper)")

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

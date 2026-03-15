#!/usr/bin/env python3
"""Validate generated static site output before publish."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from site_config import REDIRECT_PATH, SITE_URL

ROOT = Path(__file__).parent


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
    return None


def validate_html(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(ROOT).as_posix()
    errors: list[str] = []
    skip_redirect_checks = path.name == "go.html"

    if re.search(r'href="#"\s+[^>]*class="btn', content, flags=re.IGNORECASE):
        errors.append(f"{rel}: contains button link with href=\"#\"")

    if re.search(rf"{re.escape(REDIRECT_PATH)}\?target=.*{re.escape(REDIRECT_PATH)}%3Ftarget", content, flags=re.IGNORECASE):
        errors.append(f"{rel}: contains nested redirect target")

    if re.search(r"www\.Naukri Dhaba\.com|Naukri Dhaba\.com|naukri%20dhaba", content, flags=re.IGNORECASE):
        errors.append(f"{rel}: contains malformed host text")

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

    for match in re.finditer(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', content, flags=re.IGNORECASE):
        canonical = match.group(1)
        if not canonical.startswith(SITE_URL):
            errors.append(f"{rel}: canonical does not use {SITE_URL}: {canonical}")

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

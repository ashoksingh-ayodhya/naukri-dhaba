#!/usr/bin/env python3
"""Website health check for naukridhaba.in (Next.js static site)."""

import sys
import json
import re
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

SITE = "https://naukridhaba.in"
TIMEOUT = 15
HEADERS = {
    "User-Agent": "NaukriDhaba-HealthCheck/1.0",
    "Accept": "text/html,application/json,application/xml,*/*",
}

passed = 0
failed = 0


def check(url, label, min_size=500, expect_type="html", check_content=None):
    global passed, failed
    full_url = f"{SITE}{url}" if url.startswith("/") else url
    try:
        req = Request(full_url, headers=HEADERS)
        with urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read()
            size = len(body)
            text = body.decode("utf-8", errors="replace")
            issues = []

            if resp.status >= 400:
                issues.append(f"HTTP {resp.status}")
            if size < min_size:
                issues.append(f"too small ({size} bytes, expected >={min_size})")

            if expect_type == "html":
                if "<title>" not in text.lower():
                    issues.append("missing <title> tag")

            if expect_type == "json":
                try:
                    data = json.loads(text)
                    if isinstance(data, list) and len(data) == 0:
                        issues.append("empty JSON array")
                    elif isinstance(data, dict) and not data:
                        issues.append("empty JSON object")
                except json.JSONDecodeError:
                    issues.append("invalid JSON")

            if expect_type == "xml":
                if "<url>" not in text and "<item" not in text and "<loc>" not in text:
                    issues.append("XML has no items/URLs")

            if check_content:
                for s in check_content:
                    if s.lower() not in text.lower():
                        issues.append(f"missing: '{s}'")

            if issues:
                failed += 1
                print(f"  FAIL  {label}")
                for i in issues:
                    print(f"        - {i}")
                return text, False
            else:
                passed += 1
                print(f"  OK    {label} ({size:,} bytes)")
                return text, True

    except HTTPError as e:
        failed += 1
        print(f"  FAIL  {label}  →  HTTP {e.code} {e.reason}")
        return None, False
    except URLError as e:
        failed += 1
        print(f"  FAIL  {label}  →  {e.reason}")
        return None, False
    except Exception as e:
        failed += 1
        print(f"  FAIL  {label}  →  {e}")
        return None, False


def main():
    print("=" * 60)
    print("NAUKRI DHABA — HEALTH CHECK")
    print(f"Site: {SITE}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("=" * 60)

    # 1. Core pages
    print("\n[1] CORE PAGES")
    home_html, _ = check("/", "Homepage", min_size=2000,
                         check_content=["naukri dhaba"])
    check("/latest-jobs", "Latest Jobs", min_size=1000)
    check("/results", "Results", min_size=500)
    check("/admit-cards", "Admit Cards", min_size=500)
    check("/answer-keys", "Answer Keys", min_size=200)
    check("/syllabus", "Syllabus", min_size=200)

    # 2. Category pages
    print("\n[2] CATEGORY PAGES")
    for cat in ["ssc", "railway", "banking", "upsc"]:
        check(f"/jobs/{cat}", f"Jobs/{cat}", min_size=500)

    # 3. Search index (used by client-side search)
    print("\n[3] SEARCH INDEX")
    check("/search-index.json", "Search index", min_size=100, expect_type="json")

    # 4. Sitemap
    print("\n[4] SITEMAP")
    check("/sitemap.xml", "Sitemap", min_size=200, expect_type="xml")

    # 5. RSS feeds
    print("\n[5] RSS FEEDS")
    check("/feed.xml", "RSS feed", min_size=200, expect_type="xml")

    # 6. Sample detail pages — extract from homepage
    print("\n[6] SAMPLE DETAIL PAGES")
    if home_html:
        links = list(dict.fromkeys(
            re.findall(r'href="(/(?:jobs|results|admit-cards)/[^/"]+/[^"]+)"', home_html)
        ))[:4]
        if links:
            for link in links:
                check(link, f"Detail: {link}", min_size=1000,
                      check_content=["naukri dhaba"])
                time.sleep(0.3)
        else:
            print("  SKIP  No detail links found on homepage")
    else:
        print("  SKIP  Homepage unavailable")

    # Summary
    total = passed + failed
    print(f"\n{'=' * 60}")
    print(f"Passed: {passed}/{total}   Failed: {failed}/{total}")
    print("STATUS: HEALTHY" if failed == 0 else "STATUS: UNHEALTHY")
    print("=" * 60)
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())

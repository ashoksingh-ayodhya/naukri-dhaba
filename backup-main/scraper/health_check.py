#!/usr/bin/env python3
"""
Website health check for naukridhaba.in
Checks all key pages, API, feeds, and job detail pages.
"""

import sys
import json
import time
import re
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
warnings = 0


def check(url, label, min_size=500, expect_type="html", check_content=None):
    global passed, failed, warnings
    full_url = f"{SITE}{url}" if url.startswith("/") else url
    try:
        req = Request(full_url, headers=HEADERS)
        with urlopen(req, timeout=TIMEOUT) as resp:
            status = resp.status
            body = resp.read()
            size = len(body)
            content_type = resp.headers.get("Content-Type", "")

            issues = []

            if status >= 400:
                issues.append(f"HTTP {status}")

            if size < min_size:
                issues.append(f"too small ({size} bytes, expected >={min_size})")

            text = body.decode("utf-8", errors="replace")

            if expect_type == "html":
                if "<title>" not in text.lower():
                    issues.append("missing <title> tag")
                if "sarkariresult" in text.lower() or "sarkari result" in text.lower():
                    issues.append("BRANDING LEAK: contains 'sarkariresult' text")

            if expect_type == "json":
                try:
                    data = json.loads(text)
                    if isinstance(data, dict):
                        total = sum(len(v) for v in data.values() if isinstance(v, list))
                        if total == 0:
                            issues.append("JSON has no items")
                    elif isinstance(data, list) and len(data) == 0:
                        issues.append("JSON array is empty")
                except json.JSONDecodeError:
                    issues.append("invalid JSON")

            if expect_type == "xml":
                if "<item" not in text and "<url>" not in text and "<loc>" not in text:
                    issues.append("XML has no items/URLs")

            if check_content:
                for check_str in check_content:
                    if check_str.lower() not in text.lower():
                        issues.append(f"missing expected content: '{check_str}'")

            if issues:
                failed += 1
                print(f"  FAIL  {label} ({full_url})")
                for i in issues:
                    print(f"        - {i}")
                return text, False
            else:
                passed += 1
                print(f"  OK    {label} ({size:,} bytes)")
                return text, True

    except HTTPError as e:
        failed += 1
        print(f"  FAIL  {label} ({full_url})")
        print(f"        - HTTP {e.code} {e.reason}")
        return None, False
    except URLError as e:
        failed += 1
        print(f"  FAIL  {label} ({full_url})")
        print(f"        - {e.reason}")
        return None, False
    except Exception as e:
        failed += 1
        print(f"  FAIL  {label} ({full_url})")
        print(f"        - {e}")
        return None, False


def extract_job_links(html):
    """Extract a few job detail page links from HTML."""
    links = re.findall(r'href="(/jobs/[^"]+\.html)"', html)
    return list(dict.fromkeys(links))[:5]  # unique, first 5


def extract_result_links(html):
    links = re.findall(r'href="(/results/[^"]+\.html)"', html)
    return list(dict.fromkeys(links))[:3]


def extract_admit_links(html):
    links = re.findall(r'href="(/admit-cards/[^"]+\.html)"', html)
    return list(dict.fromkeys(links))[:3]


def main():
    global passed, failed, warnings
    print("=" * 60)
    print("NAUKRI DHABA — WEBSITE HEALTH CHECK")
    print(f"Site: {SITE}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 60)

    # 1. Main pages
    print("\n[1] MAIN PAGES")
    print("-" * 40)
    home_html, _ = check("/", "Homepage", min_size=1000,
                          check_content=["naukri dhaba"])
    jobs_html, _ = check("/latest-jobs.html", "Latest Jobs", min_size=500)
    results_html, _ = check("/results.html", "Results", min_size=500)
    admits_html, _ = check("/admit-cards.html", "Admit Cards", min_size=500)
    check("/previous-papers.html", "Previous Papers", min_size=200)

    # 2. API
    print("\n[2] API ENDPOINT")
    print("-" * 40)
    check("/api/latest.json", "API latest.json", min_size=100, expect_type="json")

    # 3. RSS Feeds
    print("\n[3] RSS FEEDS")
    print("-" * 40)
    check("/feed.xml", "Main RSS Feed", min_size=200, expect_type="xml")
    check("/feed/jobs.xml", "Jobs RSS Feed", min_size=200, expect_type="xml")
    check("/feed/results.xml", "Results RSS Feed", min_size=200, expect_type="xml")
    check("/feed/admit-cards.xml", "Admit Cards RSS Feed", min_size=200, expect_type="xml")

    # 4. Sitemap
    print("\n[4] SITEMAP")
    print("-" * 40)
    check("/sitemap.xml", "Sitemap", min_size=200, expect_type="xml")

    # 5. CSS/JS assets
    print("\n[5] ASSETS")
    print("-" * 40)
    check("/css/style.css", "Main CSS", min_size=100, expect_type="css")

    # 6. Sample detail pages
    print("\n[6] SAMPLE JOB PAGES")
    print("-" * 40)
    job_links = []
    if jobs_html:
        job_links = extract_job_links(jobs_html)
    if not job_links and home_html:
        job_links = extract_job_links(home_html)
    if job_links:
        for link in job_links:
            check(link, f"Job: {link.split('/')[-1][:50]}", min_size=1000,
                  check_content=["naukri dhaba"])
            time.sleep(0.5)
    else:
        failed += 1
        print("  FAIL  No job links found on listing pages!")

    print("\n[7] SAMPLE RESULT PAGES")
    print("-" * 40)
    result_links = extract_result_links(results_html) if results_html else []
    if result_links:
        for link in result_links:
            check(link, f"Result: {link.split('/')[-1][:50]}", min_size=1000)
            time.sleep(0.5)
    else:
        print("  SKIP  No result links found")

    print("\n[8] SAMPLE ADMIT CARD PAGES")
    print("-" * 40)
    admit_links = extract_admit_links(admits_html) if admits_html else []
    if admit_links:
        for link in admit_links:
            check(link, f"Admit: {link.split('/')[-1][:50]}", min_size=1000)
            time.sleep(0.5)
    else:
        print("  SKIP  No admit card links found")

    # Summary
    print("\n" + "=" * 60)
    print("HEALTH CHECK SUMMARY")
    print(f"  Passed : {passed}")
    print(f"  Failed : {failed}")
    print(f"  Total  : {passed + failed}")
    print("=" * 60)

    if failed > 0:
        print("\nSTATUS: UNHEALTHY — issues found above")
        return 1
    else:
        print("\nSTATUS: HEALTHY — all checks passed")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

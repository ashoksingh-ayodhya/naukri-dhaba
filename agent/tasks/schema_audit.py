#!/usr/bin/env python3
"""
Schema Markup Auditor
======================
Agent task: fetch live naukridhaba.in pages and sarkariresult.com pages,
extract all JSON-LD schema blocks, compare them, and report what we are
missing or have wrong.

This task ALWAYS fetches live URLs — it never uses training-data knowledge.
If fetching fails the error is escalated to Copilot.

Called by the agent as: from tasks.schema_audit import run
"""

from __future__ import annotations

import json
import re
import sys
import time
from typing import Any

SITE_URL   = "https://naukridhaba.in"
SOURCE_URL = "https://www.sarkariresult.com"

# Schema types we intentionally do NOT use — do not flag as gaps even if source has them.
# FAQPage: deprecated by Google on 2026-05-07, no longer triggers rich results.
IGNORED_SOURCE_SCHEMA_TYPES = {"FAQPage"}

REQUIRED_JOB_FIELDS = {
    "@type", "title", "description", "hiringOrganization",
    "datePosted", "jobLocation", "employmentType",
}


def _fetch_html(url: str, timeout: int = 15) -> str | None:
    """Fetch URL and return HTML text, or None on failure."""
    try:
        import urllib.request
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
                "Accept-Language": "en-IN,en;q=0.9",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"[schema_audit] fetch failed for {url}: {exc}", file=sys.stderr)
        return None


def _extract_json_ld(html: str) -> list[dict]:
    """Extract all JSON-LD blocks from an HTML page."""
    blocks = []
    for raw in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.S | re.I,
    ):
        try:
            blocks.append(json.loads(raw.strip()))
        except Exception:
            pass
    return blocks


def _get_types(blocks: list[dict]) -> set[str]:
    types: set[str] = set()
    for b in blocks:
        t = b.get("@type", "")
        if isinstance(t, list):
            types.update(t)
        elif t:
            types.add(t)
    return types


def _check_job_posting(blocks: list[dict]) -> tuple[bool, list[str]]:
    """Check if JobPosting schema has all required fields. Returns (ok, missing_fields)."""
    for b in blocks:
        if b.get("@type") == "JobPosting":
            missing = [f for f in REQUIRED_JOB_FIELDS if f not in b]
            return (len(missing) == 0), missing
    return False, list(REQUIRED_JOB_FIELDS)


def audit_page(url: str, label: str) -> dict:
    """Fetch a page and audit its schema. Returns audit result dict."""
    print(f"[schema_audit] Fetching {label}: {url}")
    html = _fetch_html(url)
    if not html:
        return {"url": url, "label": label, "error": "fetch_failed", "types": [], "blocks": []}

    blocks = _extract_json_ld(html)
    types  = sorted(_get_types(blocks))
    ok, missing = _check_job_posting(blocks)

    return {
        "url":     url,
        "label":   label,
        "types":   types,
        "block_count": len(blocks),
        "has_job_posting": ok,
        "job_posting_missing_fields": missing,
        "blocks": blocks,
    }


def run(sample_slugs: list[str] | None = None) -> dict:
    """
    Audit schema on:
      - 3 live naukridhaba.in job pages
      - 3 live sarkariresult.com job pages (for comparison)

    Returns a report dict with findings and any missing schema fields.
    """
    import pathlib

    results = {"our_pages": [], "source_pages": [], "issues": []}

    # Find 3 real job slugs from our content
    content_dir = pathlib.Path(__file__).parent.parent.parent / "content" / "jobs"
    our_urls: list[tuple[str, str]] = []
    for cat_dir in sorted(content_dir.iterdir()):
        if not cat_dir.is_dir(): continue
        for mdx in sorted(cat_dir.glob("*.mdx"))[:2]:
            slug = mdx.stem
            cat  = cat_dir.name
            our_urls.append((
                f"{SITE_URL}/jobs/{cat}/{slug}/",
                f"naukridhaba/{cat}/{slug}",
            ))
        if len(our_urls) >= 3:
            break

    # Known sarkariresult job detail URLs to compare against
    source_urls = [
        (f"{SOURCE_URL}/upsc/upsc-nda-na-i-2025/",   "sarkariresult/upsc/nda-na-i-2025"),
        (f"{SOURCE_URL}/ssc/ssc-cgl-2024/",           "sarkariresult/ssc/cgl-2024"),
        (f"{SOURCE_URL}/railway/rrb-ntpc-2025/",      "sarkariresult/railway/rrb-ntpc-2025"),
    ]

    # Audit our pages
    for url, label in our_urls[:3]:
        time.sleep(1)
        r = audit_page(url, label)
        results["our_pages"].append(r)

        # Check for required schema
        if not r.get("has_job_posting"):
            missing = r.get("job_posting_missing_fields", [])
            results["issues"].append({
                "url": url,
                "problem": "Missing or incomplete JobPosting schema",
                "missing_fields": missing,
            })

    # Audit source pages for comparison
    for url, label in source_urls:
        time.sleep(2)  # polite delay
        r = audit_page(url, label)
        results["source_pages"].append(r)

    # Summary
    our_types    = set()
    source_types = set()
    for r in results["our_pages"]:
        our_types.update(r.get("types", []))
    for r in results["source_pages"]:
        source_types.update(r.get("types", []))

    # Exclude intentionally deprecated/ignored types from gap analysis
    actionable_source_types = source_types - IGNORED_SOURCE_SCHEMA_TYPES

    results["summary"] = {
        "our_schema_types":    sorted(our_types),
        "source_schema_types": sorted(source_types),
        "types_we_have_they_dont": sorted(our_types - source_types),
        "types_they_have_we_dont": sorted(actionable_source_types - our_types),
        "issue_count": len(results["issues"]),
    }

    print("[schema_audit] Summary:")
    print(f"  Our schema types:    {sorted(our_types)}")
    print(f"  Source schema types: {sorted(source_types)}")
    print(f"  We have, they don't: {sorted(our_types - source_types)}")
    print(f"  They have, we don't: {sorted(actionable_source_types - our_types)}  (ignored: {sorted(IGNORED_SOURCE_SCHEMA_TYPES & source_types)})")
    print(f"  Issues found: {len(results['issues'])}")

    return results


if __name__ == "__main__":
    import pprint
    pprint.pprint(run())

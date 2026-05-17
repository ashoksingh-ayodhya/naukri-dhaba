#!/usr/bin/env python3
"""
Bulk IndexNow submission for naukridhaba.in

Reads all MDX content files, builds canonical URLs, and submits them to
IndexNow (https://api.indexnow.org). IndexNow is supported by Google,
Bing, and Yandex. No auth required — just a key file served at the site.

Usage:
    python push_to_index.py              # submit all URLs
    python push_to_index.py --dry-run    # print URLs only, no HTTP calls
    python push_to_index.py --new-only   # only submit URLs not yet tracked

Key file: public/d18d2e15c800f5c94ec2263b1321d00c.txt  (already deployed)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

# ── Config ────────────────────────────────────────────────────────────────────

SITE_URL    = "https://naukridhaba.in"
INDEXNOW_KEY = "d18d2e15c800f5c94ec2263b1321d00c"
INDEXNOW_API = "https://api.indexnow.org/indexnow"
BATCH_SIZE   = 10_000   # IndexNow max per request
RATE_DELAY   = 2        # seconds between batches

CONTENT_ROOT = Path(__file__).parent.parent / "content"
SUBMITTED_LOG = Path(__file__).parent / "indexnow_submitted.json"

TYPE_DIR = {
    "job":        "jobs",
    "result":     "results",
    "admit":      "admit-cards",
    "answer-key": "answer-keys",
    "syllabus":   "syllabus",
}

# Types that don't have a category subdirectory
FLAT_TYPES = {"answer-key", "syllabus"}


def _parse_frontmatter(path: Path) -> dict:
    """Extract key: value pairs from YAML frontmatter block."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm: dict = {}
    for line in m.group(1).splitlines():
        kv = re.match(r'^(\w+):\s*"?([^"]*)"?\s*$', line)
        if kv:
            fm[kv.group(1)] = kv.group(2).strip()
    return fm


def collect_urls() -> list[str]:
    """Walk content/ and build canonical URLs for every MDX file."""
    urls: list[str] = []

    # Static pages
    static = [
        "/",
        "/latest-jobs/",
        "/results/",
        "/admit-cards/",
        "/answer-keys/",
        "/syllabus/",
        "/search/",
    ]
    urls.extend(SITE_URL + p for p in static)

    # Category listing pages
    for type_key, dir_name in TYPE_DIR.items():
        if type_key in FLAT_TYPES:
            continue
        cat_dir = CONTENT_ROOT / dir_name
        if not cat_dir.exists():
            continue
        for cat in sorted(cat_dir.iterdir()):
            if cat.is_dir():
                urls.append(f"{SITE_URL}/{dir_name}/{cat.name}/")

    # Detail pages
    for type_key, dir_name in TYPE_DIR.items():
        base = CONTENT_ROOT / dir_name
        if not base.exists():
            continue

        if type_key in FLAT_TYPES:
            for mdx in sorted(base.glob("*.mdx")):
                slug = mdx.stem
                urls.append(f"{SITE_URL}/{dir_name}/{slug}/")
        else:
            for cat_dir in sorted(base.iterdir()):
                if not cat_dir.is_dir():
                    continue
                for mdx in sorted(cat_dir.glob("*.mdx")):
                    fm = _parse_frontmatter(mdx)
                    slug = fm.get("slug") or mdx.stem
                    category = fm.get("category") or cat_dir.name
                    urls.append(f"{SITE_URL}/{dir_name}/{category}/{slug}/")

    return urls


def load_submitted() -> set[str]:
    if SUBMITTED_LOG.exists():
        return set(json.loads(SUBMITTED_LOG.read_text()))
    return set()


def save_submitted(submitted: set[str]) -> None:
    SUBMITTED_LOG.write_text(json.dumps(sorted(submitted), indent=2))


def submit_batch(urls: list[str], dry_run: bool) -> bool:
    payload = {
        "host": "naukridhaba.in",
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": urls,
    }
    print(f"  Submitting {len(urls)} URLs to IndexNow ...", end=" ", flush=True)
    if dry_run:
        print("[DRY RUN — no request sent]")
        return True
    try:
        r = requests.post(
            INDEXNOW_API,
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        if r.status_code in (200, 202):
            print(f"OK ({r.status_code})")
            return True
        else:
            print(f"FAILED ({r.status_code}): {r.text[:200]}")
            return False
    except Exception as exc:
        print(f"ERROR: {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk IndexNow submission")
    parser.add_argument("--dry-run", action="store_true", help="Print URLs, no HTTP calls")
    parser.add_argument("--new-only", action="store_true", help="Only submit previously unsubmitted URLs")
    args = parser.parse_args()

    all_urls = collect_urls()
    print(f"Total URLs discovered: {len(all_urls)}")

    submitted = load_submitted()

    if args.new_only:
        to_submit = [u for u in all_urls if u not in submitted]
        print(f"New (not yet submitted): {len(to_submit)}")
    else:
        to_submit = all_urls
        print(f"Submitting all: {len(to_submit)}")

    if not to_submit:
        print("Nothing to submit.")
        return

    if args.dry_run:
        for u in to_submit[:20]:
            print(" ", u)
        if len(to_submit) > 20:
            print(f"  ... and {len(to_submit) - 20} more")

    # Submit in batches
    success_count = 0
    for i in range(0, len(to_submit), BATCH_SIZE):
        batch = to_submit[i : i + BATCH_SIZE]
        ok = submit_batch(batch, dry_run=args.dry_run)
        if ok:
            success_count += len(batch)
            submitted.update(batch)
        if not args.dry_run and i + BATCH_SIZE < len(to_submit):
            time.sleep(RATE_DELAY)

    if not args.dry_run:
        save_submitted(submitted)

    print(f"\nDone. Successfully submitted: {success_count} / {len(to_submit)} URLs")


if __name__ == "__main__":
    main()

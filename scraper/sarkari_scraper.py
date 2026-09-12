#!/usr/bin/env python3
"""
Naukri Dhaba content scraper.

    python scraper/sarkari_scraper.py                 # daily run (new posts + refresh open jobs)
    python scraper/sarkari_scraper.py --sitemap       # also crawl sarkariresult's sitemap for backfill
    python scraper/sarkari_scraper.py --dry-run       # fetch + parse, write nothing

Flow: listing pages → classify titles → skip already-known posts → fetch detail page →
parse → normalise → write MDX → validate (delete on failure) → mark seen.
A post is marked seen only after it was written or definitively rejected, so a
crash or timeout never loses posts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

SCRAPER_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRAPER_DIR.parent
sys.path.insert(0, str(SCRAPER_DIR))

from classify import classify_title  # noqa: E402
from detail_parser import parse_detail_page  # noqa: E402
from detail_parser.link_resolver import resolve_links  # noqa: E402
from fetcher import FetchError, fetch_soup, fetch_text, stats as fetch_stats  # noqa: E402
from listing import parse_listing  # noqa: E402
from mdx_generator import (CONTENT_ROOT, MIN_POST_DATE, TYPE_DIR_MAP, detail_to_raw, mdx_path_for,  # noqa: E402
                           normalize_frontmatter, parse_mdx, render_mdx)
from site_config import SOURCES  # noqa: E402
from textutil import parse_ddmmyyyy, slugify  # noqa: E402
from urls import is_source_host  # noqa: E402
from validate_content import validate_file  # noqa: E402

LOG_DIR = SCRAPER_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
SEEN_FILE = SCRAPER_DIR / "seen_items.json"
LAST_RUN_FILE = SCRAPER_DIR / "last_run.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_DIR / "scraper.log", encoding="utf-8"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("NaukriDhaba")

ARCHIVE_PAGES = {
    "sarkariresult": {k: f"https://www.sarkariresult.com/{p}/page/" for k, p in
                      (("job", "latestjob"), ("result", "result"), ("admit", "admitcard"),
                       ("answer-key", "answer-key"), ("syllabus", "syllabus"))},
    "freejobalert": {k: f"https://www.freejobalert.com/{p}/page/" for k, p in
                     (("job", "government-jobs"), ("result", "sarkariresult"), ("admit", "admit-card"),
                      ("answer-key", "answer-key"), ("syllabus", "syllabus"))},
    "rojgarresult": {"job": "https://www.rojgarresult.com/recruitments/page/",
                     "result": "https://www.rojgarresult.com/latest-result/page/",
                     "admit": "https://www.rojgarresult.com/admit-card/page/"},
    "sarkariexam": {"job": "https://www.sarkariexam.com/category/jobs/page/",
                    "result": "https://www.sarkariexam.com/exam-result/page/",
                    "admit": "https://www.sarkariexam.com/category/admit-card/page/",
                    "answer-key": "https://www.sarkariexam.com/category/answer-key/page/",
                    "syllabus": "https://www.sarkariexam.com/category/syllabus/page/"},
}


# ── state ─────────────────────────────────────────────────────────────────────

def url_id(url: str) -> str:
    u = re.sub(r"^https?://(www\.)?", "", url.strip().lower()).rstrip("/")
    return hashlib.md5(u.encode()).hexdigest()[:16]


def load_seen() -> set[str]:
    try:
        data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        return set(data) if isinstance(data, list) else set()
    except (OSError, ValueError):
        return set()


def save_seen(seen: set[str]) -> None:
    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=0) + "\n", encoding="utf-8")


def existing_index(content_root: Path) -> dict[str, Path]:
    """slug → path for every published post (used to skip cross-source duplicates)."""
    index: dict[str, Path] = {}
    for p in content_root.rglob("*.mdx"):
        index.setdefault(p.stem, p)
    return index


# ── discovery ─────────────────────────────────────────────────────────────────

def discover(listing_pages: int, deadline: float) -> list[dict]:
    found: dict[str, dict] = {}
    for source in SOURCES:
        name, base = source["name"], source["base"]
        for hint, url in source["urls"].items():
            pages = [url] + [f"{ARCHIVE_PAGES.get(name, {}).get(hint, '')}{n}/"
                             for n in range(2, listing_pages + 1) if ARCHIVE_PAGES.get(name, {}).get(hint)]
            for page_url in pages:
                if time.time() > deadline:
                    log.warning("time budget reached during discovery")
                    return list(found.values())
                try:
                    soup = fetch_soup(page_url)
                except FetchError as exc:
                    log.warning("[%s] listing %s failed: %s", name, page_url, exc)
                    break
                if soup is None:
                    break
                rows = parse_listing(soup, hint, base)
                log.info("[%s] %-10s %s → %d rows", name, hint, page_url, len(rows))
                if not rows:
                    break
                for r in rows:
                    r["source"] = name
                    found.setdefault(r["detail_url"], r)
    return list(found.values())


def discover_sitemap(deadline: float) -> list[dict]:
    """Backfill from sarkariresult's XML sitemap (only posts with lastmod ≥ MIN_POST_DATE)."""
    out: list[dict] = []
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    def entries(xml: str) -> list[tuple[str, str]]:
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            return []
        tag = "sm:sitemap" if root.tag.endswith("sitemapindex") else "sm:url"
        res = []
        for el in root.findall(tag, ns):
            loc = (el.findtext("sm:loc", namespaces=ns) or "").strip()
            lm = (el.findtext("sm:lastmod", namespaces=ns) or "").strip()[:10]
            if loc:
                res.append((loc, lm))
        return res

    try:
        root_xml = fetch_text("https://www.sarkariresult.com/sitemap.xml")
    except FetchError as exc:
        log.warning("sitemap fetch failed: %s", exc)
        return out
    if not root_xml:
        return out
    root_entries = entries(root_xml)
    subs = [u for u, _ in root_entries if u.endswith(".xml")]
    posts = [(u, lm) for u, lm in root_entries if not u.endswith(".xml")]
    for sub in subs:
        if time.time() > deadline:
            break
        try:
            xml = fetch_text(sub)
        except FetchError:
            continue
        if xml:
            posts.extend(entries(xml))
    for u, lm in posts:
        if lm and lm < MIN_POST_DATE:
            continue
        slug = urlparse(u).path.rstrip("/").rsplit("/", 1)[-1]
        title = slug.replace("-", " ").replace("_", " ").title()
        kind = classify_title(title)
        if not kind:
            continue
        out.append({"title": title, "detail_url": u, "kind": kind, "date": lm or "", "source": "sarkariresult",
                    "_rough_title": True})
    log.info("sitemap: %d candidate posts", len(out))
    return out


# ── processing ────────────────────────────────────────────────────────────────

def write_post(item: dict, content_root: Path, dry_run: bool) -> tuple[str, Path | None]:
    """Fetch, parse, normalise and write one post. Returns (status, path)."""
    url = item["detail_url"]
    try:
        soup = fetch_soup(url)
    except FetchError as exc:
        log.warning("  fetch failed: %s", exc)
        return "fetch_failed", None
    if soup is None:
        return "gone", None

    listing_item = {"title": item["title"], "detail_url": url, "source_detail_url": url,
                    "page_type": item["kind"], "date_str": item.get("date", ""), "dept": "",
                    "_rough_title": item.get("_rough_title", False)}
    detail = parse_detail_page(soup, listing_item, source_name=item["source"])
    resolve_links(detail)
    raw = detail_to_raw(detail, kind_hint=item["kind"])
    if not raw.get("publishedAt") and item.get("date"):
        raw["publishedAt"] = item["date"]
    fm = normalize_frontmatter(raw, base_url=url, scraped_at=detail.scraped_at)
    if fm is None:
        return "rejected", None
    if fm["publishedAt"] < MIN_POST_DATE:
        return "too_old", None
    path = mdx_path_for(fm, content_root)
    if path.exists():
        return "duplicate", path
    if dry_run:
        log.info("  [dry-run] would write %s", path.relative_to(content_root))
        return "written", path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_mdx(fm), encoding="utf-8")
    errs = validate_file(path)
    if errs:
        log.warning("  invalid after write, removed: %s", "; ".join(errs))
        path.unlink(missing_ok=True)
        return "invalid", None
    return "written", path


def refresh_open_jobs(content_root: Path, limit: int, deadline: float, dry_run: bool) -> int:
    """Re-scrape jobs whose deadline has not passed so date extensions and new links are picked up."""
    today = datetime.now().date()
    candidates: list[tuple[str, Path, dict, str]] = []
    for p in (content_root / "jobs").rglob("*.mdx"):
        try:
            fm, body = parse_mdx(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        src = fm.get("sourceUrl") or ""
        last = parse_ddmmyyyy(fm.get("lastDate"))
        if not last or last < today or not is_source_host(src) or "sitemap" in src:
            continue
        candidates.append((fm.get("updatedAt") or fm.get("publishedAt") or "", p, fm, body))
    candidates.sort(key=lambda t: t[0])
    refreshed = 0
    for _, path, old_fm, _body in candidates[:limit]:
        if time.time() > deadline:
            break
        url = old_fm["sourceUrl"]
        try:
            soup = fetch_soup(url)
        except FetchError:
            continue
        if soup is None:
            continue
        item = {"title": old_fm["title"], "detail_url": url, "source_detail_url": url,
                "page_type": "job", "dept": old_fm.get("dept", "")}
        detail = parse_detail_page(soup, item, source_name=old_fm.get("source", ""))
        resolve_links(detail)
        raw = detail_to_raw(detail, kind_hint="job")
        raw["publishedAt"] = old_fm.get("publishedAt")
        fm = normalize_frontmatter(raw, base_url=url, keep_category=old_fm.get("category"), keep_slug=path.stem)
        if fm is None or fm["type"] != "job":
            continue
        fm["publishedAt"] = old_fm["publishedAt"]
        changed = {k: fm.get(k) for k in ("lastDate", "applicationBegin", "examDate", "totalPosts", "importantLinks")} != \
                  {k: old_fm.get(k) for k in ("lastDate", "applicationBegin", "examDate", "totalPosts", "importantLinks")}
        if not changed:
            continue
        fm["updatedAt"] = today.isoformat()
        if not dry_run:
            path.write_text(render_mdx(fm), encoding="utf-8")
            if validate_file(path):
                path.write_text(render_mdx(old_fm, _body), encoding="utf-8")
                continue
        refreshed += 1
        log.info("  refreshed %s", path.relative_to(content_root))
    return refreshed


def run(args: argparse.Namespace) -> int:
    start = time.time()
    deadline = start + args.max_minutes * 60
    content_root = Path(args.content_root) if args.content_root else CONTENT_ROOT
    log.info("=" * 70)
    log.info("Naukri Dhaba scraper — %s  (budget %d min, max %d details)", datetime.now().strftime("%d %b %Y %H:%M"),
             args.max_minutes, args.max_details)
    if not os.environ.get("CF_WORKER_PROXY_URL"):
        log.warning("CF_WORKER_PROXY_URL not set — fetching sources directly")

    seen = load_seen()
    existing = existing_index(content_root)
    log.info("known posts: %d files, %d seen ids", len(existing), len(seen))

    items = discover(args.listing_pages, deadline)
    if args.sitemap:
        items.extend(discover_sitemap(deadline))
    log.info("discovered %d rows", len(items))

    queue: list[dict] = []
    picked_slugs: set[str] = set()
    for it in items:
        uid = url_id(it["detail_url"])
        if uid in seen:
            continue
        slug = slugify(it["title"])
        if slug in existing or slug in picked_slugs:
            seen.add(uid)
            continue
        picked_slugs.add(slug)
        it["_id"] = uid
        queue.append(it)
    # newest first so the daily budget goes to fresh posts
    queue.sort(key=lambda r: r.get("date", ""), reverse=True)
    log.info("new posts to fetch: %d (listings reported %d, already known %d)", len(queue), len(items), len(items) - len(queue))

    counts: dict[str, int] = {}
    written: dict[str, int] = {k: 0 for k in TYPE_DIR_MAP}
    processed = 0
    for it in queue:
        if processed >= args.max_details or time.time() > deadline:
            log.info("stopping: %s", "detail cap reached" if processed >= args.max_details else "time budget reached")
            break
        processed += 1
        log.info("[%s] %s", it["kind"], it["title"][:90])
        status, path = write_post(it, content_root, args.dry_run)
        counts[status] = counts.get(status, 0) + 1
        if status == "written" and path is not None:
            kind = path.parts[-3] if path.parent.parent.name in TYPE_DIR_MAP.values() else path.parent.name
            for k, d in TYPE_DIR_MAP.items():
                if d == kind:
                    written[k] += 1
            existing[path.stem] = path
            log.info("  written %s", path.relative_to(content_root))
        if status != "fetch_failed":
            seen.add(it["_id"])

    refreshed = 0
    if args.refresh > 0 and time.time() < deadline:
        refreshed = refresh_open_jobs(content_root, args.refresh, deadline, args.dry_run)

    if not args.dry_run:
        save_seen(seen)

    elapsed = int(time.time() - start)
    summary = {
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "elapsed_seconds": elapsed,
        "discovered": len(items),
        "queued": len(queue),
        "processed": processed,
        "written": written,
        "refreshed": refreshed,
        "statuses": counts,
        "fetch": dict(fetch_stats),
    }
    if not args.dry_run:
        LAST_RUN_FILE.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    log.info("DONE in %ds — written %s, refreshed %d, statuses %s, fetch %s", elapsed, written, refreshed, counts, dict(fetch_stats))
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as fh:
            fh.write(f"## Scraper run\n\n- discovered: {len(items)}\n- new written: {sum(written.values())} {written}\n"
                     f"- refreshed: {refreshed}\n- statuses: {counts}\n- fetch: {dict(fetch_stats)}\n- elapsed: {elapsed}s\n")
    if len(items) == 0:
        log.error("no listing page could be fetched — sources blocked or proxy down")
        return 2
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Naukri Dhaba scraper")
    ap.add_argument("--max-minutes", type=int, default=int(os.environ.get("SCRAPER_MAX_MINUTES", "45")))
    ap.add_argument("--max-details", type=int, default=int(os.environ.get("SCRAPER_MAX_DETAILS", "150")))
    ap.add_argument("--listing-pages", type=int, default=3, help="listing pages per source per type")
    ap.add_argument("--refresh", type=int, default=25, help="re-scrape up to N open jobs for updates")
    ap.add_argument("--sitemap", action="store_true", help="also crawl sarkariresult's sitemap (backfill)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--content-root", default="")
    args = ap.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

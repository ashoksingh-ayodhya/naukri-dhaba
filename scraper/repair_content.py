#!/usr/bin/env python3
"""One-off (idempotent) repair of every MDX file under content/.

- re-normalises all frontmatter through mdx_generator.normalize_frontmatter
- drops brand-corrupted / aggregator / social links
- regenerates shortDescription + body with the fact-only content writer
- moves files whose title says they are a different type (admit card filed under jobs, …)
- deletes junk pages (empty titles, listing pages scraped as posts, unparsable files)
- deletes posts published before MIN_POST_DATE or that cannot be dated at all
- deletes duplicates: the same source page written under several slugs
- rebuilds scraper/seen_items.json from the surviving files' sourceUrl

    python scraper/repair_content.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from content_writer import write_body  # noqa: E402
from mdx_generator import CONTENT_ROOT, DIR_TYPE_MAP, FLAT_TYPES, MIN_POST_DATE, mdx_path_for, normalize_frontmatter, parse_mdx, render_mdx  # noqa: E402
from sarkari_scraper import SEEN_FILE, url_id  # noqa: E402
from taxonomy import CATEGORY_SLUGS  # noqa: E402
from validate_content import validate_frontmatter  # noqa: E402


def duplicate_keys(fm: dict) -> list[tuple]:
    """Signals that two files are the same post. Both are deliberately narrow.

    A post's identity is its source page, so the same sourceUrl under different
    slugs is always a duplicate (the old scraper followed several listing URLs
    that all redirect to one canonical page). Beyond that, only an identical
    title published on the same day by the same site counts — aggregators
    republish an article under new ids. Title alone would wrongly merge real
    posts such as CTET January 2024 and CTET July 2024.
    """
    keys: list[tuple] = []
    src = (fm.get("sourceUrl") or "").strip().rstrip("/").lower()
    if src:
        keys.append(("source-url", src))
    title = re.sub(r"\s+", " ", fm["title"].strip().lower())
    keys.append(("republished", fm["type"], title, fm["publishedAt"], fm.get("source", "")))
    return keys


def _completeness(fm: dict) -> tuple:
    """Rank files in a duplicate group; the highest scoring one is kept."""
    slug_words = {w for w in fm["slug"].split("-") if w and not w.isdigit()}
    title_words = {w for w in re.findall(r"[a-z0-9]+", fm["title"].lower()) if not w.isdigit()}
    overlap = len(slug_words & title_words) / len(slug_words) if slug_words else 0.0
    return (
        len(fm),                                  # populated frontmatter fields
        len(fm.get("importantLinks") or []),
        round(overlap, 2),                        # slug describes the title
        fm.get("updatedAt") or fm["publishedAt"],
        -len(fm["slug"]),                         # prefer the canonical shorter slug
        fm["slug"],                               # deterministic tie-break
    )


def dedupe(dry_run: bool, stats: Counter) -> set[str]:
    """Delete duplicate posts, keeping the most complete file of each group."""
    records: list[tuple[Path, dict]] = []
    for path in sorted(CONTENT_ROOT.rglob("*.mdx")):
        try:
            fm, _ = parse_mdx(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        records.append((path, fm))

    groups: dict[tuple, list[tuple[Path, dict]]] = defaultdict(list)
    for path, fm in records:
        for key in duplicate_keys(fm):
            groups[key].append((path, fm))

    doomed: dict[Path, str] = {}
    for key, members in groups.items():
        alive = [(p, fm) for p, fm in members if p not in doomed]
        if len(alive) < 2:
            continue
        keeper = max(alive, key=lambda pair: _completeness(pair[1]))
        for path, _fm in alive:
            if path != keeper[0]:
                doomed[path] = f"{key[0]} of {keeper[0].relative_to(CONTENT_ROOT)}"

    for path, reason in sorted(doomed.items()):
        stats[f"deleted_duplicate_{reason.split(' of ')[0]}"] += 1
        print(f"DELETE (duplicate: {reason}) {path.relative_to(CONTENT_ROOT)}")
        if not dry_run:
            path.unlink()

    return {url_id(fm["sourceUrl"]) for path, fm in records
            if fm.get("sourceUrl") and path not in doomed}


def repair(dry_run: bool) -> Counter:
    stats: Counter = Counter()
    files = sorted(CONTENT_ROOT.rglob("*.mdx"))
    for path in files:
        rel = path.relative_to(CONTENT_ROOT)
        dir_type = DIR_TYPE_MAP.get(rel.parts[0])
        try:
            raw, _body = parse_mdx(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            stats["deleted_unparsable"] += 1
            print(f"DELETE (unparsable: {exc}) {rel}")
            if not dry_run:
                path.unlink()
            continue
        if not raw.get("type"):
            raw["type"] = dir_type
        current_cat = rel.parts[1] if dir_type not in FLAT_TYPES and len(rel.parts) == 3 else None
        fm = normalize_frontmatter(
            raw,
            base_url=raw.get("sourceUrl") or None,
            keep_category=current_cat if current_cat in CATEGORY_SLUGS else None,
            keep_slug=path.stem,
        )
        if fm is None:
            stats["deleted_junk"] += 1
            print(f"DELETE (junk) {rel}: {raw.get('title')!r}")
            if not dry_run:
                path.unlink()
            continue
        if fm["publishedAt"] < MIN_POST_DATE:
            stats["deleted_pre_cutoff"] += 1
            print(f"DELETE (published {fm['publishedAt']} < {MIN_POST_DATE}) {rel}")
            if not dry_run:
                path.unlink()
            continue
        target = mdx_path_for(fm)
        body = write_body(fm)
        errs = validate_frontmatter(fm, body, target)
        if errs:
            stats["still_invalid"] += 1
            print(f"INVALID {rel}: {'; '.join(errs)}")
            continue
        text = render_mdx(fm, body)
        if target.resolve() != path.resolve():
            if target.exists():
                stats["deleted_duplicate"] += 1
                print(f"DELETE (duplicate of {target.relative_to(CONTENT_ROOT)}) {rel}")
                if not dry_run:
                    path.unlink()
                continue
            stats[f"moved_{dir_type}->{fm['type']}"] += 1
            print(f"MOVE {rel} -> {target.relative_to(CONTENT_ROOT)}")
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                path.unlink()
                target.write_text(text, encoding="utf-8")
            continue
        if not dry_run:
            path.write_text(text, encoding="utf-8")
        stats["rewritten"] += 1

    seen = dedupe(dry_run, stats)
    if not dry_run:
        SEEN_FILE.write_text(json.dumps(sorted(seen), indent=0) + "\n", encoding="utf-8")
    stats["seen_ids"] = len(seen)
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    stats = repair(args.dry_run)
    print("\nSUMMARY")
    for k, v in sorted(stats.items()):
        print(f"  {k:32s} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

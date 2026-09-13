#!/usr/bin/env python3
"""One-off (idempotent) repair of every MDX file under content/.

- re-normalises all frontmatter through mdx_generator.normalize_frontmatter
- drops brand-corrupted / aggregator / social links
- regenerates shortDescription + body with the fact-only content writer
- moves files whose title says they are a different type (admit card filed under jobs, …)
- deletes junk pages (empty titles, listing pages scraped as posts, unparsable files)
- deletes posts published before MIN_POST_DATE or that cannot be dated at all
- rebuilds scraper/seen_items.json from the surviving files' sourceUrl

    python scraper/repair_content.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from content_writer import write_body  # noqa: E402
from mdx_generator import CONTENT_ROOT, DIR_TYPE_MAP, FLAT_TYPES, MIN_POST_DATE, mdx_path_for, normalize_frontmatter, parse_mdx, render_mdx  # noqa: E402
from sarkari_scraper import SEEN_FILE, url_id  # noqa: E402
from taxonomy import CATEGORY_SLUGS  # noqa: E402
from validate_content import validate_frontmatter  # noqa: E402


def repair(dry_run: bool) -> Counter:
    stats: Counter = Counter()
    seen: set[str] = set()
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
        if fm.get("sourceUrl"):
            seen.add(url_id(fm["sourceUrl"]))
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

#!/usr/bin/env python3
"""Delete posts published before a cut-off year.

Old job and admit-card pages describe openings that closed long ago, so they
cost build time and repository weight without helping a visitor. Results,
answer keys and syllabi are kept by default: those stay useful (and keep
drawing searches) long after the exam.

    python scraper/prune_content.py --before 2025 --types job,admit [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mdx_generator import CONTENT_ROOT, TYPE_DIR_MAP, parse_mdx  # noqa: E402


def prune(before: int, types: set[str], dry_run: bool) -> Counter:
    stats: Counter = Counter()
    cutoff = f"{before}-01-01"
    for type_name in sorted(types):
        directory = CONTENT_ROOT / TYPE_DIR_MAP[type_name]
        for path in sorted(directory.rglob("*.mdx")):
            try:
                fm, _ = parse_mdx(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            if fm.get("type") != type_name or str(fm.get("publishedAt", "")) >= cutoff:
                continue
            stats[f"{type_name} {str(fm['publishedAt'])[:4]}"] += 1
            stats["deleted"] += 1
            stats["bytes"] += path.stat().st_size
            if not dry_run:
                path.unlink()
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", type=int, required=True, help="delete posts published before this year")
    ap.add_argument("--types", default="job,admit", help="comma-separated content types")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    types = {t.strip() for t in args.types.split(",") if t.strip()}
    unknown = types - set(TYPE_DIR_MAP)
    if unknown:
        print(f"unknown type(s): {', '.join(sorted(unknown))}; valid: {', '.join(TYPE_DIR_MAP)}", file=sys.stderr)
        return 2

    stats = prune(args.before, types, args.dry_run)
    print(f"{'would delete' if args.dry_run else 'deleted'} {stats['deleted']} posts "
          f"({stats['bytes'] / 1e6:.1f} MB of MDX) published before {args.before}")
    for key, count in sorted(k for k in stats.items() if " " in k[0]):
        print(f"  {key:18s} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

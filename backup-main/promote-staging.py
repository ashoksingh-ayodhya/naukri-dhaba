#!/usr/bin/env python3
"""
Promote reviewed staging pages to the live site.

Usage:
  # List all staged items pending review
  python3 promote-staging.py --list

  # Promote a specific item by its index in the manifest
  python3 promote-staging.py --promote 0 1 3

  # Promote all items from a specific source
  python3 promote-staging.py --promote-source freejobalert

  # Promote all staged items (bulk approve)
  python3 promote-staging.py --promote-all

  # Remove a staged item without promoting (reject)
  python3 promote-staging.py --reject 2 5

Secondary source pages sit in staging/ until explicitly promoted.
Promoted pages pass through the same validation pipeline as primary ones.
"""

import sys
import os
import json
import shutil
import argparse
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from site_config import STAGING_DIR, SITE_URL

STAGING_ROOT = ROOT_DIR / STAGING_DIR
MANIFEST_FILE = STAGING_ROOT / "manifest.json"
VALIDATOR = ROOT_DIR / "validate-generated-site.py"


def load_manifest() -> list[dict]:
    if not MANIFEST_FILE.exists():
        return []
    try:
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_manifest(items: list[dict]) -> None:
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(
        json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def list_staged(items: list[dict]) -> None:
    if not items:
        print("No staged items pending review.")
        return
    print(f"\n{'Idx':<5} {'Source':<18} {'Kind':<8} {'Title':<55} {'Scraped At'}")
    print("-" * 110)
    for i, item in enumerate(items):
        title = item.get("title", "")[:52]
        print(
            f"{i:<5} {item.get('source', '?'):<18} {item.get('kind', '?'):<8} "
            f"{title:<55} {item.get('scraped_at', '?')[:19]}"
        )
    print(f"\nTotal: {len(items)} item(s) in staging.\n")


def validate_page(page_path: Path) -> bool:
    """Run the site validator on a single promoted page."""
    if not VALIDATOR.exists():
        print(f"  Warning: validator not found at {VALIDATOR}, skipping validation")
        return True
    try:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR)],
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR),
        )
        if result.returncode != 0:
            print(f"  Validation FAILED:\n{result.stdout}\n{result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"  Validation error: {e}")
        return False


def promote_items(items: list[dict], indices: list[int]) -> list[dict]:
    """Promote items at given indices from staging to live. Returns remaining items."""
    promoted = 0
    failed = 0
    remaining = []

    for i, item in enumerate(items):
        if i not in indices:
            remaining.append(item)
            continue

        rel_path = item.get("rel_path", "")
        staging_file = STAGING_ROOT / rel_path
        live_file = ROOT_DIR / rel_path

        if not staging_file.exists():
            print(f"  [{i}] SKIP — staging file missing: {staging_file}")
            remaining.append(item)
            failed += 1
            continue

        # Copy to live location
        live_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staging_file, live_file)
        print(f"  [{i}] Promoted: {rel_path}  (source: {item.get('source', '?')})")

        # Remove staging copy
        staging_file.unlink()
        promoted += 1

    # Run validation after all promotions
    if promoted > 0:
        print(f"\nRunning site validation after promoting {promoted} page(s)...")
        if not validate_page(ROOT_DIR):
            print("\nValidation FAILED. Rolling back promoted pages.")
            # Rollback: move promoted files back to staging
            for i in indices:
                if i < len(items):
                    rel_path = items[i].get("rel_path", "")
                    live_file = ROOT_DIR / rel_path
                    staging_file = STAGING_ROOT / rel_path
                    if live_file.exists() and not staging_file.exists():
                        staging_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(live_file), str(staging_file))
                        remaining.append(items[i])
                        print(f"  Rolled back: {rel_path}")
            failed += promoted
            promoted = 0

    print(f"\nPromoted: {promoted}, Failed: {failed}, Remaining in staging: {len(remaining)}")
    return remaining


def reject_items(items: list[dict], indices: list[int]) -> list[dict]:
    """Remove staged items without promoting them."""
    remaining = []
    rejected = 0
    for i, item in enumerate(items):
        if i not in indices:
            remaining.append(item)
            continue
        rel_path = item.get("rel_path", "")
        staging_file = STAGING_ROOT / rel_path
        if staging_file.exists():
            staging_file.unlink()
        print(f"  [{i}] Rejected: {rel_path}  (source: {item.get('source', '?')})")
        rejected += 1
    print(f"\nRejected: {rejected}, Remaining in staging: {len(remaining)}")
    return remaining


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote or reject staged pages")
    parser.add_argument("--list", action="store_true", help="List all staged items")
    parser.add_argument("--promote", nargs="+", type=int, help="Promote items by index")
    parser.add_argument("--promote-source", type=str, help="Promote all items from a source")
    parser.add_argument("--promote-all", action="store_true", help="Promote all staged items")
    parser.add_argument("--reject", nargs="+", type=int, help="Reject items by index")
    args = parser.parse_args()

    items = load_manifest()

    if args.list or (not args.promote and not args.promote_source and not args.promote_all and not args.reject):
        list_staged(items)
        return 0

    if args.promote:
        indices = set(args.promote)
        invalid = [i for i in indices if i < 0 or i >= len(items)]
        if invalid:
            print(f"Invalid indices: {invalid} (valid range: 0-{len(items)-1})")
            return 1
        items = promote_items(items, indices)
        save_manifest(items)

    if args.promote_source:
        indices = {i for i, item in enumerate(items) if item.get("source") == args.promote_source}
        if not indices:
            print(f"No staged items from source '{args.promote_source}'")
            return 1
        items = promote_items(items, indices)
        save_manifest(items)

    if args.promote_all:
        indices = set(range(len(items)))
        items = promote_items(items, indices)
        save_manifest(items)

    if args.reject:
        indices = set(args.reject)
        invalid = [i for i in indices if i < 0 or i >= len(items)]
        if invalid:
            print(f"Invalid indices: {invalid} (valid range: 0-{len(items)-1})")
            return 1
        items = reject_items(items, indices)
        save_manifest(items)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

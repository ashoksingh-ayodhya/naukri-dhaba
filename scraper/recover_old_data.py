#!/usr/bin/env python3
"""
Convert all old scraped JSON files (recovered from git history) to MDX.
Run from the repo root:  python3 scraper/recover_old_data.py /tmp/old_json_data
"""
import json
import sys
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "scraper"))

from detail_parser.models import DetailData
from mdx_generator import generate_mdx, is_within_date_range, MIN_POST_DATE

input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/old_json_data")
json_files = list(input_dir.rglob("*.json"))
print(f"Found {len(json_files)} JSON files in {input_dir}")

ok = skipped = failed = 0

for jf in sorted(json_files):
    try:
        data = json.loads(jf.read_text())
    except Exception as e:
        print(f"  [parse error] {jf}: {e}")
        failed += 1
        continue

    # Date filter
    post_date = data.get("post_date") or data.get("update_date") or data.get("scraped_at", "")[:10]
    if not is_within_date_range(post_date):
        skipped += 1
        continue

    # Map path type: admit-cards/ → admit, jobs/ → job, results/ → result, etc.
    path_parts = jf.relative_to(input_dir).parts
    dir_type = path_parts[0] if path_parts else ""
    type_map = {"jobs": "job", "results": "result", "admit-cards": "admit",
                "answer-keys": "answer-key", "syllabus": "syllabus"}
    page_type = type_map.get(dir_type, data.get("page_type", "job"))

    slug = jf.stem  # filename without .json

    try:
        dd = DetailData(
            title=data.get("title", ""),
            slug=slug,
            source=data.get("source", "sarkariresult"),
            source_detail_url=data.get("source_detail_url", ""),
            page_type=page_type,
            scraped_at=data.get("scraped_at", datetime.now().isoformat()),
            post_name=data.get("post_name", data.get("title", "")),
            short_description=data.get("short_description", ""),
            post_date=data.get("post_date", ""),
            update_date=data.get("update_date", ""),
            dept=data.get("dept", ""),
            organization_full_name=data.get("organization_full_name", ""),
            advertisement_number=data.get("advertisement_number", ""),
            dates=data.get("dates", {}),
            fees=data.get("fees", {}),
            fee_payment_method=data.get("fee_payment_method", ""),
            age_min=data.get("age_min"),
            age_max=data.get("age_max"),
            age_reference_date=data.get("age_reference_date", ""),
            total_posts=str(data.get("total_posts", "")) if data.get("total_posts") else "",
            vacancy_breakdown=data.get("vacancy_breakdown", []),
            qualification=data.get("qualification", ""),
            qualification_items=data.get("qualification_items", []),
            salary=data.get("salary", ""),
            how_to_apply=data.get("how_to_apply", []),
            important_links=data.get("important_links", []),
            apply_url=data.get("apply_url", ""),
            notification_url=data.get("notification_url", ""),
            result_url=data.get("result_url", ""),
            admit_url=data.get("admit_url", ""),
            official_website_url=data.get("official_website_url", ""),
        )
        mdx_path = generate_mdx(dd)
        if mdx_path:
            ok += 1
            if ok % 50 == 0:
                print(f"  [{ok}] {mdx_path.relative_to(ROOT_DIR)}")
        else:
            skipped += 1
    except Exception as e:
        print(f"  [mdx error] {jf.name}: {e}")
        failed += 1

print(f"\nDone: {ok} MDX files written, {skipped} skipped (date/none), {failed} failed")

"""
MDX Generator — converts DetailData objects into MDX content files.

Output path: content/{type_dir}/{category}/{slug}.mdx
Frontmatter mirrors the PostFrontmatter TypeScript interface exactly.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from detail_parser.models import DetailData

# ── Constants ─────────────────────────────────────────────────────────────────

CONTENT_ROOT = Path(__file__).parent.parent / "content"

TYPE_DIR_MAP = {
    "job": "jobs",
    "result": "results",
    "admit": "admit-cards",
    "answer-key": "answer-keys",
    "syllabus": "syllabus",
}

# Only scrape posts from this date onwards (YYYY-MM-DD)
MIN_POST_DATE = "2022-01-01"

# ── Category mapping ──────────────────────────────────────────────────────────

DEPT_TO_CATEGORY = {
    "SSC": "ssc",
    "RAILWAY": "railway",
    "BANKING": "banking",
    "BANK": "banking",
    "IBPS": "banking",
    "UPSC": "upsc",
    "POLICE": "police",
    "DEFENCE": "defence",
    "DEFENSE": "defence",
    "ARMY": "defence",
    "NAVY": "defence",
    "AIR FORCE": "defence",
    "TEACHING": "teaching",
    "EDUCATION": "teaching",
    "TET": "teaching",
    "PSU": "psu",
    "STATE PSC": "state-psc",
    "PSC": "state-psc",
    "POSTAL": "postal",
    "POST": "postal",
    "MEDICAL": "medical",
    "HEALTH": "medical",
    "AIIMS": "medical",
}


def dept_to_category(dept: str) -> str:
    """Map a department string to a URL-safe category slug."""
    upper = dept.upper().strip()
    for key, slug in DEPT_TO_CATEGORY.items():
        if key in upper:
            return slug
    return "government"


# ── Date filter ───────────────────────────────────────────────────────────────

def is_within_date_range(post_date: str) -> bool:
    """Return True if post_date >= MIN_POST_DATE (YYYY-MM-DD format)."""
    if not post_date:
        return True  # include if date unknown
    try:
        # Normalize to YYYY-MM-DD
        if "/" in post_date:
            parts = post_date.split("/")
            if len(parts) == 3:
                post_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        return post_date >= MIN_POST_DATE
    except Exception:
        return True


# ── YAML helpers ──────────────────────────────────────────────────────────────

def _yaml_str(value: str) -> str:
    """Safely quote a YAML string value."""
    if not value:
        return '""'
    # Escape double quotes inside
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def _yaml_list(items: list) -> str:
    """Format a list as YAML block sequence."""
    if not items:
        return "[]"
    lines = [""]
    for item in items:
        if isinstance(item, str):
            escaped = item.replace('"', '\\"')
            lines.append(f'  - "{escaped}"')
        else:
            lines.append(f"  - {json.dumps(item, ensure_ascii=False)}")
    return "\n".join(lines)


def _yaml_dict(d: dict) -> str:
    """Format a dict as inline YAML."""
    if not d:
        return "{}"
    parts = []
    for k, v in d.items():
        ek = k.replace('"', '\\"')
        ev = str(v).replace('"', '\\"')
        parts.append(f'"{ek}": "{ev}"')
    return "{" + ", ".join(parts) + "}"


# ── MDX body generator ────────────────────────────────────────────────────────

def build_mdx_body(detail: "DetailData") -> str:
    """Generate SEO-friendly MDX body text from detail data."""
    lines = []

    if detail.short_description:
        lines.append(detail.short_description)
        lines.append("")

    if detail.organization_full_name:
        lines.append(
            f"{detail.organization_full_name} has released an official notification "
            f"for {detail.post_name or detail.title}. "
        )

    if detail.total_posts:
        lines.append(f"A total of **{detail.total_posts}** posts are available for this recruitment.")

    if detail.dates:
        last = (
            detail.dates.get("Last Date for Registration")
            or detail.dates.get("Last Date for Apply Online")
            or detail.dates.get("Last Date")
            or detail.dates.get("Closing Date")
        )
        if last:
            lines.append(f"The last date to apply is **{last}**.")

    if detail.qualification:
        lines.append(f"Candidates must have {detail.qualification} as minimum educational qualification.")

    if detail.how_to_apply:
        lines.append("")
        lines.append("## How to Apply")
        lines.append("")
        for i, step in enumerate(detail.how_to_apply, 1):
            lines.append(f"{i}. {step}")

    return "\n".join(lines)


# ── Main generator ────────────────────────────────────────────────────────────

def generate_mdx(detail: "DetailData") -> Path | None:
    """
    Write a .mdx file for the given DetailData.

    Returns the written path, or None if skipped (date filter / no slug).
    """
    if not detail.slug:
        return None

    # Date filter: skip posts before MIN_POST_DATE
    if not is_within_date_range(detail.post_date):
        return None

    # Determine content type directory
    type_dir = TYPE_DIR_MAP.get(detail.page_type, "jobs")

    # Determine category
    category = dept_to_category(detail.dept)

    # Output path
    if detail.page_type in ("answer-key", "syllabus"):
        out_dir = CONTENT_ROOT / type_dir
    else:
        out_dir = CONTENT_ROOT / type_dir / category

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{detail.slug}.mdx"

    # Build frontmatter
    ld = detail.to_legacy_dict()

    frontmatter_lines = [
        "---",
        f"title: {_yaml_str(detail.title)}",
        f"slug: {_yaml_str(detail.slug)}",
        f'type: "{detail.page_type}"',
        f'category: "{category}"',
        f'dept: {_yaml_str(detail.dept)}',
        f"organization: {_yaml_str(detail.organization_full_name)}",
    ]

    if detail.advertisement_number:
        frontmatter_lines.append(f"advertisementNo: {_yaml_str(detail.advertisement_number)}")

    if detail.total_posts:
        frontmatter_lines.append(f"totalPosts: {_yaml_str(detail.total_posts)}")

    # Dates
    last_date = ld.get("last_date", "")
    if last_date and last_date not in ("Check Notification", ""):
        frontmatter_lines.append(f"lastDate: {_yaml_str(last_date)}")

    app_begin = ld.get("app_begin", "")
    if app_begin and app_begin not in ("Check Notification", ""):
        frontmatter_lines.append(f"applicationBegin: {_yaml_str(app_begin)}")

    exam_date = ld.get("exam_date", "")
    if exam_date and exam_date not in ("As per Schedule", ""):
        frontmatter_lines.append(f"examDate: {_yaml_str(exam_date)}")

    admit_date = ld.get("admit_release", "")
    if admit_date and admit_date not in ("Check Notification", ""):
        frontmatter_lines.append(f"admitDate: {_yaml_str(admit_date)}")

    result_date = ld.get("result_date", "")
    if result_date and result_date not in ("Check Notification", ""):
        frontmatter_lines.append(f"resultDate: {_yaml_str(result_date)}")

    # Age
    if detail.age_min is not None:
        frontmatter_lines.append(f"ageMin: {detail.age_min}")
    if detail.age_max is not None:
        frontmatter_lines.append(f"ageMax: {detail.age_max}")
    if detail.age_reference_date:
        frontmatter_lines.append(f"ageReferenceDate: {_yaml_str(detail.age_reference_date)}")
    if detail.age_relaxation_notes:
        frontmatter_lines.append(f"ageRelaxationNotes: {_yaml_str(detail.age_relaxation_notes)}")

    # Qualification
    if detail.qualification:
        frontmatter_lines.append(f"qualification: {_yaml_str(detail.qualification)}")
    if detail.qualification_items:
        frontmatter_lines.append(f"qualificationItems: {_yaml_list(detail.qualification_items)}")

    # Fee
    fee_general = ld.get("fee_general", "")
    if fee_general:
        frontmatter_lines.append(f"feeGeneral: {_yaml_str(fee_general)}")
    fee_sc_st = ld.get("fee_sc_st", "")
    if fee_sc_st:
        frontmatter_lines.append(f"feeSCST: {_yaml_str(fee_sc_st)}")
    if detail.fee_payment_method:
        frontmatter_lines.append(f"feePaymentMethod: {_yaml_str(detail.fee_payment_method)}")

    # Salary
    if detail.salary:
        frontmatter_lines.append(f"salary: {_yaml_str(detail.salary)}")

    # URLs
    if detail.apply_url and detail.apply_url != "#":
        frontmatter_lines.append(f"applyUrl: {_yaml_str(detail.apply_url)}")
    if detail.notification_url:
        frontmatter_lines.append(f"notificationUrl: {_yaml_str(detail.notification_url)}")
    if detail.result_url and detail.result_url != "#":
        frontmatter_lines.append(f"resultUrl: {_yaml_str(detail.result_url)}")
    if detail.admit_url and detail.admit_url != "#":
        frontmatter_lines.append(f"admitUrl: {_yaml_str(detail.admit_url)}")
    if detail.official_website_url:
        frontmatter_lines.append(f"officialWebsite: {_yaml_str(detail.official_website_url)}")

    # Dates
    if detail.source_detail_url:
        frontmatter_lines.append(f"sourceUrl: {_yaml_str(detail.source_detail_url)}")
    if detail.source:
        frontmatter_lines.append(f'source: "{detail.source}"')

    frontmatter_lines.append(f"publishedAt: {_yaml_str(detail.post_date or detail.scraped_at[:10])}")
    if detail.update_date:
        frontmatter_lines.append(f"updatedAt: {_yaml_str(detail.update_date)}")

    if detail.short_description:
        frontmatter_lines.append(f"shortDescription: {_yaml_str(detail.short_description[:300])}")

    # Complex fields as JSON-compatible YAML
    if detail.dates:
        frontmatter_lines.append(f"dates: {_yaml_dict(detail.dates)}")
    if detail.fees:
        frontmatter_lines.append(f"fees: {_yaml_dict(detail.fees)}")
    if detail.vacancy_breakdown:
        frontmatter_lines.append(f"vacancyBreakdown: {json.dumps(detail.vacancy_breakdown, ensure_ascii=False)}")
    if detail.important_links:
        frontmatter_lines.append(f"importantLinks: {json.dumps(detail.important_links, ensure_ascii=False)}")
    if detail.how_to_apply:
        frontmatter_lines.append(f"howToApply: {_yaml_list(detail.how_to_apply)}")

    frontmatter_lines.append("---")
    frontmatter = "\n".join(frontmatter_lines)

    # Build body
    body = build_mdx_body(detail)

    # Write file
    content = f"{frontmatter}\n\n{body}\n"
    out_path.write_text(content, encoding="utf-8")

    return out_path

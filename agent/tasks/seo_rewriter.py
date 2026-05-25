#!/usr/bin/env python3
"""
SEO Content Rewriter
====================
Primary agent task. For every MDX file in content/:

  1. Strip all "Sarkari Result" branding from every field
  2. Generate SEO-optimised shortDescription (200–250 words, keyword-rich,
     unique per job using its own data fields)
  3. Replace stock howToApply steps with clean Naukri Dhaba copy
  4. Enrich the MDX body with a full SEO article:
       - Lead paragraph (primary keyword × 3)
       - Key details section (vacancy, dates, fee, salary)
       - Eligibility section
       - How to apply numbered steps
       - FAQ block (5 Q&As with structured data hint)
  5. Set optimised title (≤ 60 chars) and meta description (≤ 155 chars)
     via shortDescription field used by generateMetadata()

Run once manually or via the daily agent workflow.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

CONTENT_ROOT = Path(__file__).parent.parent.parent / "content"
YEAR = datetime.now().year

# ── Branding cleaner ──────────────────────────────────────────────────────────

_BRAND = [
    (re.compile(r'(?i)sarkari\s*results?(?:\.(?:com|org|in))?'), "Naukri Dhaba"),
    (re.compile(r'(?i)www\.sarkariresults?\.(?:com|org|in)'),    "www.naukridhaba.in"),
    (re.compile(r'(?i)sarkariresults?\.(?:com|org|in)'),         "naukridhaba.in"),
]


def _clean(text: str) -> str:
    for pat, rep in _BRAND:
        text = pat.sub(rep, text)
    return text


# ── Frontmatter field extractor ───────────────────────────────────────────────

def _field(front: str, key: str) -> str:
    """Extract a simple scalar frontmatter field."""
    m = re.search(rf'^{re.escape(key)}:\s*"?(.*?)"?\s*$', front, re.M)
    return m.group(1).strip().strip('"') if m else ""


def _list_field(front: str, key: str) -> list[str]:
    """Extract a YAML list field."""
    m = re.search(rf'^{re.escape(key)}:\s*\n((?:\s+-.*\n)*)', front, re.M)
    if not m:
        return []
    items = []
    for line in m.group(1).splitlines():
        item = re.sub(r'^\s*-\s*"?(.*?)"?\s*$', r'\1', line).strip()
        if item:
            items.append(_clean(item))
    return items


# ── Content generators ────────────────────────────────────────────────────────

def _build_short_description(fm: dict) -> str:
    """Generate a 200-250 word SEO-optimised meta description / intro paragraph."""
    title   = fm["title"]
    org     = fm.get("organization") or fm.get("dept") or "the Government"
    posts   = fm.get("totalPosts", "")
    qual    = fm.get("qualification", "")
    last    = fm.get("lastDate", "")
    begin   = fm.get("applicationBegin", "")
    salary  = fm.get("salary", "")
    fee     = fm.get("feeGeneral", "")
    cat     = fm.get("category", "government")

    p = []

    # Para 1 — primary keyword intro
    if posts:
        p.append(
            f"{org} has officially announced the {title} recruitment {YEAR} notification. "
            f"A total of {posts} posts are available under this {title} recruitment drive. "
            f"Interested and eligible candidates can apply online for {title} {YEAR} through the official portal."
        )
    else:
        p.append(
            f"{org} has officially announced the {title} recruitment {YEAR} notification. "
            f"Interested and eligible candidates can apply online for this {cat} government job through the official portal."
        )

    # Para 2 — dates
    if begin and last:
        p.append(
            f"The online registration window for {title} opens on {begin} and closes on {last}. "
            f"Applicants are strongly advised to complete and submit their application form well before the last date "
            f"to avoid last-minute server issues."
        )
    elif last:
        p.append(
            f"The last date to apply online for {title} is {last}. "
            f"Do not wait until the deadline — submit your application form on Naukri Dhaba's direct apply link early."
        )

    # Para 3 — eligibility
    if qual:
        p.append(
            f"To be eligible for {title}, candidates must hold {qual} from a recognised university or board. "
            f"Age limit, reservation norms, and relaxation criteria are as per the official {org} notification."
        )

    # Para 4 — salary / fee
    extras = []
    if salary:
        extras.append(f"The pay scale offered is {salary}")
    if fee:
        extras.append(f"the application fee for General/OBC candidates is {fee}")
    if extras:
        p.append(
            f"{'. '.join(s[0].upper() + s[1:] for s in extras)}. "
            f"SC/ST/PwD categories may receive a fee waiver as per government rules."
        )

    # Para 5 — CTA
    p.append(
        f"Naukri Dhaba brings you the complete {title} details including eligibility criteria, "
        f"important dates, application fee, vacancy breakdown, and the direct official apply link. "
        f"Bookmark this page and check back for admit card and result updates."
    )

    desc = " ".join(p)
    return desc[:1000]  # keep long for body; generateMetadata slices to 160


def _build_how_to_apply(fm: dict) -> list[str]:
    """Generate clean, Naukri-Dhaba-branded how-to-apply steps."""
    org   = fm.get("organization") or fm.get("dept") or "the organisation"
    title = fm["title"]
    return [
        f"Go to the official website of {org} or use the direct apply link on this page at Naukri Dhaba.",
        f"Find the '{title}' recruitment notification and click 'Apply Online'.",
        "Click on 'New Registration' and fill in your name, mobile number, and email ID to create an account.",
        "Log in with your credentials and fill in Part I of the application — personal details, educational qualifications, and work experience.",
        "Upload a recent passport-size photograph, your signature, and all required documents in the specified file size and format.",
        "Pay the application fee online via Debit Card, Credit Card, Net Banking, or UPI.",
        "Preview your completed application form carefully. Correct any errors before final submission.",
        "Submit the form and download the confirmation page. Keep a printed copy safe for exam day and document verification.",
    ]


def _build_faq(fm: dict) -> str:
    """Return an SEO FAQ section (plain text, not JSON-LD — that's in page.tsx)."""
    title = fm["title"]
    org   = fm.get("organization") or fm.get("dept") or "the authority"
    last  = fm.get("lastDate") or "as per official notification"
    posts = fm.get("totalPosts", "")
    qual  = fm.get("qualification", "Check official notification")
    salary = fm.get("salary", "")

    qa = [
        (
            f"What is the last date to apply for {title}?",
            f"The last date to apply for {title} is {last}. Candidates must submit their online application before this date. "
            f"No applications are accepted after the deadline under any circumstances."
        ),
        (
            f"How many total vacancies are there in {title}?",
            f"{'There are ' + posts + ' total vacancies in ' + title + '.' if posts else 'The total vacancy count for ' + title + ' is mentioned in the official notification released by ' + org + '.'} "
            f"The vacancy breakup by category (General, OBC, SC, ST, EWS) is available in the official notification."
        ),
        (
            f"What is the educational qualification for {title}?",
            f"The minimum educational qualification required for {title} is {qual}. "
            f"Candidates should verify eligibility from the official notification as requirements may vary by post."
        ),
        (
            f"What is the salary for {title}?",
            f"{'The selected candidates for ' + title + ' will receive a pay scale of ' + salary + ' as per the government pay matrix.' if salary else 'The salary details for ' + title + ' are mentioned in the official notification by ' + org + '. Please refer to the official advertisement for the exact pay scale.'}"
        ),
        (
            f"How to apply for {title}?",
            f"To apply for {title}: (1) Visit the official website of {org}. "
            f"(2) Find the {title} notification and click Apply Online. "
            f"(3) Register, fill the form, upload documents, pay the fee, and submit. "
            f"(4) Download your application confirmation page. All steps are detailed above on this Naukri Dhaba page."
        ),
    ]

    lines = ["\n## Frequently Asked Questions (FAQ)\n"]
    for q, a in qa:
        lines.append(f"### {q}\n\n{a}\n")
    return "\n".join(lines)


def _build_mdx_body(fm: dict) -> str:
    """Build a rich, keyword-optimised MDX body replacing the scraped stub."""
    title   = fm["title"]
    org     = fm.get("organization") or fm.get("dept") or "the Government"
    posts   = fm.get("totalPosts", "")
    qual    = fm.get("qualification", "")
    last    = fm.get("lastDate", "")
    begin   = fm.get("applicationBegin", "")
    salary  = fm.get("salary", "")
    fee_g   = fm.get("feeGeneral", "")
    fee_s   = fm.get("feeSCST", "")
    age_min = fm.get("ageMin", "")
    age_max = fm.get("ageMax", "")
    cat     = fm.get("category", "government")

    sections = []

    # Lead paragraph
    sections.append(_build_short_description(fm))

    # Key details table
    rows = []
    if org:         rows.append(("Organisation", org))
    if posts:       rows.append(("Total Posts", posts))
    if cat:         rows.append(("Job Category", cat.replace("-", " ").title()))
    if begin:       rows.append(("Application Start", begin))
    if last:        rows.append(("Last Date to Apply", last))
    if age_min and age_max: rows.append(("Age Limit", f"{age_min} – {age_max} years"))
    if qual:        rows.append(("Qualification", qual))
    if salary:      rows.append(("Pay Scale", salary))
    if fee_g:       rows.append(("Application Fee (General/OBC)", fee_g))
    if fee_s:       rows.append(("Application Fee (SC/ST/PwD)", fee_s))

    if rows:
        table_rows = "\n".join(f"| {k} | {v} |" for k, v in rows)
        sections.append(
            f"\n## {title} — Key Details\n\n"
            f"| Detail | Information |\n|--------|-------------|\n{table_rows}\n"
        )

    # Eligibility
    if qual or (age_min and age_max):
        elig = [f"\n## Eligibility Criteria for {title}\n"]
        if qual:
            elig.append(
                f"**Educational Qualification:** Candidates must hold {qual} from a recognised university or institution. "
                f"Please check the official {org} notification for post-wise qualification details."
            )
        if age_min and age_max:
            elig.append(
                f"\n**Age Limit:** The minimum age to apply is {age_min} years and the maximum age is {age_max} years. "
                f"Age relaxation is applicable for SC/ST/OBC/PwD candidates as per Government of India norms."
            )
        sections.append("\n".join(elig))

    # How to apply
    steps = _build_how_to_apply(fm)
    steps_text = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    sections.append(f"\n## How to Apply for {title}\n\n{steps_text}\n")

    # FAQ
    sections.append(_build_faq(fm))

    # Disclaimer
    sections.append(
        f"\n---\n*This page is maintained by Naukri Dhaba for informational purposes. "
        f"All {title} details are sourced from official {org} notifications. "
        f"Candidates are advised to verify all information from the official website before applying.*\n"
    )

    return "\n".join(sections)


# ── Field updater ─────────────────────────────────────────────────────────────

def _set_field(front: str, key: str, value: str) -> str:
    """Insert or replace a scalar YAML field in the frontmatter string."""
    escaped = value.replace('"', '\\"')
    new_line = f'{key}: "{escaped}"'
    if re.search(rf'^{re.escape(key)}:', front, re.M):
        front = re.sub(rf'^{re.escape(key)}:.*$', new_line, front, flags=re.M)
    else:
        # Append before closing ---
        front = front.rstrip() + f"\n{new_line}"
    return front


def _set_list_field(front: str, key: str, items: list[str]) -> str:
    """Insert or replace a YAML list field."""
    lines = [f'{key}: ']
    for item in items:
        lines.append(f'  - "{item.replace(chr(34), chr(92)+chr(34))}"')
    new_block = "\n".join(lines)
    # Remove existing block
    front = re.sub(
        rf'^{re.escape(key)}:\s*\n(?:\s+-.*\n)*',
        '',
        front,
        flags=re.M,
    )
    # Also remove inline form
    front = re.sub(rf'^{re.escape(key)}:.*$', '', front, flags=re.M)
    return front.rstrip() + "\n" + new_block


# ── File rewriter ─────────────────────────────────────────────────────────────

def rewrite_file(fpath: Path, dry_run: bool = False) -> bool:
    """Rewrite a single MDX file with full SEO optimisation. Returns True if changed."""
    original = fpath.read_text(encoding="utf-8")

    parts = original.split("---", 2)
    if len(parts) < 3:
        return False

    front = parts[1]
    # body  = parts[2]  # we replace the body entirely for job pages

    # Extract all fields
    fm = {
        "title":           _clean(_field(front, "title")),
        "organization":    _clean(_field(front, "organization")),
        "dept":            _clean(_field(front, "dept")),
        "totalPosts":      _field(front, "totalPosts"),
        "lastDate":        _field(front, "lastDate"),
        "applicationBegin": _field(front, "applicationBegin"),
        "qualification":   _clean(_field(front, "qualification")),
        "salary":          _field(front, "salary"),
        "feeGeneral":      _field(front, "feeGeneral"),
        "feeSCST":         _field(front, "feeSCST"),
        "applyUrl":        _field(front, "applyUrl"),
        "category":        _field(front, "category"),
        "ageMin":          _field(front, "ageMin"),
        "ageMax":          _field(front, "ageMax"),
        "type":            _field(front, "type"),
    }

    if not fm["title"]:
        return False

    # Clean all text fields in frontmatter
    for key in ("title", "organization", "dept", "qualification", "salary",
                "feeGeneral", "feeSCST", "feePaymentMethod"):
        val = _field(front, key)
        cleaned = _clean(val)
        if cleaned != val and val:
            front = _set_field(front, key, cleaned)

    # Generate SEO content
    short_desc = _build_short_description(fm)

    # Update shortDescription in frontmatter
    front = _set_field(front, "shortDescription", short_desc[:400])

    # For jobs only: replace howToApply steps
    if fm.get("type") == "job":
        new_steps = _build_how_to_apply(fm)
        front = _set_list_field(front, "howToApply", new_steps)

    # Rebuild body (jobs only — results/admits keep their body)
    if fm.get("type") == "job":
        new_body = "\n" + _build_mdx_body(fm) + "\n"
    else:
        # For results/admits: just clean branding in body
        new_body = _clean(parts[2])

    new_content = "---" + front.rstrip("\n") + "\n---" + new_body

    if new_content == original:
        return False

    if not dry_run:
        fpath.write_text(new_content, encoding="utf-8")
    return True


# ── Main entry ────────────────────────────────────────────────────────────────

def run(dry_run: bool = False) -> int:
    """Rewrite all MDX files. Returns number of files changed."""
    files = list(CONTENT_ROOT.rglob("*.mdx"))
    changed = 0
    errors  = 0

    for fpath in files:
        try:
            if rewrite_file(fpath, dry_run=dry_run):
                changed += 1
        except Exception as exc:
            print(f"  [seo_rewriter] ERROR {fpath.name}: {exc}", file=sys.stderr)
            errors += 1

    print(
        f"[seo_rewriter] {'Would change' if dry_run else 'Changed'} "
        f"{changed}/{len(files)} files ({errors} errors)."
    )
    return changed


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    run(dry_run=args.dry_run)

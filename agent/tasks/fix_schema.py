#!/usr/bin/env python3
"""
Schema Code Fixer
=================
Agent task: audit and fix schema markup gaps in lib/seo.ts and page components.

Reads agent/knowledge.md as its spec, then applies idempotent targeted patches:
  1. lib/seo.ts — buildOrganizationJsonLd logo as ImageObject
  2. lib/seo.ts — buildAdmitJsonLd: add endDate + image
  3. lib/seo.ts — buildSyllabusJsonLd: add teaches field
  4. app/answer-keys/[slug]/page.tsx — wire buildAnswerKeyJsonLd
  5. app/syllabus/[slug]/page.tsx — wire buildSyllabusJsonLd
  6. app/jobs/[category]/[slug]/page.tsx — wire buildFaqJsonLd
  7. app/jobs/[category]/page.tsx — wire buildListingPageJsonLd
  8. app/results/[category]/page.tsx — wire buildListingPageJsonLd
  9. app/admit-cards/[category]/page.tsx — wire buildListingPageJsonLd

Returns: number of individual patches applied (0 = already up to date).
Called by agent.py as: from tasks.fix_schema import run
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
SEO_TS    = REPO_ROOT / "lib" / "seo.ts"
APP_DIR   = REPO_ROOT / "app"

_applied: list[str] = []


def _patch(fpath: Path, old: str, new: str, label: str) -> bool:
    """
    Apply a targeted, idempotent string replacement.
    Returns True if the file was changed, False if already applied or not found.
    """
    try:
        text = fpath.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"[fix_schema] ⚠️  File not found: {fpath}", file=sys.stderr)
        return False

    if old not in text:
        # Check if already applied by seeing if the first distinctive line of `new` is present
        check_line = next((l.strip() for l in new.split("\n") if l.strip()), new[:60])
        if check_line in text:
            print(f"[fix_schema] ✓ Already applied: {label}")
        else:
            print(f"[fix_schema] ⚠️  Pattern not found for: {label}", file=sys.stderr)
        return False

    fpath.write_text(text.replace(old, new, 1), encoding="utf-8")
    _applied.append(label)
    print(f"[fix_schema] ✅ Applied: {label}", flush=True)
    return True


# ── lib/seo.ts fixes ──────────────────────────────────────────────────────────

def fix_organization_logo() -> bool:
    """
    buildOrganizationJsonLd: logo must be ImageObject per Google's spec.
    A bare URL string will not trigger the Organization logo rich result.
    """
    return _patch(
        SEO_TS,
        '    logo: `${siteConfig.url}/logo.svg`,',
        (
            '    logo: {\n'
            '      "@type": "ImageObject",\n'
            '      url: `${siteConfig.url}/logo.svg`,\n'
            '      width: 512,\n'
            '      height: 512,\n'
            '    },'
        ),
        "seo.ts: buildOrganizationJsonLd — logo → ImageObject",
    )


def fix_admit_end_date_and_image() -> bool:
    """
    buildAdmitJsonLd: endDate is required by Google Event schema.
    image improves rich result display in search.
    """
    return _patch(
        SEO_TS,
        (
            "    startDate: examDateIso || datePosted,\n"
            "    eventStatus:"
        ),
        (
            "    startDate: examDateIso || datePosted,\n"
            "    endDate: examDateIso || datePosted,\n"
            "    image: `${siteConfig.url}${siteConfig.ogImage}`,\n"
            "    eventStatus:"
        ),
        "seo.ts: buildAdmitJsonLd — add endDate + image",
    )


def fix_syllabus_teaches() -> bool:
    """
    buildSyllabusJsonLd: teaches improves Course schema quality for Google.
    """
    return _patch(
        SEO_TS,
        (
            "    isAccessibleForFree: true,\n"
            "    hasCourseInstance:"
        ),
        (
            "    isAccessibleForFree: true,\n"
            '    teaches: fm.qualification || "Government Exam Syllabus",\n'
            "    hasCourseInstance:"
        ),
        "seo.ts: buildSyllabusJsonLd — add teaches",
    )


# ── Page component wiring ─────────────────────────────────────────────────────

def wire_answer_key_schema() -> bool:
    """Wire buildAnswerKeyJsonLd into the answer-key detail page."""
    page = APP_DIR / "answer-keys" / "[slug]" / "page.tsx"
    c1 = _patch(
        page,
        'import { buildMetadata, buildBreadcrumbJsonLd } from "@/lib/seo";',
        'import { buildMetadata, buildBreadcrumbJsonLd, buildAnswerKeyJsonLd } from "@/lib/seo";',
        "answer-keys/[slug]/page.tsx — import buildAnswerKeyJsonLd",
    )
    c2 = _patch(
        page,
        (
            '      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(buildBreadcrumbJsonLd(breadcrumbs)) }} />\n'
            '      <div'
        ),
        (
            '      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(buildBreadcrumbJsonLd(breadcrumbs)) }} />\n'
            '      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(buildAnswerKeyJsonLd(fm, pageUrl)) }} />\n'
            '      <div'
        ),
        "answer-keys/[slug]/page.tsx — wire buildAnswerKeyJsonLd tag",
    )
    return c1 or c2


def wire_syllabus_schema() -> bool:
    """Wire buildSyllabusJsonLd into the syllabus detail page."""
    page = APP_DIR / "syllabus" / "[slug]" / "page.tsx"
    c1 = _patch(
        page,
        'import { buildMetadata, buildBreadcrumbJsonLd } from "@/lib/seo";',
        'import { buildMetadata, buildBreadcrumbJsonLd, buildSyllabusJsonLd } from "@/lib/seo";',
        "syllabus/[slug]/page.tsx — import buildSyllabusJsonLd",
    )
    c2 = _patch(
        page,
        (
            '      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(buildBreadcrumbJsonLd(breadcrumbs)) }} />\n'
            '      <div'
        ),
        (
            '      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(buildBreadcrumbJsonLd(breadcrumbs)) }} />\n'
            '      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(buildSyllabusJsonLd(fm, pageUrl)) }} />\n'
            '      <div'
        ),
        "syllabus/[slug]/page.tsx — wire buildSyllabusJsonLd tag",
    )
    return c1 or c2


def wire_faq_schema_job_page() -> bool:
    """
    Wire buildFaqJsonLd into the job detail page.
    FAQs are written into MDX body as **Q:**/**A:** pairs by the SEO rewriter.
    The regex extracts them at build time and emits FAQPage JSON-LD.
    """
    page = APP_DIR / "jobs" / "[category]" / "[slug]" / "page.tsx"

    c1 = _patch(
        page,
        'import { buildMetadata, buildJobJsonLd, buildBreadcrumbJsonLd } from "@/lib/seo";',
        'import { buildMetadata, buildJobJsonLd, buildBreadcrumbJsonLd, buildFaqJsonLd } from "@/lib/seo";',
        "jobs/[category]/[slug]/page.tsx — import buildFaqJsonLd",
    )

    # Guard: only wire FAQ block if it's not already there.
    # The old pattern is a prefix of the new pattern so we must check explicitly.
    try:
        text = page.read_text(encoding="utf-8")
    except FileNotFoundError:
        return c1

    faq_block = (
        '      {(() => {\n'
        '        const faqs: Array<{question: string; answer: string}> = [];\n'
        '        const faqRe = /\\*\\*Q:\\*\\*\\s*(.+?)\\s*\\n\\s*\\*\\*A:\\*\\*\\s*(.+?)(?=\\n\\s*\\*\\*Q:|$)/gs;\n'
        '        let m;\n'
        '        while ((m = faqRe.exec(content || "")) !== null) {\n'
        '          faqs.push({ question: m[1].trim(), answer: m[2].trim() });\n'
        '        }\n'
        '        return faqs.length > 0 ? (\n'
        '          <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(buildFaqJsonLd(faqs)) }} />\n'
        '        ) : null;\n'
        '      })()}'
    )

    label = "jobs/[category]/[slug]/page.tsx — wire buildFaqJsonLd"
    if "faqRe" in text:
        print(f"[fix_schema] ✓ Already applied: {label}")
        return c1

    breadcrumb_tag = '      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(buildBreadcrumbJsonLd(breadcrumbs)) }} />'
    if breadcrumb_tag not in text:
        print(f"[fix_schema] ⚠️  Pattern not found for: {label}", file=sys.stderr)
        return c1

    new_text = text.replace(
        breadcrumb_tag,
        breadcrumb_tag + "\n" + faq_block,
        1,
    )
    page.write_text(new_text, encoding="utf-8")
    _applied.append(label)
    print(f"[fix_schema] ✅ Applied: {label}", flush=True)
    return True


def _wire_listing_page(
    page: Path,
    get_all_posts_call: str,
    url_prefix: str,
    label: str,
    page_label: str,
) -> bool:
    """
    Wire buildListingPageJsonLd into a category listing page.
    Injects schema script as first element inside the return fragment.
    """
    if not page.exists():
        print(f"[fix_schema] ⚠️  Not found: {page}", file=sys.stderr)
        return False

    text = page.read_text(encoding="utf-8")
    if "buildListingPageJsonLd" in text:
        print(f"[fix_schema] ✓ Already applied: {page_label}")
        return False

    changed = False

    # 1. Extend seo import
    old_seo_import = 'import { buildMetadata } from "@/lib/seo";'
    new_seo_import = 'import { buildMetadata, buildListingPageJsonLd } from "@/lib/seo";'
    if old_seo_import in text:
        text = text.replace(old_seo_import, new_seo_import, 1)
        changed = True

    # 2. Add siteConfig to config import
    old_cfg_import = 'import { CATEGORIES } from "@/config/site";'
    new_cfg_import = 'import { CATEGORIES, siteConfig } from "@/config/site";'
    if old_cfg_import in text:
        text = text.replace(old_cfg_import, new_cfg_import, 1)
        changed = True

    # 3. Inject listing URL + items variables, wrap return with fragment + schema script.
    # Try both: with blank line (some pages) and without (others).
    for sep in ("\n\n", "\n"):
        old_return = (
            f"  const posts = {get_all_posts_call};{sep}"
            "  return (\n"
            '    <div className="max-w-7xl mx-auto px-4 py-6">'
        )
        new_return = (
            f"  const posts = {get_all_posts_call};\n"
            f"  const _listUrl = `${{siteConfig.url}}{url_prefix}/${{category}}/`;\n"
            f"  const _items = posts.slice(0, 50).map((p: {{title: string; slug: string}}) => ({{\n"
            f"    name: p.title,\n"
            f"    url: `${{siteConfig.url}}{url_prefix}/${{category}}/${{p.slug}}/`,\n"
            f"  }}));\n"
            "  return (\n"
            "    <>\n"
            f'      <script type="application/ld+json" dangerouslySetInnerHTML={{{{ __html: JSON.stringify(buildListingPageJsonLd(`${{cat?.fullName || category}} {label} ${{YEAR}}`, _listUrl, _items)) }}}} />\n'
            '      <div className="max-w-7xl mx-auto px-4 py-6">'
        )
        if old_return in text:
            text = text.replace(old_return, new_return, 1)
            changed = True
            break

    # 4. Close the fragment (replace the final closing div+return).
    # Look for pattern after adding the fragment open.
    if "    </>\n  );\n}" not in text:
        old_close = "    </div>\n  );\n}"
        new_close = "    </div>\n    </>\n  );\n}"
        idx = text.rfind(old_close)
        if idx != -1:
            text = text[:idx] + new_close + text[idx + len(old_close):]
            changed = True

    if changed:
        page.write_text(text, encoding="utf-8")
        _applied.append(page_label)
        print(f"[fix_schema] ✅ Applied: {page_label}", flush=True)

    return changed


def wire_listing_pages() -> bool:
    """Wire buildListingPageJsonLd into all three category listing pages."""
    configs = [
        (
            APP_DIR / "jobs" / "[category]" / "page.tsx",
            'getAllPosts("job", category)',
            "/jobs",
            "Jobs",
            "jobs/[category]/page.tsx — wire buildListingPageJsonLd",
        ),
        (
            APP_DIR / "results" / "[category]" / "page.tsx",
            'getAllPosts("result", category)',
            "/results",
            "Results",
            "results/[category]/page.tsx — wire buildListingPageJsonLd",
        ),
        (
            APP_DIR / "admit-cards" / "[category]" / "page.tsx",
            'getAllPosts("admit", category)',
            "/admit-cards",
            "Admit Cards",
            "admit-cards/[category]/page.tsx — wire buildListingPageJsonLd",
        ),
    ]
    changed = False
    for (path, get_posts, url_prefix, label, page_label) in configs:
        changed |= _wire_listing_page(path, get_posts, url_prefix, label, page_label)
    return changed


# ── Entry point ───────────────────────────────────────────────────────────────

def run() -> int:
    """
    Run all schema fixes. Idempotent — safe to run on every agent cycle.
    Returns count of patches applied (0 means already up to date).
    """
    knowledge_path = Path(__file__).parent.parent / "knowledge.md"
    print(f"[fix_schema] Spec: {knowledge_path} ({knowledge_path.stat().st_size} bytes)", flush=True)

    print("[fix_schema] --- lib/seo.ts ---", flush=True)
    fix_organization_logo()
    fix_admit_end_date_and_image()
    fix_syllabus_teaches()

    print("[fix_schema] --- page components ---", flush=True)
    wire_answer_key_schema()
    wire_syllabus_schema()
    wire_faq_schema_job_page()
    wire_listing_pages()

    n = len(_applied)
    if n:
        print(f"[fix_schema] {n} fix(es) applied:", flush=True)
        for f in _applied:
            print(f"  • {f}", flush=True)
    else:
        print("[fix_schema] All schema checks passed — nothing to fix.", flush=True)
    return n


if __name__ == "__main__":
    print(run())

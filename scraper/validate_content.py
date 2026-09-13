#!/usr/bin/env python3
"""Validate every MDX file under content/. Exit 1 when any file is invalid.

    python scraper/validate_content.py            # whole tree
    python scraper/validate_content.py path.mdx   # specific files
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mdx_generator import CONTENT_ROOT, DIR_TYPE_MAP, FLAT_TYPES, LINK_TYPES, parse_mdx  # noqa: E402
from taxonomy import CATEGORY_SLUGS  # noqa: E402
from textutil import parse_ddmmyyyy  # noqa: E402
from urls import is_social, is_source_host  # noqa: E402

_BRAND_RE = re.compile(r"(?i)sarkari\s*result|freejobalert|rojgar\s*result|sarkariexam")
_DDMMYYYY_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_URL_FIELDS = ("applyUrl", "notificationUrl", "resultUrl", "admitUrl", "officialWebsite")
_TEXT_FIELDS = ("title", "organization", "dept", "qualification", "salary", "shortDescription",
                "feePaymentMethod", "ageRelaxationNotes", "advertisementNo")


def _url_ok(u: object) -> str | None:
    if not isinstance(u, str) or not re.match(r"^https?://[^\s/]+\.[a-z]{2,}", u, re.I):
        return "not an absolute http(s) URL"
    if " " in u or "Naukri Dhaba" in u:
        return "malformed URL"
    if is_source_host(u):
        return "links to an aggregator host"
    if is_social(u):
        return "links to a social/shortener host"
    return None


def validate_frontmatter(fm: dict, body: str, path: Path) -> list[str]:
    errs: list[str] = []
    p = path.resolve()
    if p.parent.name in DIR_TYPE_MAP:
        parts: tuple[str, ...] = (p.parent.name, p.name)
    elif p.parent.parent.name in DIR_TYPE_MAP:
        parts = (p.parent.parent.name, p.parent.name, p.name)
    else:
        parts = ()

    for key in ("title", "slug", "type", "category", "publishedAt", "shortDescription"):
        if not fm.get(key):
            errs.append(f"missing {key}")
    if errs:
        return errs

    if fm["slug"] != path.stem:
        errs.append(f"slug '{fm['slug']}' != filename '{path.stem}'")
    if not re.match(r"^[a-z0-9][a-z0-9-]{4,}$", fm["slug"]):
        errs.append("slug has invalid characters")
    if len(parts) >= 1 and parts[0] in DIR_TYPE_MAP and DIR_TYPE_MAP[parts[0]] != fm["type"]:
        errs.append(f"type '{fm['type']}' does not match directory '{parts[0]}'")
    if fm["category"] not in CATEGORY_SLUGS:
        errs.append(f"unknown category '{fm['category']}'")
    if fm["type"] not in FLAT_TYPES and len(parts) >= 3 and parts[1] != fm["category"]:
        errs.append(f"category '{fm['category']}' does not match directory '{parts[1]}'")
    if len(fm["title"]) < 10 or fm["title"].isdigit():
        errs.append("title too short")
    if not _ISO_RE.match(str(fm["publishedAt"])):
        errs.append(f"publishedAt not ISO: {fm['publishedAt']!r}")
    if fm.get("updatedAt") and not _ISO_RE.match(str(fm["updatedAt"])):
        errs.append("updatedAt not ISO")
    for key in ("lastDate", "applicationBegin"):
        v = fm.get(key)
        if v and (not isinstance(v, str) or not _DDMMYYYY_RE.match(v) or not parse_ddmmyyyy(v)):
            errs.append(f"{key} not DD/MM/YYYY: {v!r}")
    for key in _TEXT_FIELDS:
        v = fm.get(key)
        if isinstance(v, str) and _BRAND_RE.search(v):
            errs.append(f"{key} mentions an aggregator brand")
    if _BRAND_RE.search(body):
        errs.append("body mentions an aggregator brand")
    q = fm.get("qualification")
    if isinstance(q, str) and re.search(r"(?i)click here|check notification", q):
        errs.append("qualification is junk")
    if not (40 <= len(fm["shortDescription"]) <= 200):
        errs.append(f"shortDescription length {len(fm['shortDescription'])}")
    if len(body.strip()) < 80:
        errs.append("body too thin")
    for key in _URL_FIELDS:
        v = fm.get(key)
        if v:
            problem = _url_ok(v)
            if problem:
                errs.append(f"{key}: {problem}")
    links = fm.get("importantLinks") or []
    if not isinstance(links, list):
        errs.append("importantLinks not a list")
    else:
        for lk in links:
            if not isinstance(lk, dict) or not lk.get("label") or lk.get("link_type") not in LINK_TYPES:
                errs.append("importantLinks entry malformed")
                break
            problem = _url_ok(lk.get("url"))
            if problem:
                errs.append(f"importantLinks '{lk.get('label')}': {problem}")
                break
    for key in ("dates", "fees"):
        d = fm.get(key)
        if d is not None and not isinstance(d, dict):
            errs.append(f"{key} not a mapping")
        elif isinstance(d, dict) and any(len(str(k)) > 60 for k in d):
            errs.append(f"{key} has an over-long key")
    for key in ("ageMin", "ageMax"):
        v = fm.get(key)
        if v is not None and (not isinstance(v, int) or not 10 <= v <= 70):
            errs.append(f"{key} out of range")
    return errs


def validate_file(path: Path) -> list[str]:
    try:
        fm, body = parse_mdx(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"unparsable: {exc}"]
    return validate_frontmatter(fm, body, path)


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv] if argv else sorted(CONTENT_ROOT.rglob("*.mdx"))
    bad = 0
    for f in files:
        errs = validate_file(f)
        if errs:
            bad += 1
            print(f"INVALID {f}: {'; '.join(errs)}")
    print(f"validated {len(files)} files, {bad} invalid")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

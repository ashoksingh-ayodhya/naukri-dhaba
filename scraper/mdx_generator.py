"""Turn scraped data into validated frontmatter and write MDX files.

`normalize_frontmatter()` is the single place where scraped values are cleaned,
so the live scraper and the one-off repair of old files produce identical output.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from classify import classify_title, is_junk_title
from content_writer import write_body, write_description
from portals import ORG_NAMES, full_org_name, official_portal_for
from taxonomy import CATEGORY_SLUGS, infer_category, infer_dept
from textutil import (clean, digits_only, find_dates, first_date, last_date, normalize_fee,
                      slugify, strip_brand, to_ddmmyyyy, to_iso)
from urls import clean_link_url

if TYPE_CHECKING:
    from detail_parser.models import DetailData

CONTENT_ROOT = Path(__file__).parent.parent / "content"
MIN_POST_DATE = "2022-01-01"
ORG_NAMES_KEYS = set(ORG_NAMES)

TYPE_DIR_MAP = {
    "job": "jobs",
    "result": "results",
    "admit": "admit-cards",
    "answer-key": "answer-keys",
    "syllabus": "syllabus",
}
DIR_TYPE_MAP = {v: k for k, v in TYPE_DIR_MAP.items()}
FLAT_TYPES = ("answer-key", "syllabus")

FIELD_ORDER = [
    "title", "slug", "type", "category", "dept", "organization", "advertisementNo", "totalPosts",
    "lastDate", "applicationBegin", "examDate", "admitDate", "resultDate",
    "ageMin", "ageMax", "ageReferenceDate", "ageRelaxationNotes",
    "qualification", "qualificationItems", "feeGeneral", "feeSCST", "feePaymentMethod", "salary",
    "applyUrl", "notificationUrl", "resultUrl", "admitUrl", "officialWebsite",
    "publishedAt", "updatedAt", "source", "sourceUrl", "shortDescription",
    "dates", "fees", "vacancyBreakdown", "importantLinks", "howToApply",
]

LINK_TYPES = {"apply", "result", "admit", "notification", "answer_key", "syllabus",
              "exam_city", "eligibility", "official_website", "other"}

_JUNK_TEXT_RE = re.compile(
    r"(?i)click\s*here|check\s*here|check\s*now|\bapp\b|whatsapp|telegram|instagram|youtube|facebook|"
    r"channel|subscribe|follow\s+us|join\s+(?:our|us)|video|typing\s*test|image\s*resizer|jpg\s*to\s*pdf|"
    r"resume\s*maker|download\s+(?:our|the)\s+app|प्रवेश\s*पत्र|वीडियो|sarkari|rojgar|freejob"
)
_FEE_LIKE_RE = re.compile(r"(?i)\brs\.?\s*\d|₹|\d\s*/-|\bfee\b|pay\s+the\s+exam")
_DATE_LIKE_RE = re.compile(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}")
_FEE_LABEL_RE = re.compile(
    r"(?i)general|obc|ews|\bsc\b|\bst\b|\bph\b|pwd|pwbd|dviyang|divyang|female|women|unreserved|"
    r"reserved|all\s*categor|\bur\b|\bbc\b|\bmbc\b|other|male|ex-?service|category|candidates"
)
_NOT_FEE_LABEL_RE = re.compile(
    r"(?i)officer|grade|\bpost\b|medical|engineer|assistant|clerk|constable|teacher|nurse|trainee|manager|"
    r"technician|inspector|operator|apprentice|professor|lecturer|driver|guard|stenographer|typist|\bjunior\b|\bsenior\b"
)
# Steps written by an earlier auto-rewriter; they were never scraped from a notification.
_TEMPLATE_STEP_RE = re.compile(
    r"(?i)^(go to the official website of|find the '|click on 'new registration'|log in with your credentials|"
    r"upload a recent passport-size|pay the application fee online via debit|preview your completed application|"
    r"submit the form and download the confirmation)"
)
_LAST_DECOY_RE = re.compile(
    r"(?i)fee|payment|correction|edit|noc|update|document|upload|objection|challan|print|verification|"
    r"choice|option|counsel|admission|scholar|exam|interview|dv\b|admit|result|answer|form\s*status|"
    r"hard\s*copy|offline|post\b"
)
_EXTENDED_RE = re.compile(r"(?i)extend|re-?open|revised|new\s*last")


def is_within_date_range(post_date: str) -> bool:
    iso = to_iso(post_date)
    return True if not iso else iso >= MIN_POST_DATE


# ── field cleaners ────────────────────────────────────────────────────────────

def normalize_title(raw: str) -> str:
    t = strip_brand(raw)
    t = re.sub(r"\s*[|–-]\s*(?:naukri\s*dhaba.*)?$", "", t, flags=re.I)
    t = re.sub(r"\b(\d{4})\s+\1\b", r"\1", t)
    t = re.sub(r"\s*\|\s*$", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" -|:,")
    return t


def clean_org(raw: str, title: str, dept: str) -> str:
    org = strip_brand(raw)
    org = re.sub(r"(?i)\s*\b(recruitment|notification|vacancy|online form|advt\.?)\s*$", "", org).strip(" -:|,.")
    bad = (
        not org or len(org) > 90 or len(org.split()) > 12 or ":" in org
        or re.search(r"(?i)\d{2}/\d{2}/\d{4}|age relaxation|last date|apply|click here|short information|"
                     r"\bwww\.|http|\bpost\s*date|important|candidates|eligib", org)
    )
    if bad:
        return full_org_name(title, dept)
    return org


def clean_adv(raw: str) -> str:
    a = clean(raw).split("|")[0]
    a = re.sub(r"(?i)^(advt\.?|advertisement|notification)\s*(no\.?|number)?\s*[:\-]?\s*", "", a)
    a = a.strip(" :|-,.;")
    if not a or len(a) > 40 or not re.search(r"\d", a):
        return ""
    return a


def clean_total_posts(raw: object) -> str:
    n = digits_only(raw)
    if not n:
        return ""
    v = int(n)
    return str(v) if 0 < v <= 500000 else ""


def _display_date(val: str, max_len: int = 40) -> str:
    v = clean(val)
    if not v or len(v) > max_len:
        return ""
    if find_dates(v) or re.search(r"(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b\s*\d{4}", v):
        return v
    return ""


def sane_dates(raw: object) -> dict[str, str]:
    out: dict[str, str] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        key, val = strip_brand(k), clean(v)
        if not key or not val or len(key) > 60 or len(val) > 60 or _JUNK_TEXT_RE.search(key):
            continue
        if not (find_dates(val) or re.search(r"(?i)soon|schedule|declared|released|available|notify|announced|"
                                             r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", val)):
            continue
        out[key] = val
        if len(out) >= 25:
            break
    return out


def _pick_last_date(dates: dict[str, str]) -> date | None:
    cands: list[tuple[int, date]] = []
    for k, v in dates.items():
        kl = k.lower()
        if not re.search(r"last\s*date|closing\s*date|last\s*day|end\s*date|apply\s*(?:online\s*)?(?:till|upto|up\s*to)", kl):
            continue
        if _LAST_DECOY_RE.search(kl) and not re.search(r"(?i)apply|registration|application|online form|last date\s*$", kl):
            continue
        if re.search(r"(?i)fee|payment|correction|edit|noc|document|upload|objection|print|hard\s*copy|offline", kl):
            continue
        d = last_date(v)
        if d:
            cands.append((1 if _EXTENDED_RE.search(kl) else 0, d))
    if not cands:
        return None
    cands.sort(key=lambda t: (t[0], t[1]))
    return cands[-1][1]


def _pick_begin_date(dates: dict[str, str]) -> date | None:
    for k, v in dates.items():
        kl = k.lower()
        if re.search(r"(?i)begin|start|open|from", kl) and re.search(r"(?i)appl|regist|online|form|notification", kl) \
                and not re.search(r"(?i)exam|correction|fee|admit|result|objection|counsel", kl):
            d = first_date(v)
            if d:
                return d
    return None


def _pick_display(dates: dict[str, str], include: str, exclude: str) -> str:
    for k, v in dates.items():
        if re.search(include, k, re.I) and not re.search(exclude, k, re.I):
            disp = _display_date(v)
            if disp:
                return disp
    return ""


def _fee_fields(raw_fees: object, raw_general: object, raw_scst: object) -> tuple[dict[str, str], str, str]:
    def keep(v: object) -> str | None:
        # already-normalised values ('25', 'No Fee') stay valid so the repair is idempotent
        t = clean(v)
        return t if re.match(r"^(\d{1,6}|No Fee)$", t) else normalize_fee(t)

    fees: dict[str, str] = {}
    if isinstance(raw_fees, dict):
        for k, v in raw_fees.items():
            key = strip_brand(k)
            if not key or len(key) > 45 or not _FEE_LABEL_RE.search(key) or _NOT_FEE_LABEL_RE.search(key) \
                    or _JUNK_TEXT_RE.search(key):
                continue
            val = keep(v)
            if val:
                fees[key] = val
            if len(fees) >= 10:
                break
    general = keep(raw_general) or next(
        (v for k, v in fees.items() if re.search(r"(?i)general|\bur\b|unreserved|obc|ews|all", k)), "")
    scst = keep(raw_scst) or next(
        (v for k, v in fees.items() if re.search(r"(?i)\bsc\b|\bst\b|pwd|ph\b|dviyang|divyang", k)), "")
    return fees, general or "", scst or ""


def _clean_qual_items(items: object) -> list[str]:
    out: list[str] = []
    if not isinstance(items, list):
        return out
    for it in items:
        s = strip_brand(it)
        if len(s) < 8 or len(s) > 300 or _FEE_LIKE_RE.search(s) or _DATE_LIKE_RE.search(s) or _JUNK_TEXT_RE.search(s):
            continue
        if re.search(r"(?i)^(general|sc|st|ph|pay the|application begin|last date|minimum age|maximum age|age relaxation|age limit)", s):
            continue
        if s not in out:
            out.append(s)
        if len(out) >= 12:
            break
    return out


def clean_qualification(raw: object, items: list[str]) -> str:
    q = strip_brand(raw)
    q = re.sub(r"(?i)^(eligibility|qualification|education(?:al)?\s*qualification)\s*[:\-]\s*", "", q)
    bad = (
        len(q) < 6 or len(q) > 300 or re.search(r"(?i)click\s*here|check\s*notification|see\s*notification|"
                                                  r"as\s*per\s*notification|read\s*notification|\bwww\.|http", q)
        or _FEE_LIKE_RE.search(q) or (_DATE_LIKE_RE.search(q) and not re.search(r"(?i)degree|pass|diploma|graduat|iti|class", q))
    )
    if bad:
        q = ""
    if not q and items:
        q = "; ".join(items)[:300]
    return q


def _clean_links(raw_links: object, base: str | None) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    if not isinstance(raw_links, list):
        return out
    for lk in raw_links:
        if not isinstance(lk, dict):
            continue
        label = strip_brand(lk.get("label"))
        url = clean_link_url(lk.get("url"), base)
        if not url or url in seen:
            continue
        if not label or len(label) > 80 or _JUNK_TEXT_RE.search(label):
            label = ""
        lt = lk.get("link_type") if lk.get("link_type") in LINK_TYPES else "other"
        if not label:
            label = {"apply": "Apply Online", "notification": "Official Notification", "result": "Result",
                     "admit": "Admit Card", "answer_key": "Answer Key", "syllabus": "Syllabus",
                     "exam_city": "Exam City", "eligibility": "Eligibility", "official_website": "Official Website"}.get(lt, "")
        if not label:
            continue
        seen.add(url)
        out.append({"label": label, "url": url, "link_type": lt})
        if len(out) >= 40:
            break
    return out


def _clean_steps(raw: object) -> list[str]:
    out: list[str] = []
    if not isinstance(raw, list):
        return out
    for s in raw:
        t = strip_brand(s)
        if len(t) < 12 or len(t) > 300 or _JUNK_TEXT_RE.search(t) or _TEMPLATE_STEP_RE.search(t):
            continue
        if re.search(r"(?i)^(general|sc\s*/\s*st|ph|pay the|application begin|last date|exam date)", t):
            continue
        t = t[0].upper() + t[1:]
        if t not in out:
            out.append(t)
        if len(out) >= 12:
            break
    return out if len(out) >= 2 else []


def _clean_vacancy(raw: object) -> list[dict]:
    out: list[dict] = []
    if not isinstance(raw, list):
        return out
    keys = ("post_name", "general", "ews", "obc", "sc", "st", "total", "eligibility")
    for row in raw:
        if not isinstance(row, dict):
            continue
        name = strip_brand(row.get("post_name"))
        if not name or len(name) > 120 or _JUNK_TEXT_RE.search(name):
            continue
        entry = {"post_name": name}
        for k in keys[1:]:
            v = strip_brand(row.get(k))
            if v and len(v) <= (200 if k == "eligibility" else 40):
                entry[k] = v
        if len(entry) > 1:
            out.append(entry)
        if len(out) >= 60:
            break
    return out


def _iso_or_none(val: object) -> str | None:
    iso = to_iso(val)
    if not iso:
        return None
    if iso < "2010-01-01" or iso > (datetime.now().date() + timedelta(days=1)).isoformat():
        return None
    return iso


def _age(val: object) -> int | None:
    n = digits_only(val)
    if not n:
        return None
    v = int(n[:2])
    return v if 10 <= v <= 70 else None


_SMALL_WORDS = {"for", "and", "of", "in", "to", "the", "on", "at", "by", "with", "a", "an"}
_ACRONYMS = {
    "ssc", "cgl", "chsl", "mts", "gd", "je", "cpo", "rrb", "rrc", "ntpc", "alp", "upsc", "cds", "nda", "ias", "ibps", "po",
    "sbi", "rbi", "lic", "aai", "isro", "drdo", "hal", "bel", "ongc", "iocl", "bhel", "sail", "gail", "nvs", "kvs", "emrs",
    "nta", "neet", "jee", "cuet", "ugc", "net", "csir", "gate", "ctet", "tet", "uptet", "reet", "bpsc", "uppsc", "upsssc",
    "mppsc", "rpsc", "rsmssb", "hssc", "hpsc", "jssc", "jpsc", "bssc", "dsssb", "tnpsc", "kpsc", "mpsc", "gpsc", "opsc",
    "ossc", "cgpsc", "ukpsc", "wbpsc", "apsc", "pet", "dv", "pst", "cbt", "tgt", "pgt", "prt", "lt", "gic", "apo", "gdc",
    "ro", "aro", "si", "asi", "hc", "itbp", "bsf", "crpf", "cisf", "ssb", "cen", "cms", "ies", "iss", "ifs", "ips", "iti",
    "phd", "mbbs", "bsc", "msc", "ba", "ma", "llb", "anm", "gnm", "cho", "nhm", "esic", "aiims", "pgimer", "bhu", "du",
    "ignou", "mp", "up", "hp", "cg", "wb", "tn", "ap", "ts", "uk", "ncl", "cil", "secl", "ecl", "mcl", "bccl", "ccl", "wcl",
    "nlc", "nhpc", "sjvn", "thdc", "pgcil", "npcil", "barc", "bsnl", "dmrc", "nhai", "irctc", "rites", "rvnl", "pcs", "acf",
    "rfo", "vdo", "ldc", "udc", "sc", "st", "obc", "ews", "ph", "pwd", "ii", "iii", "iv", "ug", "pg", "ipo", "ppsc", "hppsc",
    "mpesb", "csbc", "bpssc", "btsc", "uksssc", "iaf", "afcat", "ncc", "kvs", "cbse", "bseb", "hbse", "rbse", "jac", "mpbse",
    "upmsp", "cisce", "icse", "dcece", "nift", "ecce", "upsrtc", "upsrlm", "mphc", "hprca", "appsc", "bob", "cbo", "jlo",
}


def title_from_slug(slug: str) -> str:
    words = []
    for w in slug.split("-"):
        if not w:
            continue
        if w in _ACRONYMS or w.upper() in ORG_NAMES_KEYS:
            words.append(w.upper())
        elif w in _SMALL_WORDS and words:
            words.append(w)
        else:
            words.append(w[:1].upper() + w[1:])
    return " ".join(words)


def _title_disagrees_with_slug(title: str, slug: str) -> bool:
    """True when the stored title clearly describes something else than the URL slug."""
    slug_tokens = {t for t in slug.split("-") if t and not t.isdigit()}
    if len(slug_tokens) < 3:
        return False
    title_tokens = {t for t in slugify(title).split("-") if t and not t.isdigit()}
    if not title_tokens:
        return True
    overlap = len(slug_tokens & title_tokens) / len(slug_tokens)
    return overlap < 0.34


# ── main normaliser ───────────────────────────────────────────────────────────

def normalize_frontmatter(raw: dict, *, base_url: str | None = None, keep_category: str | None = None,
                          keep_slug: str | None = None, scraped_at: str | None = None) -> dict | None:
    """Clean a raw frontmatter dict. Returns None when the page is junk and must not be published."""
    title = normalize_title(raw.get("title") or "")
    if keep_slug and _title_disagrees_with_slug(title, keep_slug):
        title = title_from_slug(keep_slug)
    if is_junk_title(title):
        return None
    kind = classify_title(title, hint=raw.get("type") if raw.get("type") in TYPE_DIR_MAP else None)
    if not kind:
        return None

    slug = keep_slug or clean(raw.get("slug"))
    if not slug or slug.isdigit() or not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):
        slug = slugify(title)
    if not slugify(slug.replace("-", " ")):  # nothing ASCII survived (e.g. Devanagari-only title)
        return None
    if len(slug) < 5:
        return None

    category = keep_category if keep_category in CATEGORY_SLUGS else infer_category(title, raw.get("dept") or "", raw.get("organization") or "")
    dept = infer_dept(title, category, strip_brand(raw.get("dept")))
    org = clean_org(raw.get("organization") or "", title, dept)
    source_url = clean(raw.get("sourceUrl"))
    base = base_url or source_url or None

    dates = sane_dates(raw.get("dates"))
    last_d = _pick_last_date(dates) or first_date(raw.get("lastDate"))
    begin_d = _pick_begin_date(dates) or first_date(raw.get("applicationBegin"))
    if begin_d and last_d and begin_d > last_d:
        begin_d = None
    exam = _pick_display(dates, r"exam\s*date|examination\s*date|written\s*exam|cbt|tier|phase|exam\s*held|exam\s*schedule",
                         r"city|fee|form|apply|notice|result|admit|answer|intimation|slip") or _display_date(raw.get("examDate") or "")
    admit = _pick_display(dates, r"admit\s*card|hall\s*ticket|call\s*letter", r"notice|city") or _display_date(raw.get("admitDate") or "")
    result = _pick_display(dates, r"result", r"eligib|fee|form") or _display_date(raw.get("resultDate") or "")

    items = _clean_qual_items(raw.get("qualificationItems"))
    qualification = clean_qualification(raw.get("qualification"), items)
    fees, fee_general, fee_scst = _fee_fields(raw.get("fees"), raw.get("feeGeneral"), raw.get("feeSCST"))
    pay = strip_brand(raw.get("feePaymentMethod"))
    if len(pay) > 200 or _JUNK_TEXT_RE.search(pay) or not re.search(r"(?i)online|offline|challan|debit|credit|net\s*banking|upi|cash|bank|mode|through|via|e-?challan|counter", pay):
        pay = ""
    salary = strip_brand(raw.get("salary"))
    if len(salary) > 120 or not re.search(r"\d", salary) or re.search(r"(?i)as per (govt|government)|norms|click|notification", salary):
        salary = ""

    links = _clean_links(raw.get("importantLinks"), base)
    def first_link(lt: str) -> str:
        return next((l["url"] for l in links if l["link_type"] == lt), "")
    apply_url = clean_link_url(raw.get("applyUrl"), base) or first_link("apply")
    notif_url = clean_link_url(raw.get("notificationUrl"), base) or first_link("notification")
    result_url = clean_link_url(raw.get("resultUrl"), base) or first_link("result")
    admit_url = clean_link_url(raw.get("admitUrl"), base) or first_link("admit")
    official = clean_link_url(raw.get("officialWebsite"), base) or first_link("official_website") \
        or official_portal_for(title, dept, category)
    if official and not any(l["link_type"] == "official_website" for l in links):
        links.append({"label": "Official Website", "url": official, "link_type": "official_website"})

    # A post we cannot date is not publishable: the scraper always passes scraped_at,
    # so this only rejects legacy files that never had a date.
    published = _iso_or_none(raw.get("publishedAt")) or _iso_or_none(scraped_at)
    if not published:
        return None
    updated = _iso_or_none(raw.get("updatedAt"))
    if updated and updated < published:
        updated = None

    age_min, age_max = _age(raw.get("ageMin")), _age(raw.get("ageMax"))
    if age_min and age_max and age_min >= age_max:
        age_min = None
    age_ref = to_ddmmyyyy(first_date(raw.get("ageReferenceDate"))) or ""
    relax = strip_brand(raw.get("ageRelaxationNotes"))
    if len(relax) > 250 or _JUNK_TEXT_RE.search(relax):
        relax = ""

    fm: dict = {
        "title": title,
        "slug": slug,
        "type": kind,
        "category": category,
        "dept": dept,
        "organization": org,
    }
    adv = clean_adv(raw.get("advertisementNo") or "")
    if adv:
        fm["advertisementNo"] = adv
    tp = clean_total_posts(raw.get("totalPosts"))
    if tp:
        fm["totalPosts"] = tp
    if last_d:
        fm["lastDate"] = to_ddmmyyyy(last_d)
    if begin_d:
        fm["applicationBegin"] = to_ddmmyyyy(begin_d)
    if exam:
        fm["examDate"] = exam
    if admit:
        fm["admitDate"] = admit
    if result:
        fm["resultDate"] = result
    if age_min:
        fm["ageMin"] = age_min
    if age_max:
        fm["ageMax"] = age_max
    if age_ref:
        fm["ageReferenceDate"] = age_ref
    if relax:
        fm["ageRelaxationNotes"] = relax
    if qualification:
        fm["qualification"] = qualification
    if items:
        fm["qualificationItems"] = items
    if fee_general:
        fm["feeGeneral"] = fee_general
    if fee_scst:
        fm["feeSCST"] = fee_scst
    if pay:
        fm["feePaymentMethod"] = pay
    if salary:
        fm["salary"] = salary
    if apply_url:
        fm["applyUrl"] = apply_url
    if notif_url:
        fm["notificationUrl"] = notif_url
    if result_url:
        fm["resultUrl"] = result_url
    if admit_url:
        fm["admitUrl"] = admit_url
    if official:
        fm["officialWebsite"] = official
    fm["publishedAt"] = published
    if updated:
        fm["updatedAt"] = updated
    src = clean(raw.get("source"))
    if src and re.match(r"^[a-z]+$", src):
        fm["source"] = src
    if source_url.startswith("http") and " " not in source_url:
        fm["sourceUrl"] = source_url
    fm["shortDescription"] = write_description(fm)
    if dates:
        fm["dates"] = dates
    if fees:
        fm["fees"] = fees
    vac = _clean_vacancy(raw.get("vacancyBreakdown"))
    if vac:
        fm["vacancyBreakdown"] = vac
    if links:
        fm["importantLinks"] = links
    steps = _clean_steps(raw.get("howToApply"))
    if steps:
        fm["howToApply"] = steps
    return {k: fm[k] for k in FIELD_ORDER if k in fm}


def detail_to_raw(detail: "DetailData", kind_hint: str = "") -> dict:
    d = detail
    return {
        "title": d.title or d.post_name,
        "slug": d.slug,
        "type": d.page_type or kind_hint,
        "dept": d.dept,
        "organization": d.organization_full_name,
        "advertisementNo": d.advertisement_number,
        "totalPosts": d.total_posts,
        "ageMin": d.age_min,
        "ageMax": d.age_max,
        "ageReferenceDate": d.age_reference_date,
        "ageRelaxationNotes": d.age_relaxation_notes,
        "qualification": d.qualification,
        "qualificationItems": d.qualification_items,
        "feePaymentMethod": d.fee_payment_method,
        "salary": d.salary,
        "applyUrl": d.apply_url,
        "notificationUrl": d.notification_url,
        "resultUrl": d.result_url,
        "admitUrl": d.admit_url,
        "officialWebsite": d.official_website_url,
        "publishedAt": d.post_date,
        "updatedAt": d.update_date,
        "source": d.source,
        "sourceUrl": d.source_detail_url,
        "dates": d.dates,
        "fees": d.fees,
        "vacancyBreakdown": d.vacancy_breakdown,
        "importantLinks": d.important_links,
        "howToApply": d.how_to_apply,
    }


# ── serialisation ─────────────────────────────────────────────────────────────

def render_mdx(fm: dict, body: str | None = None) -> str:
    ordered = {k: fm[k] for k in FIELD_ORDER if k in fm}
    yml = yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, width=100000, default_flow_style=False)
    return f"---\n{yml}---\n\n{(body if body is not None else write_body(fm)).strip()}\n"


def mdx_path_for(fm: dict, content_root: Path | None = None) -> Path:
    root = content_root or CONTENT_ROOT
    type_dir = TYPE_DIR_MAP[fm["type"]]
    if fm["type"] in FLAT_TYPES:
        return root / type_dir / f"{fm['slug']}.mdx"
    return root / type_dir / fm["category"] / f"{fm['slug']}.mdx"


def parse_mdx(text: str) -> tuple[dict, str]:
    """Split an MDX file into (frontmatter dict, body). Raises ValueError if unparsable."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if not m:
        raise ValueError("no frontmatter block")
    data = yaml.safe_load(m.group(1))
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a mapping")
    return data, m.group(2)


def generate_mdx(detail: "DetailData", content_root: Path | None = None, kind_hint: str = "") -> Path | None:
    """Write a .mdx for the scraped page. Returns the path, or None if the page was rejected."""
    raw = detail_to_raw(detail, kind_hint)
    fm = normalize_frontmatter(raw, base_url=detail.source_detail_url or None, scraped_at=detail.scraped_at)
    if fm is None:
        return None
    if not is_within_date_range(fm["publishedAt"]):
        return None
    path = mdx_path_for(fm, content_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_mdx(fm), encoding="utf-8")
    return path

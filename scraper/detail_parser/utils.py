"""
Shared utilities for detail page parsing.

Label normalization, regex patterns, and link-type classification.
"""

import re

# ── Link type classification ──────────────────────────────────
# Maps label patterns → link_type for the important_links list.
LINK_TYPE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'final\s*result|result\s*download|download\s*result', re.I), "result"),
    (re.compile(r'revised\s*answer\s*key', re.I), "answer_key"),
    (re.compile(r'answer\s*key', re.I), "answer_key"),
    (re.compile(r'admit\s*card|hall\s*ticket|call\s*letter', re.I), "admit"),
    (re.compile(r'exam\s*city', re.I), "exam_city"),
    (re.compile(r'eligibility\s*result|check\s*eligibility', re.I), "eligibility"),
    (re.compile(r'how\s*to\s*check', re.I), "guide"),
    (re.compile(r'syllabus', re.I), "syllabus"),
    (re.compile(r'apply\s*online|register|registration', re.I), "apply"),
    (re.compile(r'notification|advt|advertise', re.I), "notification"),
    (re.compile(r'score\s*card|scorecard|mark\s*sheet', re.I), "scorecard"),
    (re.compile(r'official\s*website', re.I), "official_website"),
    (re.compile(r'result|merit\s*list|cut.?off', re.I), "result"),
]


def classify_link(label: str) -> str:
    """Return a link_type string for the given label."""
    for pattern, link_type in LINK_TYPE_PATTERNS:
        if pattern.search(label):
            return link_type
    return "other"


# ── Date detection ────────────────────────────────────────────
_MONTH_NAMES = (
    r'jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
    r'jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?'
)
DATE_VALUE_RE = re.compile(
    r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|'
    r'\d{1,2}\s*(?:' + _MONTH_NAMES + r')\s*\d{2,4}|'
    r'today|tomorrow|declared|released|available|schedule|soon)',
    re.I,
)

# Requires an actual currency/fee marker — a bare digit is too permissive and
# matches dates, DOB ranges, and age values, causing those rows to be
# misclassified as fees instead of dates/qualification.
FEE_VALUE_RE = re.compile(
    r'(free|nil|no\s*(?:application\s*)?fee|rs\.?\s*\d|inr\s*\d|₹\s*\d|\d\s*/-)',
    re.I,
)


def looks_like_date_value(text: str) -> bool:
    return bool(DATE_VALUE_RE.search(text))


def looks_like_fee_value(text: str) -> bool:
    return bool(FEE_VALUE_RE.search(text))


# ── Organization name validation ───────────────────────────────
# Recruiting body is unambiguous from the title for the armed forces — check
# this before any generic bold-text/table scan, which can otherwise latch
# onto unrelated "Commission"/"Board" mentions (e.g. "Short Service
# Commission") describing the tenure of service rather than naming the
# organization.
KNOWN_ORG_FROM_TITLE: list[tuple[re.Pattern, str]] = [
    (re.compile(r'indian\s+navy', re.I), 'Indian Navy'),
    (re.compile(r'indian\s+army', re.I), 'Indian Army'),
    (re.compile(r'indian\s+air\s*force', re.I), 'Indian Air Force'),
    (re.compile(r'indian\s+coast\s+guard', re.I), 'Indian Coast Guard'),
]

# Phrases that mean the matched text is describing a tenure/duration of
# service rather than naming the recruiting organization itself.
NOT_AN_ORG_NAME_RE = re.compile(
    r'\binitially\b|\btenure\b|\d+\s*years?\b|\bcourse\b|\bmonths?\b',
    re.I,
)


def known_org_from_title(title: str) -> str:
    """Return a canonical org name if the title unambiguously names one."""
    for pattern, org_name in KNOWN_ORG_FROM_TITLE:
        if pattern.search(title):
            return org_name
    return ""


# ── Section header detection ──────────────────────────────────

def is_dates_header(text: str) -> bool:
    return bool(re.search(r'important\s*dates?', text, re.I))


def is_fees_header(text: str) -> bool:
    return bool(re.search(r'application\s*fee|exam\s*fee', text, re.I))


def is_age_header(text: str) -> bool:
    return bool(re.search(r'age\s*limit', text, re.I))


def is_vacancy_header(text: str) -> bool:
    return bool(re.search(r'vacancy\s*detail|total\s*:?\s*\d+\s*post', text, re.I))


def is_category_vacancy_header(text: str) -> bool:
    return bool(re.search(r'category\s*wise|caste\s*wise', text, re.I))


def is_qualification_header(text: str) -> bool:
    return bool(re.search(r'qualification|eligibility|education', text, re.I))


def is_how_to_apply_header(text: str) -> bool:
    return bool(re.search(r'how\s*to\s*(fill|apply)', text, re.I))


def is_links_header(text: str) -> bool:
    return bool(re.search(r'(some\s*)?useful\s*important\s*links?|important\s*links?', text, re.I))


# ── Age parsing ───────────────────────────────────────────────

def extract_age_reference_date(text: str) -> str:
    """Extract 'as on DD/MM/YYYY' from text."""
    m = re.search(r'as\s*on\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text, re.I)
    return m.group(1) if m else ""


# ── Text cleaning ─────────────────────────────────────────────

def clean(text: str) -> str:
    """Strip whitespace and collapse spaces."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', str(text)).strip()


def is_junk_row(text: str) -> bool:
    """Return True if the row is source-site spam (app promos, social links, etc.)."""
    return bool(re.search(
        r'sarkari\s*result\s*(channel|app|mobile)|'
        r'download\s*sarkariresult|'
        r'android\s*app|apple\s*ios|'
        r'resume\s*cv\s*maker|'
        r'typing\s*test|'
        r'image\s*resizer|'
        r'join\s*sarkari|'
        r'sarkari\s*tools|'
        r'jpg\s*to\s*pdf|'
        r'whatsapp.*telegram|telegram.*whatsapp',
        text, re.I
    ))

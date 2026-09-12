"""Text, date and number normalisation shared by the scraper, repair and validator."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

# Aggregator brand names that must never appear in user-facing text.
_BRAND_RE = re.compile(
    r"(?i)\b(?:www\.)?(?:sarkari\s*results?|free\s*job\s*alerts?|rojgar\s*results?|sarkari\s*exam)"
    r"(?:\.(?:com|org|in|org\.in))?\b\.?"
)
# Leftovers from an earlier regex pass that swapped the brand for our name inside prose.
_SELF_BRAND_JUNK_RE = re.compile(
    r"(?i)(?:download|join|follow|like)\s+(?:the\s+)?naukri\s*dhaba\s+\S+.*$|"
    r"(?:you\s+can\s+)?check\s+other\s+naukri\s*dhaba.*$"
)

_DMY_RE = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})")
_YMD_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_TEXT_DMY_RE = re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})")
_TEXT_MDY_RE = re.compile(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})")


def clean(text: object) -> str:
    """Collapse whitespace and strip. Never returns None."""
    if text is None:
        return ""
    s = str(text).replace("\xa0", " ").replace("​", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def strip_brand(text: object) -> str:
    """Remove aggregator brand mentions from prose, tidying punctuation afterwards."""
    s = clean(text)
    if not s:
        return ""
    s = _SELF_BRAND_JUNK_RE.sub("", s)
    s = _BRAND_RE.sub("", s)
    s = re.sub(r"\s+([,.;:)])", r"\1", s)
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" -|:,")
    return s


def _valid(y: int, m: int, d: int) -> date | None:
    try:
        if 1990 <= y <= 2100:
            return date(y, m, d)
    except ValueError:
        pass
    return None


def find_dates(text: object) -> list[date]:
    """All recognisable calendar dates in *text*, in order of appearance."""
    s = clean(text)
    found: list[tuple[int, date]] = []
    for m in _YMD_RE.finditer(s):
        d = _valid(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            found.append((m.start(), d))
    for m in _DMY_RE.finditer(s):
        d = _valid(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        if d:
            found.append((m.start(), d))
    for m in _TEXT_DMY_RE.finditer(s):
        mon = MONTHS.get(m.group(2).lower())
        if mon:
            d = _valid(int(m.group(3)), mon, int(m.group(1)))
            if d:
                found.append((m.start(), d))
    for m in _TEXT_MDY_RE.finditer(s):
        mon = MONTHS.get(m.group(1).lower())
        if mon:
            d = _valid(int(m.group(3)), mon, int(m.group(2)))
            if d:
                found.append((m.start(), d))
    found.sort(key=lambda t: t[0])
    out: list[date] = []
    for _, d in found:
        if not out or out[-1] != d:
            out.append(d)
    return out


def first_date(text: object) -> date | None:
    ds = find_dates(text)
    return ds[0] if ds else None


def last_date(text: object) -> date | None:
    ds = find_dates(text)
    return ds[-1] if ds else None


def to_iso(text: object) -> str | None:
    d = first_date(text)
    return d.isoformat() if d else None


def to_ddmmyyyy(d: date | None) -> str | None:
    return d.strftime("%d/%m/%Y") if d else None


def parse_ddmmyyyy(text: object) -> date | None:
    """Parse a frontmatter display date (DD/MM/YYYY, DD-MM-YYYY or textual)."""
    return first_date(text)


def today_iso() -> str:
    return datetime.now().date().isoformat()


def slugify(text: object, max_len: int = 100) -> str:
    t = unicodedata.normalize("NFKD", clean(text)).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9\s-]", "", t)
    t = re.sub(r"[\s_]+", "-", t)
    t = re.sub(r"-{2,}", "-", t).strip("-")
    if len(t) > max_len:
        t = t[:max_len].rsplit("-", 1)[0]
    return t


def digits_only(text: object) -> str:
    return re.sub(r"[^0-9]", "", clean(text))


def normalize_fee(text: object, strict: bool = True) -> str | None:
    """'Rs. 500/-' → '500'; 'Nil' / 'No Fee' / '0/-' → 'No Fee'; unparseable → None.

    With strict=True a bare number is rejected: fee cells on the source sites always
    carry a currency marker, while bare numbers are vacancy counts or roll numbers.
    """
    s = clean(text)
    if not s:
        return None
    if re.search(r"(?i)\b(free|nil|no\s*fee|exempt|exempted|0\s*/-|^0$)", s):
        return "No Fee"
    if strict and not re.search(r"(?i)rs\.?|₹|inr|/-|\bfee\b|rupee", s):
        return None
    m = re.search(r"(\d[\d,]*)(?:\.\d+)?\s*/?-?", s)
    if not m:
        return None
    n = m.group(1).replace(",", "")
    if not n.isdigit() or int(n) == 0:
        return "No Fee" if n.isdigit() else None
    if int(n) > 100000:
        return None
    return n


def sentence_case_join(parts: list[str]) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip())


def truncate_sentences(text: str, limit: int) -> str:
    """Return the longest prefix of whole sentences that fits in *limit* chars."""
    text = clean(text)
    if len(text) <= limit:
        return text
    out = ""
    for sent in re.split(r"(?<=[.!?])\s+", text):
        candidate = f"{out} {sent}".strip()
        if len(candidate) > limit:
            break
        out = candidate
    if out:
        return out
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:") + "…"

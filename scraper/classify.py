"""Decide which content type a post title belongs to."""

from __future__ import annotations

import re

KINDS = ("job", "result", "admit", "answer-key", "syllabus")

_ANSKEY = re.compile(r"answer\s*keys?|answer\s*sheet|\bans\s*key", re.I)
_SYLLABUS = re.compile(r"syllabus|exam\s*pattern", re.I)
_ADMIT = re.compile(
    r"admit\s*cards?|hall\s*tickets?|call\s*letters?|exam\s*city|exam\s*dates?|exam\s*schedule|e-?admit|"
    r"interview\s*letter|intimation\s*slip|exam\s*intimation",
    re.I,
)
_RESULT = re.compile(
    r"\bresults?\b|merit\s*list|score\s*cards?|\bmarks\b|cut\s*-?\s*off|selection\s*list|final\s*list|"
    r"\btoppers?\b|\brank\s*list|\bdv\s*list|shortlist(?:ed)?|final\s*answer|\bwaiting\s*list",
    re.I,
)
# "Online Form" / "Apply Online" name a recruitment page even when it also mentions a result update.
_STRONG_JOB = re.compile(
    r"online\s*forms?|apply\s*online|application\s*forms?|admission\s*forms?|online\s*application|"
    r"\bregistration\b|walk\s*-?\s*in|\bbharti\b|vacanc",
    re.I,
)
# "Recruitment 2025" is usually just the exam's name ("SSC CGL Recruitment 2025 Final Result"),
# so these only win when no result/admit-card word is present.
_MEDIUM_JOB = re.compile(
    r"recruitment|\bjobs?\b|\bnotification\b|\bposts?\b|\bhiring\b|\bengagement\b|\bcareers?\b|\bbatch\b|"
    r"\bintake\b|\bentry\b|\bcourse\b|\bscheme\b|\byojana\b|\bmela\b|\bfair\b",
    re.I,
)
_WEAK_JOB = re.compile(
    r"\bapply\b|admission|\bopening|correction|edit\s*form|extended|counsell?ing|\bform\b|"
    r"\bfee\s*payment|re-?open|scholarship|\bexam\b|\binterview\b",
    re.I,
)

_JUNK_TITLE = re.compile(
    r"^(latest|top online form|top|jobs?|results?|admit cards?|home|new|latest jobs?|tracking config|"
    r"latest results?|latest admit cards?|answer keys?|syllabus|contact us|about us|privacy policy)$",
    re.I,
)


def is_junk_title(title: str) -> bool:
    t = (title or "").strip()
    if len(t) < 10 or t.isdigit():
        return True
    if _JUNK_TITLE.match(t):
        return True
    if not re.search(r"[A-Za-z]{3}", t):
        return True
    return False


def classify_title(title: str, hint: str | None = None) -> str | None:
    """Return the content kind for a title, or None if it is not a post at all.

    Priority: answer-key > syllabus > strong job phrase > admit > result > weak job phrase.
    *hint* (the listing the title came from) only breaks ties when nothing matches.
    """
    t = title or ""
    if is_junk_title(t):
        return None
    if _ANSKEY.search(t):
        return "answer-key"
    if _SYLLABUS.search(t):
        return "syllabus"
    if _STRONG_JOB.search(t):
        return "job"
    if _ADMIT.search(t):
        return "admit"
    if _RESULT.search(t):
        return "result"
    if _MEDIUM_JOB.search(t) or _WEAK_JOB.search(t):
        return "job"
    if hint in KINDS:
        return hint
    return None


def title_matches_kind(title: str, kind: str) -> bool:
    return classify_title(title, hint=None) == kind

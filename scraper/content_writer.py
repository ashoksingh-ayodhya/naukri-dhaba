"""Fact-only page copy generated from frontmatter.

Every sentence is derived from a field that was actually scraped. Nothing is
invented: no current-year injection, no fee-waiver claims, no fake steps.
"""

from __future__ import annotations

import re

from textutil import clean, truncate_sentences

TYPE_LABEL = {
    "job": "recruitment",
    "result": "result",
    "admit": "admit card",
    "answer-key": "answer key",
    "syllabus": "syllabus",
}


def _org(fm: dict) -> str:
    return clean(fm.get("organization") or fm.get("dept") or "")


def _fee_phrase(fm: dict) -> str:
    g, s = clean(fm.get("feeGeneral")), clean(fm.get("feeSCST"))

    def fmt(v: str) -> str:
        return v if not v.isdigit() else f"₹{int(v):,}"

    if g and s and g != s:
        return f"Application fee: {fmt(g)} for General/OBC/EWS and {fmt(s)} for SC/ST/PwD."
    if g:
        return f"Application fee: {fmt(g)}." if not s else f"Application fee: {fmt(g)} for all categories."
    if s:
        return f"Application fee for SC/ST/PwD: {fmt(s)}."
    return ""


def _age_phrase(fm: dict) -> str:
    lo, hi, ref = fm.get("ageMin"), fm.get("ageMax"), clean(fm.get("ageReferenceDate"))
    if lo and hi:
        base = f"Age limit: {lo} to {hi} years"
    elif hi:
        base = f"Maximum age: {hi} years"
    elif lo:
        base = f"Minimum age: {lo} years"
    else:
        return ""
    return base + (f" as on {ref}." if ref else ".")


def _short_org(org: str) -> str:
    m = re.search(r"\(([A-Z][A-Za-z&. ]{1,14})\)\s*$", org)
    return m.group(1) if m else org


def lead_sentences(fm: dict, short: bool = False) -> list[str]:
    kind = fm.get("type", "job")
    title = clean(fm.get("title"))
    org = _org(fm)
    if short:
        org = _short_org(org) or clean(fm.get("dept"))
    posts = clean(fm.get("totalPosts"))
    begin, last = clean(fm.get("applicationBegin")), clean(fm.get("lastDate"))
    exam = clean(fm.get("examDate"))
    qual = clean(fm.get("qualification"))
    salary = clean(fm.get("salary"))
    out: list[str] = []

    if kind == "job":
        if org:
            s = f"{org} has released the {title} notification"
        else:
            s = f"The {title} notification has been released"
        s += f" for {posts} posts." if posts else "."
        out.append(s)
        if begin and last:
            out.append(f"Online applications are accepted from {begin} to {last}.")
        elif last:
            out.append(f"The last date to apply is {last}.")
        elif begin:
            out.append(f"Applications open from {begin}.")
        fee = _fee_phrase(fm)
        if fee:
            out.append(fee)
        if salary:
            out.append(f"Pay scale: {salary}.")
        if exam:
            out.append(f"Exam date: {exam}.")
        return out

    if org:
        out.append(f"{org} has released the {title}.")
    else:
        out.append(f"{title} has been released.")
    if kind == "result":
        if exam:
            out.append(f"The examination was held on {exam}.")
        if posts:
            out.append(f"The recruitment covers {posts} posts.")
        out.append("Candidates can check it on the official website using their roll number or registration details.")
    elif kind == "admit":
        if exam:
            out.append(f"The examination is scheduled on {exam}.")
        admit_on = clean(fm.get("admitDate"))
        if admit_on:
            out.append(f"Admit cards are available from {admit_on}.")
        out.append("Download it from the official website using your registration number and date of birth or password.")
    elif kind == "answer-key":
        if exam:
            out.append(f"The examination was held on {exam}.")
        out.append("Candidates can download the answer key from the official website and check their responses.")
    elif kind == "syllabus":
        if qual:
            out.append(f"Eligibility: {qual}.")
        out.append("The detailed subject-wise topics and exam pattern are available in the official syllabus document linked below.")
    return out


def write_description(fm: dict) -> str:
    """Meta description / intro: whole sentences, at most 160 characters."""
    full = " ".join(lead_sentences(fm))
    if len(full.split(". ")[0]) > 160:
        full = " ".join(lead_sentences(fm, short=True))
    desc = truncate_sentences(full, 160)
    if len(desc) < 40:
        title = clean(fm.get("title"))
        desc = title if len(title) <= 160 else title[:157].rstrip() + "…"
    return desc


def _faq(fm: dict) -> list[tuple[str, str]]:
    kind = fm.get("type", "job")
    title = clean(fm.get("title"))
    org = _org(fm)
    qa: list[tuple[str, str]] = []
    posts, last, begin = clean(fm.get("totalPosts")), clean(fm.get("lastDate")), clean(fm.get("applicationBegin"))
    qual, exam, salary = clean(fm.get("qualification")), clean(fm.get("examDate")), clean(fm.get("salary"))
    site = clean(fm.get("officialWebsite"))

    if kind == "job":
        if last:
            qa.append((f"What is the last date to apply for {title}?", f"The last date to apply is {last}."))
        if begin:
            qa.append((f"When does the application for {title} start?", f"Online applications start on {begin}."))
        if posts:
            qa.append((f"How many vacancies are there in {title}?", f"A total of {posts} posts have been notified."))
        if qual:
            qa.append((f"What is the qualification for {title}?", f"{qual}."))
        age = _age_phrase(fm)
        if age:
            qa.append((f"What is the age limit for {title}?", age))
        fee = _fee_phrase(fm)
        if fee:
            qa.append((f"What is the application fee for {title}?", fee))
        if salary:
            qa.append((f"What is the salary for {title}?", f"The notified pay scale is {salary}."))
        if site:
            qa.append((f"Where can I apply for {title}?",
                       f"Applications are submitted on the official website of {org or 'the recruiting body'}: {site}"))
    else:
        label = TYPE_LABEL.get(kind, "update")
        if exam:
            qa.append((f"When was the {title} exam held?" if kind != "admit" else f"When is the {title} exam?",
                       f"The examination date is {exam}."))
        if posts:
            qa.append((f"How many posts are covered by {title}?", f"The recruitment covers {posts} posts."))
        if site:
            qa.append((f"Where can I download the {label} for {title}?",
                       f"On the official website of {org or 'the conducting body'}: {site}"))
        if org:
            qa.append((f"Who conducts {title}?", f"{org}."))
    return qa[:6]


def write_body(fm: dict) -> str:
    kind = fm.get("type", "job")
    title = clean(fm.get("title"))
    org = _org(fm)
    parts: list[str] = [" ".join(lead_sentences(fm))]

    if kind == "job":
        elig: list[str] = []
        qual = clean(fm.get("qualification"))
        if qual:
            elig.append(f"**Educational qualification:** {qual}.")
        age = _age_phrase(fm)
        if age:
            elig.append(f"**Age limit:** {age[len('Age limit: '):] if age.startswith('Age limit: ') else age}")
        notes = clean(fm.get("ageRelaxationNotes"))
        if notes:
            elig.append(f"**Age relaxation:** {notes.rstrip('.')}.")
        if elig:
            parts.append(f"\n## Eligibility for {title}\n\n" + "\n\n".join(elig))

    faq = _faq(fm)
    if len(faq) >= 2:
        lines = ["\n## Frequently Asked Questions\n"]
        for q, a in faq:
            lines.append(f"### {q}\n\n{a}\n")
        parts.append("\n".join(lines))

    who = f"the official {org} notification" if org else "the official notification"
    parts.append(f"\n---\n*Details on this page are compiled from {who}. "
                 f"Always verify dates, eligibility and fees on the official website before applying.*")
    body = "\n".join(parts).strip() + "\n"
    return re.sub(r"\n{3,}", "\n\n", body)

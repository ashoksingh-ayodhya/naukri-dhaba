"""Category / department inference. Mirrors config/site.ts CATEGORIES."""

from __future__ import annotations

import re

from portals import ORG_NAMES, _find_key

CATEGORY_SLUGS = (
    "ssc", "railway", "banking", "upsc", "police", "defence", "teaching",
    "psu", "state-psc", "postal", "medical", "government",
)

CATEGORY_LABEL = {
    "ssc": "SSC", "railway": "RAILWAY", "banking": "BANK", "upsc": "UPSC", "police": "POLICE",
    "defence": "DEFENCE", "teaching": "TEACHING", "psu": "PSU", "state-psc": "STATE PSC",
    "postal": "POSTAL", "medical": "MEDICAL", "government": "GOVERNMENT",
}

_RULES: list[tuple[str, re.Pattern]] = [
    ("state-psc", re.compile(r"\b(UPPSC|MPPSC|BPSC|RPSC|JPSC|HPSC|HPPSC|PPSC|GPSC|MPSC|TNPSC|KPSC|OPSC|CGPSC|UKPSC|WBPSC|APSC|PSC)\b")),
    ("ssc", re.compile(r"\b(SSC|UPSSSC|BSSC|JSSC|HSSC|DSSSB|OSSC|UKSSSC|SSSB|STAFF SELECTION)\b")),
    ("upsc", re.compile(r"\b(UPSC|IAS|IFS|IPS|CDS|NDA|CAPF|IES|ESE|CIVIL SERVICES)\b")),
    ("railway", re.compile(r"\b(RRB|RRC|RAILWAY|RAILWAYS|METRO|DFCCIL|RITES|IRCTC|KONKAN|LOCO PILOT|NORTHERN RAILWAY|WESTERN RAILWAY)\b")),
    ("banking", re.compile(r"\b(IBPS|SBI|RBI|NABARD|BANK|LIC|NIACL|UIIC|GIC|ECGC|SIDBI|INSURANCE|SEBI|NHB|EXIM|PNB|BOB|CANARA|IDBI|NAINITAL)\b")),
    ("police", re.compile(r"\b(POLICE|CONSTABLE|CISF|BSF|CRPF|ITBP|SSB|SSF|HOME GUARD|JAIL WARDER|SUB INSPECTOR|SI|DAROGA|PRAHARI|FIREMAN|CSBC|BPSSC|PRISON)\b")),
    ("defence", re.compile(r"\b(ARMY|NAVY|AIR FORCE|AIRFORCE|IAF|AGNIVEER|DRDO|HAL|COAST GUARD|TERRITORIAL|ORDNANCE|BEL|BDL|MES|AFCAT|SAINIK|NCC|DEFENCE|DEFENSE|CANTONMENT|AOC|GREF|BRO)\b")),
    ("teaching", re.compile(r"\b(TEACHER|TEACHERS|TGT|PGT|PRT|LECTURER|PROFESSOR|TET|CTET|UPTET|REET|KVS|NVS|EMRS|B\.?ED|DELED|D\.EL\.ED|BTC|SHIKSHAK|ANGANWADI|SCHOOL|UNIVERSITY|COLLEGE|VIDYALAYA|EDUCATION|FACULTY|SUPER TET|ASSISTANT PROFESSOR)\b")),
    ("medical", re.compile(r"\b(NURSE|NURSING|ANM|GNM|MEDICAL|AIIMS|HEALTH|NHM|PHARMACIST|PARAMEDICAL|ESIC|HOSPITAL|DOCTOR|MBBS|NEET|CHO|LAB TECHNICIAN|AYUSH|DENTAL|PGIMER|JIPMER|NIMHANS|SGPGI|KGMU|RML|STAFF NURSE)\b")),
    ("postal", re.compile(r"\b(POST OFFICE|INDIA POST|GDS|POSTAL|GRAMIN DAK|DAK SEVAK|POSTMAN)\b")),
    ("psu", re.compile(r"\b(NTPC|ONGC|BHEL|SAIL|GAIL|IOCL|BPCL|HPCL|COAL INDIA|NCL|ECL|SECL|WCL|MCL|BCCL|CCL|NLC|NHPC|POWERGRID|PGCIL|ISRO|BARC|NPCIL|AAI|BSNL|BEML|NMDC|OIL INDIA|PFC|IREL|MDL|GRSE|ECIL|NALCO|UCIL|CIL|DMRC|NHAI|NBCC|EIL|UPRVUNL|UPPCL|DVC|THDC|SJVN|IREDA|RCFL|NFL|HURL|MECON|MOIL|CONCOR|IRFC|RVNL)\b")),
]


def _norm(text: str) -> str:
    return " " + re.sub(r"[^A-Z0-9.() ]", " ", (text or "").upper()) + " "


def infer_category(title: str, dept: str = "", org: str = "") -> str:
    text = _norm(f"{dept} {title} {org}")
    for slug, rx in _RULES:
        if rx.search(text):
            return slug
    return "government"


def infer_dept(title: str, category: str, existing: str = "") -> str:
    """Short department label shown as a badge (e.g. UPSSSC, RAILWAY)."""
    ex = (existing or "").strip()
    if ex and len(ex) <= 24 and not re.search(r"(?i)sarkari|rojgar|freejob|www|http|government$", ex):
        return ex
    key = _find_key(title, ORG_NAMES)
    if key:
        return key
    return CATEGORY_LABEL.get(category, "GOVERNMENT")

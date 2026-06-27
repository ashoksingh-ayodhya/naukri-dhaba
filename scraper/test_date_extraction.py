"""
Regression tests for date/fee/qualification extraction.

These pin the exact bug classes that have repeatedly corrupted scraped
content:

  1. Application deadlines silently dropped because the source phrased the
     label differently from the exact keys to_legacy_dict() looked for
     (e.g. "Last Date for Apply" vs "Last Date to Apply Online").
  2. "Last date" decoy rows (fee payment / NOC / correction windows)
     stolen as the apply-by date.
  3. Date / DOB-range rows misclassified as application fees, or textual
     month-name dates ("25 June 2026") not recognized as dates at all.

Pure-Python and dependency-free (no lxml / network) so it runs anywhere and
can gate CI cheaply. Run: `python3 test_date_extraction.py`
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from detail_parser.models import DetailData
from detail_parser.utils import looks_like_date_value, looks_like_fee_value

_failures: list[str] = []


def check(name: str, got, want) -> None:
    if got != want:
        _failures.append(f"{name}: got {got!r}, want {want!r}")


# ── 1. last_date recovery via fuzzy fallback ──────────────────────────────
# AIIMS-style page: real deadline labelled "Last Date for Apply", followed by
# fee/NOC decoy rows that also contain the words "Last Date".
check(
    "aiims_last_date_for_apply",
    DetailData(dates={
        "Application Begin": "06/06/2026",
        "Last Date for Apply": "20/06/2026",
        "Update Fee Payment Last Date": "23/06/2026",
        "NOC Submission Last Date": "08/07/2026",
    }).to_legacy_dict()["last_date"],
    "20/06/2026",
)

# Decoy appears BEFORE the real apply date — exclude guard must still skip it.
check(
    "decoy_before_real",
    DetailData(dates={
        "Update Fee Payment Last Date": "23/06/2026",
        "Last Date for Submission": "30/06/2026",
    }).to_legacy_dict()["last_date"],
    "30/06/2026",
)

# Only a fee decoy exists — must NOT be promoted to the application deadline.
check(
    "decoy_only_no_real_date",
    DetailData(dates={"Fee Payment Last Date": "23/06/2026"}).to_legacy_dict()["last_date"],
    "Check Notification",
)

# Exact-key match still wins and keeps the caller's priority ordering.
check(
    "exact_key_match",
    DetailData(dates={"Last Date to Apply Online": "27/07/2026"}).to_legacy_dict()["last_date"],
    "27/07/2026",
)

# app_begin is unaffected by the last_date fuzzy logic.
check(
    "app_begin_unaffected",
    DetailData(dates={
        "Application Begin": "06/06/2026",
        "Last Date for Apply": "20/06/2026",
    }).to_legacy_dict()["app_begin"],
    "06/06/2026",
)

# ── 2. Value-type classification regexes ──────────────────────────────────
# Textual month-name dates must be recognized as dates.
check("textual_date_is_date", looks_like_date_value("25 June 2026"), True)
check("numeric_date_is_date", looks_like_date_value("27/07/2026"), True)
# A DOB range is date-like (so it is NOT treated as a fee/qualification).
check("dob_range_is_date", looks_like_date_value("02 Jul 2002 to 01 Jul 2006"), True)

# Real fees are fees.
check("rupee_fee_is_fee", looks_like_fee_value("Rs. 500/-"), True)
check("free_is_fee", looks_like_fee_value("Nil"), True)
# A bare date / DOB range must NOT look like a fee (the old bug).
check("date_not_fee", looks_like_fee_value("02 Jul 2002 to 01 Jan 2008"), False)
check("plain_date_not_fee", looks_like_fee_value("27/07/2026"), False)


if _failures:
    print(f"FAILED — {len(_failures)} case(s):")
    for f in _failures:
        print(f"  ✗ {f}")
    sys.exit(1)
print("ALL DATE-EXTRACTION TESTS PASSED ✓")

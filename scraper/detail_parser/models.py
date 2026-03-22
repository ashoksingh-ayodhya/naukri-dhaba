"""
DetailData — the unified data model for scraped detail pages.

All fields are flexible dicts/lists so any number of dates, fees, links, or
vacancy rows render automatically without hardcoded field limits.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DetailData:
    """Complete structured data extracted from a detail page."""

    # ── Identity ──────────────────────────────────────────────
    title: str = ""
    slug: str = ""
    source: str = ""                    # "sarkariresult" | "freejobalert" etc.
    source_detail_url: str = ""         # URL of the source page itself
    page_type: str = ""                 # "job" | "result" | "admit"
    scraped_at: str = ""                # ISO timestamp

    # ── Header / Description ──────────────────────────────────
    post_name: str = ""                 # Full name with post count
    short_description: str = ""         # Opening paragraph
    post_date: str = ""                 # When first published
    update_date: str = ""               # When source last updated

    # ── Organization ──────────────────────────────────────────
    dept: str = ""                      # Department category
    organization_full_name: str = ""    # e.g. "Uttar Pradesh Subordinate Service Selection Commission (UPSSSC)"
    advertisement_number: str = ""      # e.g. "05-Exam/2024"

    # ── Important Dates ───────────────────────────────────────
    # Flexible dict: any number of dates, keys are human-readable labels
    # e.g. {"Application Begin": "18/04/2024", "Last Date": "18/05/2024", ...}
    dates: dict = field(default_factory=dict)

    # ── Application Fee ───────────────────────────────────────
    # Flexible dict: {"General / OBC / EWS": "25/-", "SC / ST": "25/-", ...}
    fees: dict = field(default_factory=dict)
    fee_payment_method: str = ""

    # ── Age Limit ─────────────────────────────────────────────
    age_min: int | None = None
    age_max: int | None = None
    age_reference_date: str = ""        # "as on 01/07/2024"
    age_relaxation_notes: str = ""

    # ── Vacancy Details ───────────────────────────────────────
    total_posts: str = ""
    # List of dicts, each: {"post_name": str, "general": str, "ews": str,
    #                        "obc": str, "sc": str, "st": str, "total": str,
    #                        "eligibility": str}
    vacancy_breakdown: list = field(default_factory=list)

    # ── Qualification ─────────────────────────────────────────
    qualification: str = ""
    qualification_items: list = field(default_factory=list)  # bullet points

    # ── Salary ────────────────────────────────────────────────
    salary: str = ""

    # ── How to Apply ──────────────────────────────────────────
    how_to_apply: list = field(default_factory=list)  # step-by-step strings

    # ── Important Links ───────────────────────────────────────
    # Each: {"label": str, "url": str, "link_type": str}
    # link_type: "result", "admit", "apply", "notification", "answer_key",
    #            "syllabus", "exam_city", "eligibility", "official_website", "other"
    important_links: list = field(default_factory=list)

    # ── Convenience URL accessors ─────────────────────────────
    apply_url: str = ""
    notification_url: str = ""
    result_url: str = ""
    scorecard_url: str = ""
    admit_url: str = ""
    official_website_url: str = ""

    # ── Extra / Download links ────────────────────────────────
    extra_links: list = field(default_factory=list)
    download_links: list = field(default_factory=list)

    # ── Listing-level fields ──────────────────────────────────
    date_str: str = ""

    def to_legacy_dict(self) -> dict:
        """Return a flat dict matching the old parse_detail() output.

        Ensures backward compatibility with existing build_*_page functions.
        """
        d = {
            "title": self.title,
            "slug": self.slug,
            "source": self.source,
            "source_detail_url": self.source_detail_url,
            "page_type": self.page_type,
            "dept": self.dept,
            "date_str": self.date_str,
            "post_date": self.post_date,
            "update_date": self.update_date,
            "organization_full_name": self.organization_full_name,
            "advertisement_number": self.advertisement_number,
            "short_description": self.short_description,
            # Legacy date fields — pick from dates dict
            "app_begin": self.dates.get("Application Begin", "Check Notification"),
            "last_date": self._first_date_match(
                ["Last Date for Registration", "Last Date for Apply Online",
                 "Last Date", "Closing Date"]
            ) or "Check Notification",
            "exam_date": self._first_date_match(
                ["Exam Date", "Examination Date"]
            ) or "As per Schedule",
            "result_date": self._first_date_match(
                ["Final Result Available", "Result Available", "Result Date"]
            ) or "Check Notification",
            "admit_release": self._first_date_match(
                ["Admit Card Available", "Admit Card Date"]
            ) or "Check Notification",
            # All dates for new template
            "dates": dict(self.dates),
            # Fees
            "fee_general": self.fees.get("General / OBC / EWS", ""),
            "fee_sc_st": self.fees.get("SC / ST", ""),
            "fees": dict(self.fees),
            "fee_payment_method": self.fee_payment_method,
            # Age
            "age_min": self.age_min if self.age_min is not None else 18,
            "age_max": self.age_max if self.age_max is not None else 35,
            "age_reference_date": self.age_reference_date,
            "age_relaxation_notes": self.age_relaxation_notes,
            # Vacancy
            "total_posts": self.total_posts,
            "vacancy_breakdown": list(self.vacancy_breakdown),
            # Qualification
            "qualification": self.qualification or "Check Notification",
            "qualification_items": list(self.qualification_items),
            # Salary
            "salary": self.salary or "As per Government Norms",
            # How to apply
            "how_to_apply": list(self.how_to_apply),
            # Links
            "apply_url": self.apply_url or "#",
            "notification_url": self.notification_url or "",
            "result_url": self.result_url or "#",
            "scorecard_url": self.scorecard_url or "",
            "admit_url": self.admit_url or "#",
            "official_website_url": self.official_website_url,
            "important_links": list(self.important_links),
            "extra_links": list(self.extra_links),
            "download_links": list(self.download_links),
        }
        return d

    def _first_date_match(self, keys: list[str]) -> str:
        """Return the first matching date from self.dates."""
        for k in keys:
            if k in self.dates:
                return self.dates[k]
        return ""

    def to_json(self) -> str:
        """Serialize to JSON for persistence alongside HTML pages."""
        data = {
            "version": 1,
            "scraped_at": self.scraped_at or datetime.now().isoformat(),
            "source": self.source,
            "source_detail_url": self.source_detail_url,
            "page_type": self.page_type,
            "title": self.title,
            "post_name": self.post_name,
            "post_date": self.post_date,
            "update_date": self.update_date,
            "organization_full_name": self.organization_full_name,
            "advertisement_number": self.advertisement_number,
            "short_description": self.short_description,
            "dept": self.dept,
            "dates": self.dates,
            "fees": self.fees,
            "fee_payment_method": self.fee_payment_method,
            "age_min": self.age_min,
            "age_max": self.age_max,
            "age_reference_date": self.age_reference_date,
            "age_relaxation_notes": self.age_relaxation_notes,
            "total_posts": self.total_posts,
            "vacancy_breakdown": self.vacancy_breakdown,
            "qualification": self.qualification,
            "qualification_items": self.qualification_items,
            "salary": self.salary,
            "how_to_apply": self.how_to_apply,
            "important_links": self.important_links,
            "apply_url": self.apply_url,
            "notification_url": self.notification_url,
            "result_url": self.result_url,
            "scorecard_url": self.scorecard_url,
            "admit_url": self.admit_url,
            "official_website_url": self.official_website_url,
            "extra_links": self.extra_links,
            "download_links": self.download_links,
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "DetailData":
        """Reconstruct from JSON string."""
        data = json.loads(text)
        return cls(
            title=data.get("title", ""),
            source=data.get("source", ""),
            source_detail_url=data.get("source_detail_url", ""),
            page_type=data.get("page_type", ""),
            scraped_at=data.get("scraped_at", ""),
            post_name=data.get("post_name", ""),
            post_date=data.get("post_date", ""),
            update_date=data.get("update_date", ""),
            organization_full_name=data.get("organization_full_name", ""),
            advertisement_number=data.get("advertisement_number", ""),
            short_description=data.get("short_description", ""),
            dept=data.get("dept", ""),
            dates=data.get("dates", {}),
            fees=data.get("fees", {}),
            fee_payment_method=data.get("fee_payment_method", ""),
            age_min=data.get("age_min"),
            age_max=data.get("age_max"),
            age_reference_date=data.get("age_reference_date", ""),
            age_relaxation_notes=data.get("age_relaxation_notes", ""),
            total_posts=data.get("total_posts", ""),
            vacancy_breakdown=data.get("vacancy_breakdown", []),
            qualification=data.get("qualification", ""),
            qualification_items=data.get("qualification_items", []),
            salary=data.get("salary", ""),
            how_to_apply=data.get("how_to_apply", []),
            important_links=data.get("important_links", []),
            apply_url=data.get("apply_url", ""),
            notification_url=data.get("notification_url", ""),
            result_url=data.get("result_url", ""),
            scorecard_url=data.get("scorecard_url", ""),
            admit_url=data.get("admit_url", ""),
            official_website_url=data.get("official_website_url", ""),
            extra_links=data.get("extra_links", []),
            download_links=data.get("download_links", []),
        )

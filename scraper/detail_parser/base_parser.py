"""
Abstract base parser for detail pages.

Provides the orchestration flow and shared post-processing logic.
Source-specific parsers override _extract_* methods.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime

from bs4 import BeautifulSoup

from scraper.detail_parser.models import DetailData
from scraper.detail_parser.utils import classify_link

log = logging.getLogger("NaukriDhaba")


class BaseDetailParser(ABC):
    """Abstract base for source-specific detail page parsers."""

    def parse(self, soup: BeautifulSoup | None, item: dict, source_name: str = "") -> DetailData:
        """Main entry point — orchestrates extraction and post-processing."""
        data = DetailData(
            title=item.get("title", ""),
            slug=item.get("slug", ""),
            source=source_name,
            source_detail_url=item.get("source_detail_url", item.get("detail_url", "")),
            page_type=item.get("page_type", ""),
            date_str=item.get("date_str", ""),
            dept=item.get("dept", ""),
            scraped_at=datetime.now().isoformat(),
        )

        if not soup:
            log.warning(f"  [parser] No soup for {data.title[:60]} — returning defaults")
            return data

        self._extract_header(soup, data)
        self._extract_dates_and_fees(soup, data)
        self._extract_age(soup, data)
        self._extract_vacancy(soup, data)
        self._extract_qualification(soup, data)
        self._extract_salary(soup, data)
        self._extract_how_to_apply(soup, data)
        self._extract_important_links(soup, data)
        self._extract_downloads(soup, data)
        self._post_process(data)

        return data

    # ── Abstract methods — override per source ────────────────

    @abstractmethod
    def _extract_header(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract title, post_date, short_description, org name, advt number."""

    @abstractmethod
    def _extract_dates_and_fees(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract all dates and fees into data.dates and data.fees."""

    @abstractmethod
    def _extract_age(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract age_min, age_max, age_reference_date, age_relaxation_notes."""

    @abstractmethod
    def _extract_vacancy(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract total_posts and vacancy_breakdown."""

    @abstractmethod
    def _extract_qualification(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract qualification text and qualification_items."""

    @abstractmethod
    def _extract_salary(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract salary information."""

    @abstractmethod
    def _extract_how_to_apply(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract how_to_apply steps list."""

    @abstractmethod
    def _extract_important_links(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract important_links list with label, url, link_type."""

    @abstractmethod
    def _extract_downloads(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract download_links list."""

    # ── Shared post-processing ────────────────────────────────

    def _post_process(self, data: DetailData) -> None:
        """Populate convenience URLs from important_links, deduplicate."""

        # Classify links that don't have a type yet
        for link in data.important_links:
            if not link.get("link_type"):
                link["link_type"] = classify_link(link.get("label", ""))

        # Populate convenience URL fields from important_links
        for link in data.important_links:
            url = link.get("url", "")
            lt = link.get("link_type", "")
            if not url or url == "#":
                continue

            if lt == "apply" and not data.apply_url:
                data.apply_url = url
            elif lt == "notification" and not data.notification_url:
                data.notification_url = url
            elif lt == "result" and not data.result_url:
                data.result_url = url
            elif lt == "scorecard" and not data.scorecard_url:
                data.scorecard_url = url
            elif lt in ("admit",) and not data.admit_url:
                data.admit_url = url
            elif lt == "official_website" and not data.official_website_url:
                data.official_website_url = url

        # Also populate extra_links from important_links for backward compat
        seen = set()
        for link in data.important_links:
            url = link.get("url", "")
            if url and url != "#" and url not in seen:
                seen.add(url)
                data.extra_links.append({
                    "label": link.get("label", "Official Link"),
                    "url": url,
                })

        # Deduplicate download_links
        dl_seen = set()
        unique_dls = []
        for dl in data.download_links:
            url = dl.get("url", "")
            if url and url != "#" and url not in dl_seen:
                dl_seen.add(url)
                unique_dls.append(dl)
        data.download_links = unique_dls

"""
Parser for sarkariexam.com detail pages.

Layout: Uses <div> and <table> hybrid layouts with different section
header patterns. Similar data structure to sarkariresult.
"""

from __future__ import annotations

import re
import logging

from bs4 import BeautifulSoup

from scraper.detail_parser.sarkariresult import SarkariResultParser
from scraper.detail_parser.models import DetailData
from scraper.detail_parser.utils import clean, is_junk_row

log = logging.getLogger("NaukriDhaba")


class SarkariExamParser(SarkariResultParser):
    """Parses sarkariexam.com detail pages.

    Extends SarkariResultParser since the data structure is similar.
    Overrides header extraction and link parsing.
    """

    def _extract_header(self, soup: BeautifulSoup, data: DetailData) -> None:
        """SarkariExam uses article-style headers."""
        # Title from <h1> or <h2>
        for tag in soup.find_all(["h1", "h2"]):
            text = clean(tag.get_text())
            if text and len(text) > 10 and not re.search(r'sarkari\s*exam', text, re.I):
                data.post_name = text
                if not data.title:
                    data.title = text
                break

        # Content area
        content = soup.find("div", class_="entry-content") or soup.find("article") or soup

        # Short description from first <p>
        for p in content.find_all("p", limit=5):
            text = clean(p.get_text())
            if len(text) > 50 and not re.search(r'sarkariexam|www\.', text, re.I):
                data.short_description = text
                break

        # Organization from bold text
        for tag in content.find_all(["b", "strong"]):
            text = clean(tag.get_text())
            if re.search(r'(commission|board|council|ministry|department|university)', text, re.I):
                if not re.search(r'sarkari|www\.|\.com', text, re.I):
                    data.organization_full_name = text
                    break

        # Advt number
        for tag in content.find_all(["p", "b", "strong", "span"]):
            text = clean(tag.get_text())
            m = re.search(r'(?:advt|advertisement|notification)\s*(?:no\.?|number)\s*[:\-]?\s*(.+)', text, re.I)
            if m and not data.advertisement_number:
                data.advertisement_number = clean(m.group(1))
                break

        # Post date from meta or time tag
        time_tag = soup.find("time")
        if time_tag:
            data.post_date = clean(time_tag.get_text()) or time_tag.get("datetime", "")

    def _extract_important_links(self, soup: BeautifulSoup, data: DetailData) -> None:
        """SarkariExam may use different link section markers."""
        # Try parent implementation first
        super()._extract_important_links(soup, data)

        # If no links found, scan all anchors with meaningful text
        if not data.important_links:
            content = soup.find("div", class_="entry-content") or soup.find("article") or soup
            for a in content.find_all("a", href=True):
                href = a.get("href", "").strip()
                text = clean(a.get_text())
                if not href or href == "#" or not text:
                    continue
                if is_junk_row(text):
                    continue
                if re.search(r'(apply|result|admit|notification|answer\s*key|syllabus|download)', text, re.I):
                    from scraper.detail_parser.utils import classify_link
                    data.important_links.append({
                        "label": text,
                        "url": href,
                        "link_type": classify_link(text),
                    })

            # Deduplicate
            seen = set()
            unique = []
            for link in data.important_links:
                url = link.get("url", "")
                if url not in seen:
                    seen.add(url)
                    unique.append(link)
            data.important_links = unique

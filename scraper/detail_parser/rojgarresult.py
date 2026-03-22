"""
Parser for rojgarresult.com detail pages.

Layout: Similar table-based layout to sarkariresult but with different
CSS classes and slightly different label text.
"""

from __future__ import annotations

import re
import logging

from bs4 import BeautifulSoup

from scraper.detail_parser.sarkariresult import SarkariResultParser
from scraper.detail_parser.models import DetailData
from scraper.detail_parser.utils import clean, is_junk_row

log = logging.getLogger("NaukriDhaba")


class RojgarResultParser(SarkariResultParser):
    """Parses rojgarresult.com detail pages.

    Extends SarkariResultParser since the table layout is very similar.
    Overrides only what differs.
    """

    def _extract_header(self, soup: BeautifulSoup, data: DetailData) -> None:
        """RojgarResult uses similar header structure but with different markers."""
        # Try <h1>/<h2> first
        for tag in soup.find_all(["h1", "h2", "h3"]):
            text = clean(tag.get_text())
            if text and len(text) > 15 and not re.search(r'rojgar\s*result', text, re.I):
                data.post_name = text
                if not data.title:
                    data.title = text
                break

        # Organization and advt from bold/strong text
        for tag in soup.find_all(["b", "strong", "span", "p"]):
            text = clean(tag.get_text())
            if not text or len(text) < 10:
                continue

            if re.search(r'(commission|board|council|ministry|department|university|corporation)', text, re.I):
                if not re.search(r'rojgar|www\.|\.com', text, re.I):
                    if not data.organization_full_name or len(text) > len(data.organization_full_name):
                        data.organization_full_name = text

            m = re.search(r'(?:advt|advertisement|notification)\s*(?:no\.?|number)\s*[:\-]?\s*(.+)', text, re.I)
            if m and not data.advertisement_number:
                data.advertisement_number = clean(m.group(1))

        # Table-based header rows
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                label = clean(cells[0].get_text()).lower()
                val = clean(cells[-1].get_text())

                if "name of post" in label or "post name" in label:
                    data.post_name = val
                    if not data.title or len(val) > len(data.title):
                        data.title = val

                elif re.search(r'post\s*date|update\s*date', label) and val:
                    data.post_date = val

                elif "short information" in label or "brief info" in label:
                    data.short_description = clean(cells[-1].get_text())

    def _extract_important_links(self, soup: BeautifulSoup, data: DetailData) -> None:
        """RojgarResult uses similar link tables but may use different styling."""
        # Call parent implementation — table structure is similar
        super()._extract_important_links(soup, data)

        # Additional: scan for link sections with different markers
        # RojgarResult sometimes uses colored backgrounds instead of #FF6600
        if not data.important_links:
            for table in soup.find_all("table"):
                for tr in table.find_all("tr"):
                    cells = tr.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue
                    full_text = clean(tr.get_text())
                    if is_junk_row(full_text):
                        continue

                    value_cell = cells[-1]
                    anchors = value_cell.find_all("a", href=True)
                    if anchors:
                        label = clean(cells[0].get_text())
                        if label and not is_junk_row(label):
                            from scraper.detail_parser.utils import classify_link
                            for a in anchors:
                                href = a.get("href", "").strip()
                                if href and href != "#":
                                    data.important_links.append({
                                        "label": label,
                                        "url": href,
                                        "link_type": classify_link(label),
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

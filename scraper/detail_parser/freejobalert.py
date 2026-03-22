"""
Parser for freejobalert.com detail pages.

Layout: Uses <article> / .entry-content with mix of <p>, <table>, and <div>.
Bold text labels followed by colon-separated values.
"""

from __future__ import annotations

import re
import logging

from bs4 import BeautifulSoup, Tag

from scraper.detail_parser.base_parser import BaseDetailParser
from scraper.detail_parser.models import DetailData
from scraper.detail_parser.utils import (
    clean, classify_link, is_junk_row,
    looks_like_date_value, looks_like_fee_value,
    extract_age_reference_date,
)

log = logging.getLogger("NaukriDhaba")


class FreeJobAlertParser(BaseDetailParser):
    """Parses freejobalert.com detail pages."""

    def _get_content_area(self, soup: BeautifulSoup) -> Tag | None:
        """Get the main content area."""
        content = soup.find("div", class_="entry-content")
        if not content:
            content = soup.find("article")
        return content or soup

    def _extract_header(self, soup: BeautifulSoup, data: DetailData) -> None:
        content = self._get_content_area(soup)

        # Title from <h1> or <h2>
        for tag in soup.find_all(["h1", "h2"]):
            text = clean(tag.get_text())
            if text and len(text) > 10 and not re.search(r'freejobalert|comment', text, re.I):
                data.post_name = text
                if not data.title:
                    data.title = text
                break

        # Short description — first substantial <p> in content
        for p in content.find_all("p", limit=5):
            text = clean(p.get_text())
            if len(text) > 50 and not re.search(r'freejobalert|www\.', text, re.I):
                data.short_description = text
                break

        # Org name from bold text
        for tag in content.find_all(["b", "strong"]):
            text = clean(tag.get_text())
            if re.search(r'(commission|board|council|ministry|department|university)', text, re.I):
                if not re.search(r'freejobalert|www\.', text, re.I):
                    data.organization_full_name = text
                    break

        # Advt number
        for tag in content.find_all(["p", "b", "strong", "span"]):
            text = clean(tag.get_text())
            m = re.search(r'(?:advt|advertisement|notification)\s*(?:no\.?|number)\s*[:\-]?\s*(.+)', text, re.I)
            if m and not data.advertisement_number:
                data.advertisement_number = clean(m.group(1))
                break

    def _extract_dates_and_fees(self, soup: BeautifulSoup, data: DetailData) -> None:
        content = self._get_content_area(soup)

        # FreeJobAlert uses tables similar to sarkariresult
        for table in content.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                label = clean(cells[0].get_text())
                val = clean(cells[-1].get_text())

                if looks_like_date_value(val) and len(label) > 3:
                    if not is_junk_row(label):
                        data.dates[label] = val

                elif looks_like_fee_value(val) and re.search(r'(general|sc|st|obc|ews|ph|female|all)', label, re.I):
                    data.fees[label] = val

                elif re.search(r'(through|via|challan|pay\s*the)', val, re.I):
                    data.fee_payment_method = val

        # Also scan <p> and <li> for "Label : Value" patterns with dates
        for tag in content.find_all(["p", "li"]):
            text = clean(tag.get_text())
            m = re.match(r'^(.+?)\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}.*)$', text)
            if m:
                label = clean(m.group(1))
                val = clean(m.group(2))
                if not is_junk_row(label) and label not in data.dates:
                    data.dates[label] = val

    def _extract_age(self, soup: BeautifulSoup, data: DetailData) -> None:
        content = self._get_content_area(soup)

        for tag in content.find_all(["p", "li", "td"]):
            text = clean(tag.get_text())

            if re.search(r'age\s*limit', text, re.I):
                ref = extract_age_reference_date(text)
                if ref:
                    data.age_reference_date = ref

            if re.search(r'minimum\s*age', text, re.I):
                m = re.search(r'(\d+)', text)
                if m:
                    data.age_min = int(m.group(1))

            elif re.search(r'maximum\s*age', text, re.I):
                m = re.search(r'(\d+)', text)
                if m:
                    data.age_max = int(m.group(1))

            if re.search(r'age\s*relaxation', text, re.I) and not data.age_relaxation_notes:
                data.age_relaxation_notes = text

    def _extract_vacancy(self, soup: BeautifulSoup, data: DetailData) -> None:
        content = self._get_content_area(soup)

        for table in content.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                label = clean(cells[0].get_text()).lower()
                val = clean(cells[-1].get_text())

                if re.search(r'total\s*(post|vacanc)', label):
                    m = re.search(r'[\d,]+', val)
                    if m:
                        data.total_posts = m.group().replace(",", "")

        # Category-wise table detection (same logic as sarkariresult)
        for table in content.find_all("table"):
            headers = [clean(th.get_text()).lower() for th in table.find_all("th")]
            if not headers:
                first_row = table.find("tr")
                if first_row:
                    headers = [clean(td.get_text()).lower() for td in first_row.find_all(["td", "th"])]

            if any("general" in h for h in headers) and any("total" in h for h in headers):
                for tr in table.find_all("tr")[1:]:
                    cells = tr.find_all(["td", "th"])
                    vals = [clean(c.get_text()) for c in cells]
                    if len(vals) >= 3 and not any("post name" in v.lower() for v in vals):
                        entry = {"post_name": vals[0]}
                        for i, h in enumerate(headers):
                            if i < len(vals) and i > 0:
                                key = re.sub(r'[^a-z_]', '', h.replace(" ", "_"))
                                entry[key] = vals[i]
                        data.vacancy_breakdown.append(entry)

    def _extract_qualification(self, soup: BeautifulSoup, data: DetailData) -> None:
        content = self._get_content_area(soup)

        for table in content.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                label = clean(cells[0].get_text()).lower()
                if re.search(r'qualification|education|eligibility', label):
                    val_cell = cells[-1]
                    items = val_cell.find_all("li")
                    if items:
                        data.qualification_items = [clean(li.get_text()) for li in items if clean(li.get_text())]
                        data.qualification = "; ".join(data.qualification_items)
                    else:
                        data.qualification = clean(val_cell.get_text())

    def _extract_salary(self, soup: BeautifulSoup, data: DetailData) -> None:
        content = self._get_content_area(soup)

        for table in content.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                label = clean(cells[0].get_text()).lower()
                val = clean(cells[-1].get_text())
                if re.search(r'salary|pay\s*scale|pay\s*band|ctc|stipend', label):
                    data.salary = val

    def _extract_how_to_apply(self, soup: BeautifulSoup, data: DetailData) -> None:
        content = self._get_content_area(soup)
        found = False

        for tag in content.find_all(["h2", "h3", "h4", "b", "strong", "p"]):
            text = clean(tag.get_text())
            if re.search(r'how\s*to\s*(apply|fill)', text, re.I):
                found = True
                # Collect subsequent <li> items
                for li in tag.find_all_next("li", limit=15):
                    step = clean(li.get_text())
                    if step and not is_junk_row(step) and len(step) > 10:
                        data.how_to_apply.append(step)
                    if li.find_next_sibling(["h2", "h3", "h4"]):
                        break
                break

        # Deduplicate
        if data.how_to_apply:
            seen = set()
            data.how_to_apply = [s for s in data.how_to_apply if s not in seen and not seen.add(s)]

    def _extract_important_links(self, soup: BeautifulSoup, data: DetailData) -> None:
        content = self._get_content_area(soup)
        in_links = False

        for table in content.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                full_text = clean(tr.get_text())

                if re.search(r'important\s*links?', full_text, re.I):
                    in_links = True
                    continue

                if is_junk_row(full_text):
                    continue

                if len(cells) >= 2:
                    label = clean(cells[0].get_text())
                    value_cell = cells[-1]

                    has_link = bool(value_cell.find("a", href=True))
                    if (in_links or has_link) and label and not is_junk_row(label):
                        for a in value_cell.find_all("a", href=True):
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

    def _extract_downloads(self, soup: BeautifulSoup, data: DetailData) -> None:
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            if href and re.search(r'\.(pdf|doc|docx|xls|xlsx)(\?.*)?$', href, re.I):
                label = clean(a.get_text()) or "Download"
                data.download_links.append({"label": label, "url": href})

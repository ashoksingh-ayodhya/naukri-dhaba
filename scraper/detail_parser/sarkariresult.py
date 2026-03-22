"""
Parser for sarkariresult.com detail pages.

Layout: All data in <table> rows, two columns (label | value).
Link rows identified by bgcolor="#FF6600" or similar orange styling.
Dates and Fees are in a single table side by side.
Vacancy breakdown in sub-tables with category columns.
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


class SarkariResultParser(BaseDetailParser):
    """Parses sarkariresult.com orange-theme table-based detail pages."""

    def _extract_header(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract post name, date, short description, org, advt number."""

        # The page structure uses table rows for header info:
        # "Name of Post:" row, "Post Date / Update:" row, "Short Information:" row
        all_text = soup.get_text(" ", strip=True)

        # Post name — try <h1>/<h2> first, then table rows
        for tag in soup.find_all(["h1", "h2"]):
            text = clean(tag.get_text())
            if text and len(text) > 15 and not re.search(r'sarkari\s*result', text, re.I):
                data.post_name = text
                if not data.title:
                    data.title = text
                break

        # Organization name and advt number from bold/colored text blocks
        for tag in soup.find_all(["b", "strong", "span", "p", "font"]):
            text = clean(tag.get_text())
            if not text or len(text) < 10:
                continue

            # Organization: look for pattern like "Uttar Pradesh ... Commission (UPSSSC)"
            if re.search(r'(commission|board|council|ministry|department|university|corporation|authority)\b', text, re.I):
                if not re.search(r'sarkari|www\.|\.com', text, re.I):
                    if not data.organization_full_name or len(text) > len(data.organization_full_name):
                        data.organization_full_name = text

            # Advt number: "Advt No. : 05-Exam/2024"
            m = re.search(r'(?:advt|advertisement|notification)\s*(?:no\.?|number)\s*[:\-]?\s*([\w\-/]+)', text, re.I)
            if m and not data.advertisement_number:
                data.advertisement_number = clean(m.group(1))

        # Walk all tables to find header rows
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) < 1:
                    continue
                label = clean(cells[0].get_text()).lower()
                val = clean(cells[-1].get_text()) if len(cells) > 1 else ""

                if "name of post" in label and val:
                    data.post_name = val
                    if not data.title or len(val) > len(data.title):
                        data.title = val

                elif re.search(r'post\s*date|update', label) and val:
                    data.post_date = val
                    # Try to separate update date
                    parts = re.split(r'\|', val)
                    if len(parts) >= 1:
                        data.post_date = clean(parts[0])
                    if len(parts) >= 2:
                        data.update_date = clean(parts[-1])

                elif "short information" in label:
                    # The value might span the cell or be in a child element
                    desc_cell = cells[-1] if len(cells) > 1 else cells[0]
                    data.short_description = clean(desc_cell.get_text())

    def _extract_dates_and_fees(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract all dates and fees from the tables.

        SarkariResult uses a side-by-side layout:
        - Header row: "Important Dates" | "Application Fee"
        - Next row: <ul> dates </ul> | <ul> fees </ul>
        Also handles individual date/fee rows in 2-column tables.
        """

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for i, tr in enumerate(rows):
                cells = tr.find_all(["td", "th"])
                if not cells:
                    continue

                full_text = clean(tr.get_text())

                # Detect header row: "Important Dates" | "Application Fee"
                is_dates_fee_header = (
                    re.search(r'important\s*dates?', full_text, re.I) or
                    re.search(r'application\s*fee', full_text, re.I)
                )

                if is_dates_fee_header:
                    # The actual data is either in THIS row's cells (if they
                    # contain <li> items) or in the NEXT row.
                    dates_cell = None
                    fees_cell = None

                    # Check if this row's cells have list items (data in same row)
                    for c_idx, cell in enumerate(cells):
                        cell_text = clean(cell.get_text())
                        has_items = bool(cell.find("li"))
                        if re.search(r'important\s*dates?', cell_text, re.I):
                            if has_items:
                                dates_cell = cell
                            # Otherwise just a header label
                        elif re.search(r'application\s*fee', cell_text, re.I):
                            if has_items:
                                fees_cell = cell

                    # If no list items in header row, check NEXT row
                    if not dates_cell and not fees_cell and i + 1 < len(rows):
                        next_cells = rows[i + 1].find_all(["td", "th"])
                        if len(next_cells) >= 2:
                            dates_cell = next_cells[0]
                            fees_cell = next_cells[1]
                        elif len(next_cells) == 1:
                            dates_cell = next_cells[0]

                    if dates_cell:
                        self._parse_dates_cell(dates_cell, data)
                    if fees_cell:
                        self._parse_fees_cell(fees_cell, data)
                    continue

                # Parse individual date/fee rows (non-bullet format, 2-column tables)
                if len(cells) >= 2:
                    label = clean(cells[0].get_text())
                    val = clean(cells[-1].get_text())

                    # Skip rows that are clearly not date/fee rows
                    if re.search(r'(name\s*of\s*post|post\s*date|short\s*info|www\.)', label, re.I):
                        continue

                    if looks_like_date_value(val) and self._is_date_label(label):
                        data.dates[label] = val

                    elif looks_like_fee_value(val) and self._is_fee_label(label) and len(label) < 80:
                        data.fees[label] = val
                        pay_text = clean(tr.get_text())
                        if re.search(r'(through|via|mode|challan|debit|credit|net banking|upi)', pay_text, re.I):
                            if not data.fee_payment_method:
                                data.fee_payment_method = self._extract_payment_method(pay_text)

    def _parse_dates_cell(self, cell: Tag, data: DetailData) -> None:
        """Parse a cell containing bullet-list dates."""
        # Look for list items
        items = cell.find_all("li")
        if items:
            for li in items:
                text = clean(li.get_text())
                self._extract_kv_date(text, data)
            return

        # Fallback: split by newlines or bullet chars
        text = cell.get_text("\n")
        for line in text.split("\n"):
            line = clean(line)
            if line and ":" in line:
                self._extract_kv_date(line, data)

    def _parse_fees_cell(self, cell: Tag, data: DetailData) -> None:
        """Parse a cell containing fee information."""
        items = cell.find_all("li")
        lines = []
        if items:
            lines = [clean(li.get_text()) for li in items]
        else:
            lines = [clean(l) for l in cell.get_text("\n").split("\n") if clean(l)]

        for line in lines:
            if ":" in line:
                parts = line.split(":", 1)
                label = clean(parts[0])
                val = clean(parts[1])
                if looks_like_fee_value(val) and not is_junk_row(label):
                    data.fees[label] = val
                elif re.search(r'(through|via|mode|challan|pay\s*the)', line, re.I):
                    data.fee_payment_method = line

            elif re.search(r'(through|via|mode|challan|pay\s*the)', line, re.I):
                data.fee_payment_method = line

    def _extract_kv_date(self, text: str, data: DetailData) -> None:
        """Extract a key:value date pair from a line like 'Application Begin : 18/04/2024'."""
        # Split on last colon that precedes a date-like value
        m = re.match(r'^(.+?)\s*:\s*(.+)$', text)
        if m:
            label = clean(m.group(1))
            val = clean(m.group(2))
            if looks_like_date_value(val) and not is_junk_row(label):
                data.dates[label] = val

    def _extract_payment_method(self, text: str) -> str:
        """Extract the payment method sentence from fee text."""
        # Look for sentences with payment keywords
        sentences = re.split(r'[.•]', text)
        for s in sentences:
            s = clean(s)
            if re.search(r'(pay|through|via|challan|debit|credit|net banking|upi|sbi)', s, re.I):
                return s
        return ""

    def _is_date_label(self, label: str) -> bool:
        return bool(re.search(
            r'(application|last\s*date|closing|exam|admit|result|answer\s*key|'
            r'correction|fee\s*payment|eligibility|city|counsell|interview|'
            r'declaration|begin|start|available|release)',
            label, re.I
        ))

    def _is_fee_label(self, label: str) -> bool:
        return bool(re.search(
            r'(general|obc|ews|sc\s*/\s*st|\bsc\b|\bst\b|\bph\b|pwd|dviyang|female|'
            r'unreserved|reserved|all\s*categor)',
            label, re.I
        ))

    def _extract_age(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract age limits from the page."""
        # Also check bold/strong tags for "Age Limit as on DD/MM/YYYY"
        for tag in soup.find_all(["b", "strong", "h2", "h3", "h4", "p", "font", "span"]):
            text = clean(tag.get_text())
            if re.search(r'age\s*limit', text, re.I):
                ref = extract_age_reference_date(text)
                if ref:
                    data.age_reference_date = ref

        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                text = clean(tr.get_text())

                if re.search(r'age\s*limit', text, re.I):
                    ref = extract_age_reference_date(text)
                    if ref:
                        data.age_reference_date = ref

                cells = tr.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                label = clean(cells[0].get_text()).lower()
                val = clean(cells[-1].get_text())

                if re.search(r'minimum\s*age|min\.?\s*age', label):
                    m = re.search(r'\d+', val)
                    if m:
                        data.age_min = int(m.group())

                elif re.search(r'maximum\s*age|max\.?\s*age', label):
                    m = re.search(r'\d+', val)
                    if m:
                        data.age_max = int(m.group())

                elif re.search(r'age\s*limit', label) and re.search(r'\d+', val):
                    nums = re.findall(r'\d+', val)
                    if len(nums) >= 2:
                        data.age_min = int(nums[0])
                        data.age_max = int(nums[1])
                    elif len(nums) == 1:
                        data.age_max = int(nums[0])

        # Age relaxation notes — look for bullet points after age limit header
        for tag in soup.find_all(["li", "p"]):
            text = clean(tag.get_text())
            if re.search(r'age\s*relaxation', text, re.I) and not data.age_relaxation_notes:
                data.age_relaxation_notes = text

    def _extract_vacancy(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract total posts and category-wise vacancy breakdown."""
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                label = clean(cells[0].get_text()).lower()
                val = clean(cells[-1].get_text())

                if re.search(r'total\s*post|vacancy|vacancies|total\s*vacancy', label):
                    m = re.search(r'[\d,]+', val)
                    if m:
                        data.total_posts = m.group().replace(",", "")

        # Also check header text for "Total : XXX Post"
        for tag in soup.find_all(["b", "strong", "h2", "h3", "h4", "font", "span"]):
            text = clean(tag.get_text())
            m = re.search(r'total\s*:?\s*([\d,]+)\s*post', text, re.I)
            if m and not data.total_posts:
                data.total_posts = m.group(1).replace(",", "")

        # Category-wise vacancy table
        # Look for tables with headers: Post Name | General | EWS | OBC | SC | ST | Total
        for table in soup.find_all("table"):
            headers = [clean(th.get_text()).lower() for th in table.find_all("th")]
            # Also check first row as header
            first_row = table.find("tr")
            if first_row and not headers:
                headers = [clean(td.get_text()).lower() for td in first_row.find_all(["td", "th"])]

            has_category_cols = (
                any("general" in h for h in headers) and
                any(re.search(r'\bsc\b', h) for h in headers) and
                any("total" in h for h in headers)
            )

            if has_category_cols:
                rows = table.find_all("tr")[1:]  # skip header row
                for tr in rows:
                    cells = tr.find_all(["td", "th"])
                    if len(cells) < 3:
                        continue
                    vals = [clean(c.get_text()) for c in cells]
                    # Skip rows that are just headers repeated
                    if any("post name" in v.lower() for v in vals):
                        continue

                    entry = {"post_name": vals[0]}
                    # Map remaining values to category columns
                    # Standard order: Post Name | General | EWS | OBC | SC | ST | Total
                    cat_keys = []
                    for h in headers:
                        if "general" in h or "ur" == h:
                            cat_keys.append("general")
                        elif "ews" in h:
                            cat_keys.append("ews")
                        elif "obc" in h:
                            cat_keys.append("obc")
                        elif re.match(r'\bsc\b', h):
                            cat_keys.append("sc")
                        elif re.match(r'\bst\b', h):
                            cat_keys.append("st")
                        elif "total" in h:
                            cat_keys.append("total")
                        elif "post name" in h or "name" in h:
                            cat_keys.append("post_name")
                        elif "eligibility" in h or "qualification" in h:
                            cat_keys.append("eligibility")
                        else:
                            cat_keys.append(h)

                    for i, v in enumerate(vals):
                        if i < len(cat_keys) and cat_keys[i] != "post_name":
                            entry[cat_keys[i]] = v

                    if entry.get("post_name") and entry.get("total", entry.get("general", "")):
                        data.vacancy_breakdown.append(entry)

        # Simple vacancy table: Post Name | Total Post | Eligibility
        if not data.vacancy_breakdown:
            for table in soup.find_all("table"):
                headers = []
                first_row = table.find("tr")
                if first_row:
                    headers = [clean(td.get_text()).lower() for td in first_row.find_all(["td", "th"])]

                has_simple = (
                    any("post name" in h or "name" in h for h in headers) and
                    any("total" in h or "post" in h for h in headers)
                )

                if has_simple and len(headers) >= 2:
                    rows = table.find_all("tr")[1:]
                    for tr in rows:
                        cells = tr.find_all(["td", "th"])
                        if len(cells) < 2:
                            continue
                        vals = [clean(c.get_text()) for c in cells]
                        if any("post name" in v.lower() for v in vals):
                            continue
                        entry = {"post_name": vals[0], "total": vals[1] if len(vals) > 1 else ""}
                        if len(vals) > 2:
                            entry["eligibility"] = vals[2]
                        if entry["post_name"]:
                            data.vacancy_breakdown.append(entry)

    def _extract_qualification(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract qualification info from table rows and bullet lists."""
        # Check vacancy table for eligibility column
        for entry in data.vacancy_breakdown:
            if entry.get("eligibility"):
                data.qualification = entry["eligibility"]

        # Look for qualification section in tables
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                label = clean(cells[0].get_text()).lower()
                if re.search(r'qualification|education|eligibility', label):
                    val_cell = cells[-1]
                    # Get bullet items if present
                    items = val_cell.find_all("li")
                    if items:
                        data.qualification_items = [clean(li.get_text()) for li in items if clean(li.get_text())]
                        data.qualification = "; ".join(data.qualification_items)
                    else:
                        data.qualification = clean(val_cell.get_text())

    def _extract_salary(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract salary/pay scale from table rows."""
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                label = clean(cells[0].get_text()).lower()
                val = clean(cells[-1].get_text())
                if re.search(r'salary|pay\s*scale|pay\s*band|ctc|stipend', label):
                    data.salary = val

    def _extract_how_to_apply(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract how-to-apply steps.

        SarkariResult puts these in bullet/numbered lists after a
        'How to Fill' or 'How to Apply' header. We find the header element,
        then look for the NEAREST <ul>/<ol> that follows it, and extract only
        those <li> items.
        """
        # Find the "How to Fill/Apply" header
        header_tag = None
        for tag in soup.find_all(["b", "strong", "h2", "h3", "h4", "font", "span", "p"]):
            text = clean(tag.get_text())
            if re.search(r'how\s*to\s*(fill|apply)', text, re.I):
                header_tag = tag
                break

        if not header_tag:
            return

        # Find the next <ul> or <ol> after the header (not just any <li>)
        # Walk forward from the header to find the list container
        list_container = header_tag.find_next(["ul", "ol"])
        if not list_container:
            return

        # Only extract <li> from THIS specific list, not from other lists on the page
        for li in list_container.find_all("li", recursive=False):
            step_text = clean(li.get_text())
            if step_text and not is_junk_row(step_text) and len(step_text) > 10:
                # Skip items that look like dates (from the dates section)
                if re.match(r'^(Application|Last Date|Fee Payment|Correction|Eligibility|Exam|Admit|Answer|Revised|Final Result)', step_text):
                    continue
                # Skip items that look like fees
                if re.match(r'^(General|SC\s*/\s*ST|PH|Pay the)', step_text):
                    continue
                data.how_to_apply.append(step_text)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for step in data.how_to_apply:
            if step not in seen:
                seen.add(step)
                unique.append(step)
        data.how_to_apply = unique

    def _extract_important_links(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract important links from the orange-highlighted link table.

        SarkariResult marks link rows with bgcolor="#FF6600" and the
        "Some Useful Important Links" header.
        """
        in_links_section = False

        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                if not cells:
                    continue

                full_text = clean(tr.get_text())

                # Detect links section header
                if re.search(r'(some\s*)?useful\s*important\s*links?|important\s*links?', full_text, re.I):
                    in_links_section = True
                    continue

                # Skip junk rows
                if is_junk_row(full_text):
                    continue

                if len(cells) >= 2:
                    label_cell = cells[0]
                    value_cell = cells[-1]
                    label = clean(label_cell.get_text())
                    val_text = clean(value_cell.get_text())

                    # Check for orange/link row styling
                    bg = label_cell.get("bgcolor", "").lower() if hasattr(label_cell, "get") else ""
                    style = label_cell.get("style", "").lower() if hasattr(label_cell, "get") else ""
                    is_link_row = (
                        "#ff6600" in bg or "ff6600" in style or "orange" in style or
                        in_links_section or
                        re.search(r'click\s*here', val_text, re.I) is not None
                    )

                    if is_link_row and label and not is_junk_row(label):
                        # Extract all anchor hrefs from the value cell
                        anchors = value_cell.find_all("a", href=True)
                        if anchors:
                            for a in anchors:
                                href = a.get("href", "").strip()
                                if href and href != "#":
                                    link_type = classify_link(label)
                                    data.important_links.append({
                                        "label": label,
                                        "url": href,
                                        "link_type": link_type,
                                    })
                        # Also check the label cell for links
                        label_anchors = label_cell.find_all("a", href=True)
                        for a in label_anchors:
                            href = a.get("href", "").strip()
                            if href and href != "#":
                                link_type = classify_link(label)
                                data.important_links.append({
                                    "label": label,
                                    "url": href,
                                    "link_type": link_type,
                                })

                    # Official website row (last row usually)
                    if re.search(r'official\s*website', label, re.I):
                        anchors = value_cell.find_all("a", href=True)
                        for a in anchors:
                            href = a.get("href", "").strip()
                            if href and href != "#":
                                data.official_website_url = href
                                data.important_links.append({
                                    "label": clean(a.get_text()) or "Official Website",
                                    "url": href,
                                    "link_type": "official_website",
                                })

        # Deduplicate links by URL
        seen = set()
        unique = []
        for link in data.important_links:
            url = link.get("url", "")
            if url not in seen:
                seen.add(url)
                unique.append(link)
        data.important_links = unique

    def _extract_downloads(self, soup: BeautifulSoup, data: DetailData) -> None:
        """Extract downloadable assets (PDFs, docs) from all anchors on the page."""
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            if not href or href == "#":
                continue
            text = clean(a.get_text())

            if re.search(r'\.(pdf|doc|docx|xls|xlsx)(\?.*)?$', href, re.I):
                label = text or "Download"
                if re.search(r'syllabus', text, re.I):
                    label = label or "Syllabus PDF"
                elif re.search(r'answer\s*key', text, re.I):
                    label = label or "Answer Key"
                elif re.search(r'notif|advt', text, re.I):
                    label = label or "Notification PDF"
                data.download_links.append({"label": label, "url": href})

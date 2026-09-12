"""Extract (title, url, date) rows from the sources' listing pages."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from classify import classify_title
from textutil import clean, strip_brand, to_iso
from urls import is_source_host

_JUNK_PATH_RE = re.compile(
    r"/search-jobs/|/jobs-in-[a-z]|/[a-z0-9-]+-government-jobs/?$|/government-jobs/?$|"
    r"/(?:latestjob|result|admitcard|syllabus|answerkey|answer-key|admission|boardall|contactus|"
    r"search|videozone|archive|top10|page|tag|category|author|feed|about|privacy|disclaimer|sitemap)(?:\.php|/|$)",
    re.I,
)
_HEADER_TITLES = {"post name", "latest jobs", "results", "admit card", "#", "", "new", "view more", "more"}


def is_junk_listing_url(url: str) -> bool:
    parsed = urlparse(url)
    host, path = parsed.netloc.lower(), parsed.path
    if _JUNK_PATH_RE.search(path):
        return True
    if host.endswith("sarkariexam.com") and "/category/" in path:
        return True
    if host.endswith("freejobalert.com") and "/articles/" not in path:
        return True
    if path in ("", "/"):
        return True
    return False


def _row(title: str, href: str, date_text: str, source_base: str, hint: str) -> dict | None:
    title = strip_brand(title)
    if len(title) < 10 or title.lower() in _HEADER_TITLES or not href:
        return None
    url = urljoin(source_base, href.strip())
    if not url.startswith("http"):
        return None
    host = urlparse(url).netloc.lower()
    if urlparse(source_base).netloc.lower() != host and not is_source_host(url):
        return None
    if is_junk_listing_url(url):
        return None
    kind = classify_title(title, hint=hint)
    if not kind:
        return None
    return {"title": title, "detail_url": url, "kind": kind, "date": to_iso(date_text) or ""}


def parse_listing(soup: BeautifulSoup, hint: str, source_base: str) -> list[dict]:
    """Rows from table layouts (sarkariresult), list layouts (freejobalert & co) or bare anchors."""
    rows: list[dict] = []
    seen: set[str] = set()

    def add(r: dict | None) -> None:
        if r and r["detail_url"] not in seen:
            seen.add(r["detail_url"])
            rows.append(r)

    trs = (soup.select("#post-list table tr") or soup.select(".TableLi table tr")
           or soup.select("div.latestnews table tr") or soup.select("article table tr")
           or soup.select(".entry-content table tr") or soup.select("table tr"))
    for tr in trs:
        tds = tr.find_all("td")
        if not tds:
            continue
        a = None
        for td in tds:
            a = td.find("a", href=True)
            if a:
                break
        if not a:
            continue
        text = clean(tr.get_text(" "))
        m = re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", text)
        add(_row(clean(a.get_text(" ")), a["href"], m.group(0) if m else "", source_base, hint))

    if len(rows) <= 3:
        for li in (soup.select(".entry-content li") or soup.select(".post-content li") or soup.select("article li")
                   or soup.select(".td-post-content li") or soup.select("main li") or soup.select("li")):
            a = li.find("a", href=True)
            if not a:
                continue
            text = clean(li.get_text(" "))
            m = re.search(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{4}", text)
            add(_row(clean(a.get_text(" ")), a["href"], m.group(0) if m else "", source_base, hint))
            if len(rows) >= 200:
                break

    if len(rows) <= 3:
        for a in soup.find_all("a", href=True):
            add(_row(clean(a.get_text(" ")), a["href"], "", source_base, hint))
            if len(rows) >= 200:
                break
    return rows

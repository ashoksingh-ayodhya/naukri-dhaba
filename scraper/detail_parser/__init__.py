"""
Detail page parser package for Naukri Dhaba.

Provides parse_detail_page() as a drop-in replacement for the old parse_detail().
Dispatches to source-specific parsers and returns a DetailData object.
"""

from scraper.detail_parser.models import DetailData
from scraper.detail_parser.sarkariresult import SarkariResultParser
from scraper.detail_parser.freejobalert import FreeJobAlertParser
from scraper.detail_parser.rojgarresult import RojgarResultParser
from scraper.detail_parser.sarkariexam import SarkariExamParser

from urllib.parse import urlparse

_PARSER_MAP = {
    "sarkariresult": SarkariResultParser,
    "freejobalert": FreeJobAlertParser,
    "rojgarresult": RojgarResultParser,
    "sarkariexam": SarkariExamParser,
}


def _infer_source(url: str) -> str:
    """Guess source name from a URL's hostname."""
    if not url:
        return "sarkariresult"
    host = urlparse(url).netloc.lower()
    for name in _PARSER_MAP:
        if name in host:
            return name
    return "sarkariresult"


def parse_detail_page(soup, item: dict, source_name: str = "") -> DetailData:
    """Parse a detail page and return a DetailData object.

    Args:
        soup: BeautifulSoup of the detail page (can be None).
        item: Dict from the listing parser (title, dept, detail_url, etc.).
        source_name: Source identifier (e.g. "sarkariresult"). Auto-detected if empty.

    Returns:
        DetailData with all extracted fields.
    """
    if not source_name:
        source_name = item.get("source", "") or _infer_source(item.get("detail_url", ""))

    parser_cls = _PARSER_MAP.get(source_name, SarkariResultParser)
    parser = parser_cls()
    return parser.parse(soup, item, source_name)


__all__ = ["parse_detail_page", "DetailData"]

"""Regression tests for the scraper. Run: python -m unittest discover -s scraper/tests -v"""

from __future__ import annotations

import re
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from bs4 import BeautifulSoup  # noqa: E402

from classify import classify_title  # noqa: E402
from content_writer import write_body, write_description  # noqa: E402
from detail_parser import parse_detail_page  # noqa: E402
from detail_parser.link_resolver import resolve_links  # noqa: E402
from listing import parse_listing  # noqa: E402
from mdx_generator import detail_to_raw, normalize_frontmatter, parse_mdx, render_mdx  # noqa: E402
from textutil import find_dates, normalize_fee, strip_brand, to_iso  # noqa: E402
from urls import clean_link_url  # noqa: E402
from validate_content import validate_frontmatter  # noqa: E402

FIXTURES = HERE / "fixtures"


class ClassifyTests(unittest.TestCase):
    CASES = {
        "UPSC CDS II Online Form 2026 for 451 Post Date Extended": "job",
        "UPPSC APO Mains Admit Card 2026 for 182 Post": "admit",
        "SSC CGL 2025 Final Result": "result",
        "UPSC ISS Answer Key 2026 for 44 Post": "answer-key",
        "UP Police Constable Result 2026 for 32679 Post": "result",
        "Railway RRB NTPC Graduate Level CBT II Exam City Details 2026 | CEN 06/2025": "admit",
        "SSC GD Constable 2026 Exam Date": "admit",
        "RRB Group D Syllabus 2026": "syllabus",
        "Coast Guard Navik GD 02/2026 Batch": "job",
        "Bank of India Credit Officer Admit Card 2026": "admit",
        "UPSSSC PET 2025 Score Card": "result",
        "Top Online Form": None,
        "Latest": None,
        "52433": None,
    }

    def test_titles(self):
        for title, kind in self.CASES.items():
            self.assertEqual(classify_title(title), kind, title)


class TextTests(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(to_iso("27 July 2026"), "2026-07-27")
        self.assertEqual(to_iso("May 14, 2026"), "2026-05-14")
        self.assertEqual(to_iso("06 May 2023 | 11:30 PM"), "2023-05-06")
        self.assertEqual([d.isoformat() for d in find_dates("30/11/2025 to 09/12/2025")], ["2025-11-30", "2025-12-09"])
        self.assertIsNone(to_iso("As per Schedule"))

    def test_fee(self):
        self.assertEqual(normalize_fee("Rs. 500/-"), "500")
        self.assertEqual(normalize_fee("Nil"), "No Fee")
        self.assertIsNone(normalize_fee("Click Here"))

    def test_brand(self):
        self.assertNotIn("Sarkari", strip_brand("Notification by Sarkari Result . Visit sarkariresult.com"))


class UrlTests(unittest.TestCase):
    def test_policy(self):
        base = "https://www.sarkariresult.com/upsssc/x/"
        self.assertIsNone(clean_link_url("https://www.Naukri Dhaba/upload/Naukri Dhaba_UPSSSC.pdf"))
        self.assertIsNone(clean_link_url("https://www.sarkariresult.com/upload/x.pdf"))
        self.assertIsNone(clean_link_url("blob:https://rrbpryj.gov.in/abc"))
        self.assertIsNone(clean_link_url("https://tinyurl.com/x"))
        self.assertIsNone(clean_link_url("https://rrbmumbai.gov.in/x.pdfhttps://doc.sarkariresult.in/y.pdf"))
        self.assertIsNone(clean_link_url("https://www.instagram.com/x"))
        self.assertIsNone(clean_link_url("/AllNotifications.aspx"))
        self.assertEqual(clean_link_url("/AllNotifications.aspx", "https://upsssc.gov.in/a/"), "https://upsssc.gov.in/AllNotifications.aspx")
        self.assertEqual(clean_link_url("https://www.sarkariresult.com/go?url=https://ssc.gov.in/apply", base), "https://ssc.gov.in/apply")


class NormaliseTests(unittest.TestCase):
    RAW = {
        "title": "UPSSSC UP Vidhan Bhawan Guard / Fireman Online Form 2026 | Sarkari Result",
        "slug": "upsssc-up-vidhan-bhawan-guard-fireman-online-form-2026",
        "type": "job", "dept": "UPSSSC",
        "organization": "Age Relaxation Extra as per UPSSSC UP Advertisement No.-09-Exam/2026, UP Vidhan Bhavan Guard",
        "advertisementNo": "09-Exam/2026 |",
        "totalPosts": "170 Post",
        "qualification": "Click Here",
        "qualificationItems": ["General / OBC / EWS : 25/-", "SC / ST : 25/-", "Bachelor Degree in Any Stream"],
        "fees": {"General / OBC / EWS": "25/-", "SC / ST": "25/-", "First": "In this, the candidate will have to login PET 2025",
                 "After login, the complete information of the candidate": "Rs.25/- will have to be paid."},
        "dates": {"Application Begin": "09/06/2026", "Last Date for Registration": "29/06/2026",
                  "Fee Payment Last Date": "29/06/2026", "Correction Last Date": "06/07/2026", "Exam Date": "As per Schedule"},
        "notificationUrl": "https://www.Naukri Dhaba/upload/Naukri Dhaba_UPSSSC_09Exam_2026_Notification.pdf",
        "applyUrl": "https://upsssc.gov.in//AllNotifications.aspx",
        "officialWebsite": "https://upsssc.gov.in/",
        "importantLinks": [
            {"label": "Apply Online", "url": "https://upsssc.gov.in//AllNotifications.aspx", "link_type": "apply"},
            {"label": "Download SarkariResult App", "url": "https://play.google.com/x", "link_type": "other"},
            {"label": "Follow SarkariExam on Instagram", "url": "https://www.instagram.com/Naukri Dhaba.cm_", "link_type": "other"},
        ],
        "howToApply": ["Go to the official website of UPSSSC or use the direct apply link on this page at Naukri Dhaba.",
                       "Pay the application fee online via Debit Card, Credit Card, Net Banking, or UPI.",
                       "Candidates read the full notification before apply the recruitment application form.",
                       "Take a print out of final submitted form.",
                       "You Can Check other Naukri Dhaba Notification Here – Check Now."],
        "sourceUrl": "https://www.sarkariresult.com/upsssc/upsssc-vidhan-09-exam-2026/", "source": "sarkariresult",
        "publishedAt": "2026-05-29", "updatedAt": "06:32 PM",
    }

    def test_normalise(self):
        fm = normalize_frontmatter(self.RAW, keep_category="ssc")
        self.assertIsNotNone(fm)
        self.assertEqual(fm["title"], "UPSSSC UP Vidhan Bhawan Guard / Fireman Online Form 2026")
        self.assertEqual(fm["type"], "job")
        self.assertEqual(fm["organization"], "Uttar Pradesh Subordinate Services Selection Commission (UPSSSC)")
        self.assertEqual(fm["advertisementNo"], "09-Exam/2026")
        self.assertEqual(fm["totalPosts"], "170")
        self.assertEqual(fm["lastDate"], "29/06/2026")
        self.assertEqual(fm["applicationBegin"], "09/06/2026")
        self.assertEqual(fm["qualification"], "Bachelor Degree in Any Stream")
        self.assertEqual(fm["qualificationItems"], ["Bachelor Degree in Any Stream"])
        self.assertEqual(set(fm["fees"]), {"General / OBC / EWS", "SC / ST"})
        self.assertEqual(fm["feeGeneral"], "25")
        self.assertNotIn("notificationUrl", fm)
        self.assertEqual([l["label"] for l in fm["importantLinks"]], ["Apply Online", "Official Website"])
        self.assertEqual(len(fm["howToApply"]), 2)
        self.assertNotIn("updatedAt", fm)
        self.assertNotIn("examDate", fm)
        self.assertTrue(40 <= len(fm["shortDescription"]) <= 160)
        body = write_body(fm)
        self.assertNotIn("Sarkari", body)
        self.assertNotIn("2026 recruitment 2026", body)
        errs = validate_frontmatter(fm, body, Path("content/jobs/ssc") / f"{fm['slug']}.mdx")
        self.assertEqual(errs, [])
        text = render_mdx(fm, body)
        fm2, body2 = parse_mdx(text)
        self.assertEqual(fm2["lastDate"], "29/06/2026")
        self.assertEqual(fm2["publishedAt"], "2026-05-29")
        self.assertIsInstance(fm2["ageMin"] if "ageMin" in fm2 else 1, int)

    def test_rejects_junk(self):
        self.assertIsNone(normalize_frontmatter({"title": "", "slug": "latest", "type": "job"}))
        self.assertIsNone(normalize_frontmatter({"title": "Top Online Form", "slug": "top-online-form", "type": "job"}))
        self.assertIsNone(normalize_frontmatter({"title": "52433", "slug": "52433", "type": "job"}))

    def test_reclassifies_by_title(self):
        fm = normalize_frontmatter({"title": "UPPSC APO Mains Admit Card 2026 for 182 Post", "slug": "x-y-z-admit",
                                    "type": "job", "publishedAt": "2026-03-01"}, keep_category="state-psc")
        self.assertEqual(fm["type"], "admit")
        self.assertIn("released the UPPSC APO Mains Admit Card 2026", write_description(fm))
        self.assertNotIn("apply", write_description(fm).lower())


class ParserTests(unittest.TestCase):
    def test_sarkariresult_detail(self):
        html = (FIXTURES / "sarkariresult_detail.html").read_text(encoding="utf-8")
        item = {"title": "Upsssc Junior Assistant 07 2026", "detail_url": "https://www.sarkariresult.com/upsssc/junior-assistant-07-2026/",
                "page_type": "job", "_rough_title": True}
        detail = parse_detail_page(BeautifulSoup(html, "lxml"), item, source_name="sarkariresult")
        resolve_links(detail)
        fm = normalize_frontmatter(detail_to_raw(detail, "job"), base_url=item["detail_url"], scraped_at="2026-09-12T00:00:00")
        self.assertEqual(fm["title"], "UPSSSC Junior Assistant Online Form 2026")
        self.assertEqual(fm["slug"], "upsssc-junior-assistant-online-form-2026")
        self.assertEqual(fm["organization"], "Uttar Pradesh Subordinate Services Selection Commission (UPSSSC)")
        self.assertEqual(fm["advertisementNo"], "07-Exam/2026")
        self.assertEqual(fm["totalPosts"], "3000")
        self.assertEqual(fm["lastDate"], "30/09/2026")
        self.assertEqual(fm["applicationBegin"], "10/09/2026")
        self.assertEqual(fm["publishedAt"], "2026-09-05")
        self.assertEqual(fm["ageMin"], 18)
        self.assertEqual(fm["ageMax"], 40)
        self.assertEqual(fm["ageReferenceDate"], "01/07/2026")
        self.assertTrue(fm["qualification"].startswith("Bachelor Degree"))
        self.assertEqual(fm["feeGeneral"], "25")
        self.assertEqual(set(fm["fees"]), {"General / OBC / EWS", "SC / ST", "PH (Dviyang)"})
        labels = [l["label"] for l in fm["importantLinks"]]
        self.assertIn("Apply Online", labels)
        self.assertIn("Official Website", labels)
        self.assertNotIn("Download Notification", labels)
        self.assertFalse(any(re.search(r"\bApp\b|Channel", l) for l in labels))
        self.assertEqual(fm["applyUrl"], "https://upsssc.gov.in/AllNotifications.aspx")
        self.assertEqual(len(fm["howToApply"]), 3)
        self.assertEqual(validate_frontmatter(fm, write_body(fm), Path("content/jobs/ssc") / f"{fm['slug']}.mdx"), [])

    def test_listings(self):
        html = (FIXTURES / "sarkariresult_listing.html").read_text(encoding="utf-8")
        rows = parse_listing(BeautifulSoup(html, "lxml"), "job", "https://www.sarkariresult.com")
        kinds = {r["title"]: r["kind"] for r in rows}
        self.assertEqual(kinds["Railway Group D Recruitment 2026"], "job")
        self.assertEqual(kinds["UPPSC APO Mains Admit Card 2026 for 182 Post"], "admit")
        self.assertNotIn("Latest Jobs", kinds)
        self.assertEqual(rows[0]["date"], "2026-09-09")
        html = (FIXTURES / "freejobalert_listing.html").read_text(encoding="utf-8")
        rows = parse_listing(BeautifulSoup(html, "lxml"), "job", "https://www.freejobalert.com")
        self.assertEqual(len(rows), 2)
        self.assertTrue(all("/articles/" in r["detail_url"] for r in rows))


class _Handler(BaseHTTPRequestHandler):
    pages: dict[str, bytes] = {}

    def do_GET(self):  # noqa: N802
        body = self.pages.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # noqa: D102
        pass


class EndToEndTests(unittest.TestCase):
    """Listing → detail → MDX against a local HTTP server, using the real orchestrator function."""

    def test_write_post(self):
        import sarkari_scraper as sc

        _Handler.pages = {
            "/latestjob.php": (FIXTURES / "sarkariresult_listing.html").read_bytes(),
            "/upsssc/junior-assistant-07-2026/": (FIXTURES / "sarkariresult_detail.html").read_bytes(),
        }
        srv = HTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{srv.server_port}"
        try:
            soup = BeautifulSoup(_Handler.pages["/latestjob.php"], "lxml")
            rows = parse_listing(soup, "job", base)
            row = next(r for r in rows if "junior-assistant" in r["detail_url"])
            row["source"] = "sarkariresult"
            with tempfile.TemporaryDirectory() as tmp:
                status, path = sc.write_post(row, Path(tmp), dry_run=False)
                self.assertEqual(status, "written")
                self.assertTrue(path.exists())
                self.assertEqual(path.relative_to(tmp).as_posix(), "jobs/ssc/upsssc-junior-assistant-online-form-2026.mdx")
                fm, body = parse_mdx(path.read_text(encoding="utf-8"))
                self.assertEqual(fm["lastDate"], "30/09/2026")
                self.assertNotIn("sarkariresult", body.lower())
                status2, _ = sc.write_post(row, Path(tmp), dry_run=False)
                self.assertEqual(status2, "duplicate")
                gone = dict(row, detail_url=f"{base}/missing/", title="Some Missing Post Online Form 2026")
                self.assertEqual(sc.write_post(gone, Path(tmp), dry_run=False)[0], "gone")
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()

"""Shared site configuration for static generation scripts."""

import os

SITE_NAME = "Naukri Dhaba"
SITE_URL = os.getenv("NAUKRI_DHABA_SITE_URL", "https://naukridhaba.in").rstrip("/")

# Primary source (kept for backward-compat)
SOURCE_BASE_URL = "https://www.sarkariresult.com"

# All scraping sources: name, base URL, listing URLs per content type.
# "primary": True  → pages go live immediately after validation.
# "primary": False → pages land in staging/ and require manual promotion.
SOURCES = [
    # SarkariResult is the PRIMARY source — always scraped first.
    # Other sources are FALLBACKS — only used to fill gaps when
    # sarkariresult is down or missing a listing.
    {
        "name": "sarkariresult",
        "base": "https://www.sarkariresult.com",
        "primary": True,
        "urls": {
            "job":    "https://www.sarkariresult.com/latestjob.php",
            "result": "https://www.sarkariresult.com/result.php",
            "admit":  "https://www.sarkariresult.com/admitcard.php",
        },
    },
    {
        "name": "freejobalert",
        "base": "https://www.freejobalert.com",
        "primary": False,
        "urls": {
            "job":    "https://www.freejobalert.com/government-jobs/",
            "result": "https://www.freejobalert.com/sarkariresult/",
            "admit":  "https://www.freejobalert.com/admit-card/",
        },
    },
    {
        "name": "rojgarresult",
        "base": "https://www.rojgarresult.com",
        "primary": False,
        "urls": {
            "job":    "https://www.rojgarresult.com/recruitments/",
            "result": "https://www.rojgarresult.com/latest-result/",
            "admit":  "https://www.rojgarresult.com/admit-card/",
        },
    },
    {
        "name": "sarkariexam",
        "base": "https://www.sarkariexam.com",
        "primary": False,
        "urls": {
            "job":    "https://www.sarkariexam.com/category/jobs",
            "result": "https://www.sarkariexam.com/exam-result",
            "admit":  "https://www.sarkariexam.com/category/admit-card/",
        },
    },
]

# All source domains — used to filter/drop source-internal links
SOURCE_HOSTS = {
    "sarkariresult.com",
    "www.sarkariresult.com",
    "sarkariresults.com",
    "www.sarkariresults.com",
    # .org.in variants (same network, different TLD)
    "sarkariresult.org.in",
    "www.sarkariresult.org.in",
    "sarkariresults.org.in",
    "www.sarkariresults.org.in",
    # Document / CDN subdomains used by sarkariresult for PDF uploads
    "doc.sarkariresult.com",
    "doc.sarkariresults.com",
    "doc.sarkariresult.org.in",
    "doc.sarkariresults.org.in",
    "freejobalert.com",
    "www.freejobalert.com",
    "rojgarresult.com",
    "www.rojgarresult.com",
    "sarkariexam.com",
    "www.sarkariexam.com",
}

# Staging directory for secondary source content (not served live)
STAGING_DIR = "staging"
REDIRECT_PATH = "/go.html"
PRETTY_ROUTE_MAP = {
    "index.html": "/",
    "latest-jobs.html": "/latest-jobs.html",
    "results.html": "/results.html",
    "admit-cards.html": "/admit-cards.html",
    "resources.html": "/resources.html",
    "previous-papers.html": "/previous-papers.html",
    "eligibility-calculator.html": "/eligibility-calculator.html",
    "study-planner.html": "/study-planner.html",
}

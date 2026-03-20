"""Shared site configuration for static generation scripts."""

import os

SITE_NAME = "Naukri Dhaba"
SITE_URL = os.getenv("NAUKRI_DHABA_SITE_URL", "https://naukridhaba.in").rstrip("/")

# Primary source (kept for backward-compat)
SOURCE_BASE_URL = "https://www.sarkariresult.com"

# All scraping sources: name, base URL, listing URLs per content type
SOURCES = [
    {
        "name": "sarkariresult",
        "base": "https://www.sarkariresult.com",
        "urls": {
            "job":    "https://www.sarkariresult.com/latestjob.php",
            "result": "https://www.sarkariresult.com/result.php",
            "admit":  "https://www.sarkariresult.com/admitcard.php",
        },
    },
]

# All source domains — used to filter/drop source-internal links
SOURCE_HOSTS = {
    "sarkariresult.com",
    "www.sarkariresult.com",
    "sarkariresults.com",
    "www.sarkariresults.com",
}
REDIRECT_PATH = "/go.html"
PRETTY_ROUTE_MAP = {
    "index.html": "/",
    "latest-jobs.html": "/latest-jobs",
    "results.html": "/results",
    "admit-cards.html": "/admit-cards",
    "resources.html": "/resources",
    "previous-papers.html": "/previous-papers",
    "eligibility-calculator.html": "/eligibility-calculator",
    "study-planner.html": "/study-planner",
}

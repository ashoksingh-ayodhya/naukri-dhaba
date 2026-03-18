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
    {
        "name": "freejobalert",
        "base": "https://www.freejobalert.com",
        "urls": {
            "job":    "https://www.freejobalert.com/latest-govt-jobs/",
            "result": "https://www.freejobalert.com/sarkari-result/",
            "admit":  "https://www.freejobalert.com/admit-card/",
        },
    },
    {
        "name": "rojgarresult",
        "base": "https://www.rojgarresult.com",
        "urls": {
            "job":    "https://www.rojgarresult.com/latest-jobs/",
            "result": "https://www.rojgarresult.com/result/",
            "admit":  "https://www.rojgarresult.com/admit-card/",
        },
    },
    {
        "name": "sarkariexam",
        "base": "https://www.sarkariexam.com",
        "urls": {
            "job":    "https://www.sarkariexam.com/govt-jobs/",
            "result": "https://www.sarkariexam.com/results/",
            "admit":  "https://www.sarkariexam.com/admit-card/",
        },
    },
]

# All source domains — used to filter/drop source-internal links
SOURCE_HOSTS = {
    "sarkariresult.com",
    "www.sarkariresult.com",
    "sarkariresults.com",
    "www.sarkariresults.com",
    "freejobalert.com",
    "www.freejobalert.com",
    "rojgarresult.com",
    "www.rojgarresult.com",
    "sarkariexam.com",
    "www.sarkariexam.com",
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

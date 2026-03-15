"""Shared site configuration for static generation scripts."""

import os

SITE_NAME = "Naukri Dhaba"
SITE_URL = os.getenv("NAUKRI_DHABA_SITE_URL", "https://naukridhaba.in").rstrip("/")
SOURCE_BASE_URL = "https://www.sarkariresult.com"
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

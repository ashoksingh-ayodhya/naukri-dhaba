"""Scraper configuration — mirrors config/site.ts for the Python scraper."""

import os
from pathlib import Path

SITE_NAME = "Naukri Dhaba"
SITE_URL = os.getenv("NAUKRI_DHABA_SITE_URL", "https://naukridhaba.in").rstrip("/")

SOURCE_BASE_URL = "https://www.sarkariresult.com"

SOURCES = [
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

SOURCE_HOSTS = {
    "sarkariresult.com",
    "www.sarkariresult.com",
    "sarkariresults.com",
    "www.sarkariresults.com",
    "sarkariresult.org.in",
    "www.sarkariresult.org.in",
    "sarkariresults.org.in",
    "www.sarkariresults.org.in",
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

STAGING_DIR = "staging"
REDIRECT_PATH = "/go/"

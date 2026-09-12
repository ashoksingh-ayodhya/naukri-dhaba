"""Scraper sources. Each source lists one listing URL per content kind."""

import os

SITE_NAME = "Naukri Dhaba"
SITE_URL = os.getenv("NAUKRI_DHABA_SITE_URL", "https://naukridhaba.in").rstrip("/")

SOURCES = [
    {
        "name": "sarkariresult",
        "base": "https://www.sarkariresult.com",
        "urls": {
            "job": "https://www.sarkariresult.com/latestjob.php",
            "result": "https://www.sarkariresult.com/result.php",
            "admit": "https://www.sarkariresult.com/admitcard.php",
            "answer-key": "https://www.sarkariresult.com/answer-key.php",
            "syllabus": "https://www.sarkariresult.com/syllabus.php",
        },
    },
    {
        "name": "freejobalert",
        "base": "https://www.freejobalert.com",
        "urls": {
            "job": "https://www.freejobalert.com/government-jobs/",
            "result": "https://www.freejobalert.com/sarkariresult/",
            "admit": "https://www.freejobalert.com/admit-card/",
            "answer-key": "https://www.freejobalert.com/answer-key/",
            "syllabus": "https://www.freejobalert.com/syllabus/",
        },
    },
    {
        "name": "rojgarresult",
        "base": "https://www.rojgarresult.com",
        "urls": {
            "job": "https://www.rojgarresult.com/recruitments/",
            "result": "https://www.rojgarresult.com/latest-result/",
            "admit": "https://www.rojgarresult.com/admit-card/",
        },
    },
    {
        "name": "sarkariexam",
        "base": "https://www.sarkariexam.com",
        "urls": {
            "job": "https://www.sarkariexam.com/category/jobs",
            "result": "https://www.sarkariexam.com/exam-result",
            "admit": "https://www.sarkariexam.com/category/admit-card/",
            "answer-key": "https://www.sarkariexam.com/category/answer-key/",
            "syllabus": "https://www.sarkariexam.com/category/syllabus/",
        },
    },
]

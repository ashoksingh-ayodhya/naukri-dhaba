#!/usr/bin/env python3
"""
============================================================
NAUKRI DHABA - JOB POSTER
File: scraper/job_poster.py
============================================================

Scrapes sarkariresult.com and posts new job/result/admit-card
pages to Naukri Dhaba automatically.

SCHEDULE (via cron - every 5 minutes):
  */5 * * * * /usr/bin/python3 /path/to/scraper/job_poster.py >> /path/to/scraper/logs/job_poster.log 2>&1

SETUP CRON (run once):
  python3 scraper/job_poster.py --setup-cron

MANUAL RUN:
  python3 scraper/job_poster.py

DAEMON MODE (runs every 5 min in foreground, no cron needed):
  python3 scraper/job_poster.py --daemon

LOGS:
  scraper/logs/job_poster.log

============================================================
"""

import sys
import os
import time
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRAPER_DIR = Path(__file__).resolve().parent
LOG_FILE = SCRAPER_DIR / "logs" / "job_poster.log"
SCRAPER_SCRIPT = SCRAPER_DIR / "sarkari_scraper.py"
INTERVAL_SECONDS = 300  # 5 minutes

# ─── Logging ───────────────────────────────────────────────
SCRAPER_DIR.joinpath("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [JOB-POSTER] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("job_poster")


def run_scraper():
    """Run the main scraper once and return True on success."""
    log.info("Starting scrape run...")
    try:
        result = subprocess.run(
            [sys.executable, str(SCRAPER_SCRIPT)],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=240,  # 4 min timeout (safe within 5-min window)
        )
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                log.info(line)
        if result.returncode != 0:
            log.error(f"Scraper exited with code {result.returncode}")
            if result.stderr:
                for line in result.stderr.strip().splitlines()[-10:]:
                    log.error(line)
            return False
        log.info("Scrape run completed successfully.")
        return True
    except subprocess.TimeoutExpired:
        log.error("Scraper timed out after 4 minutes.")
        return False
    except Exception as e:
        log.error(f"Scraper error: {e}")
        return False


def setup_cron():
    """Install a cron job to run job_poster.py every 5 minutes."""
    script_path = Path(__file__).resolve()
    log_path = LOG_FILE.resolve()
    cron_line = (
        f"*/5 * * * * {sys.executable} {script_path} >> {log_path} 2>&1"
    )

    # Read existing crontab
    try:
        existing = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True
        ).stdout
    except Exception:
        existing = ""

    if str(script_path) in existing:
        print("Cron job already installed:")
        for line in existing.splitlines():
            if str(script_path) in line:
                print(f"  {line}")
        return

    new_crontab = existing.rstrip("\n") + f"\n{cron_line}\n"
    proc = subprocess.run(
        ["crontab", "-"], input=new_crontab, capture_output=True, text=True
    )
    if proc.returncode == 0:
        print(f"Cron job installed:\n  {cron_line}")
    else:
        print(f"Failed to install cron job: {proc.stderr}")
        print(f"\nAdd this line manually to your crontab (crontab -e):\n  {cron_line}")


def remove_cron():
    """Remove the job_poster cron job."""
    script_path = str(Path(__file__).resolve())
    try:
        existing = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True
        ).stdout
    except Exception:
        print("No crontab found.")
        return

    new_lines = [l for l in existing.splitlines() if script_path not in l]
    new_crontab = "\n".join(new_lines) + "\n"
    subprocess.run(["crontab", "-"], input=new_crontab, capture_output=True)
    print("Cron job removed.")


def daemon_mode():
    """Run scraper every 5 minutes in foreground (no cron needed)."""
    log.info(f"Daemon started — running every {INTERVAL_SECONDS // 60} minutes. Ctrl+C to stop.")
    while True:
        start = time.time()
        run_scraper()
        elapsed = time.time() - start
        wait = max(0, INTERVAL_SECONDS - elapsed)
        log.info(f"Next run in {int(wait)} seconds...")
        try:
            time.sleep(wait)
        except KeyboardInterrupt:
            log.info("Daemon stopped.")
            break


def main():
    parser = argparse.ArgumentParser(
        description="Naukri Dhaba Job Poster — scrapes and posts new jobs every 5 minutes"
    )
    parser.add_argument(
        "--setup-cron", action="store_true",
        help="Install cron job to run every 5 minutes"
    )
    parser.add_argument(
        "--remove-cron", action="store_true",
        help="Remove the cron job"
    )
    parser.add_argument(
        "--daemon", action="store_true",
        help="Run continuously every 5 minutes (foreground, no cron)"
    )
    args = parser.parse_args()

    if args.setup_cron:
        setup_cron()
    elif args.remove_cron:
        remove_cron()
    elif args.daemon:
        daemon_mode()
    else:
        # Single manual run
        success = run_scraper()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

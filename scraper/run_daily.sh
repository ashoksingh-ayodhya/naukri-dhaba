#!/bin/bash
# ============================================================
# NAUKRI DHABA - DAILY RUN SCRIPT
# File: scraper/run_daily.sh
#
# Called by cron at 10:00 AM IST every day.
# Installs deps if missing, runs scraper, regenerates sitemap.
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE_DIR="$(dirname "$SCRIPT_DIR")"
LOG="$SCRIPT_DIR/logs/cron.log"
PYTHON="$(command -v python3 || command -v python)"

mkdir -p "$SCRIPT_DIR/logs"

echo "" >> "$LOG"
echo "======================================" >> "$LOG"
echo "RUN: $(TZ='Asia/Kolkata' date '+%Y-%m-%d %H:%M:%S IST')" >> "$LOG"
echo "======================================" >> "$LOG"

# ── Auto-install deps if not present ──────────────────────
$PYTHON -c "import requests, bs4" 2>/dev/null || {
  echo "Installing deps…" >> "$LOG"
  $PYTHON -m pip install -q requests beautifulsoup4 lxml >> "$LOG" 2>&1
}

# ── Run the scraper ────────────────────────────────────────
echo "Starting scraper…" >> "$LOG"
cd "$SITE_DIR"
$PYTHON "$SCRIPT_DIR/sarkari_scraper.py" >> "$LOG" 2>&1
STATUS=$?

if [ $STATUS -eq 0 ]; then
  echo "Scraper finished OK" >> "$LOG"
else
  echo "Scraper exited with code $STATUS" >> "$LOG"
fi

# ── Regenerate sitemap ─────────────────────────────────────
$PYTHON "$SITE_DIR/generate-sitemap.py" >> "$LOG" 2>&1
echo "Sitemap updated" >> "$LOG"
echo "DONE: $(TZ='Asia/Kolkata' date '+%H:%M:%S IST')" >> "$LOG"

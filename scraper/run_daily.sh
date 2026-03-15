#!/bin/bash
# ============================================================
# NAUKRI DHABA - DAILY SCRAPER RUNNER
# File: scraper/run_daily.sh
# ============================================================
# CRON SETUP (runs daily at 6 AM):
#   crontab -e
#   Add: 0 6 * * * /path/to/naukri-dhaba/scraper/run_daily.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$SCRIPT_DIR/logs/cron.log"
PYTHON=$(which python3 || which python)

mkdir -p "$SCRIPT_DIR/logs"

echo "=============================" >> "$LOG_FILE"
echo "Run: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "=============================" >> "$LOG_FILE"

# Install dependencies if needed
if ! $PYTHON -c "import requests" 2>/dev/null; then
    echo "Installing Python dependencies..." >> "$LOG_FILE"
    $PYTHON -m pip install -r "$SCRIPT_DIR/requirements.txt" >> "$LOG_FILE" 2>&1
fi

# Run scraper
echo "Starting scraper..." >> "$LOG_FILE"
cd "$SITE_DIR"
$PYTHON "$SCRIPT_DIR/sarkari_scraper.py" >> "$LOG_FILE" 2>&1

# Regenerate sitemap
echo "Regenerating sitemap..." >> "$LOG_FILE"
$PYTHON "$SITE_DIR/generate-sitemap.py" >> "$LOG_FILE" 2>&1

echo "Done: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

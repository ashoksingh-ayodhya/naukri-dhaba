#!/bin/bash
# ============================================================
# NAUKRI DHABA - CRON SETUP  (10:00 AM IST daily)
# File: scraper/setup_cron.sh
# ============================================================
#
# WHAT THIS DOES:
#   Installs a cron job that runs the scraper every day at
#   10:00 AM Indian Standard Time (IST = UTC+5:30 = 04:30 UTC).
#
# HOW TO RUN:
#   bash scraper/setup_cron.sh
#
# TO REMOVE THE CRON JOB LATER:
#   crontab -e   →  delete the "# NaukriDhaba" line
#
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="$(command -v python3 || command -v python)"
RUNNER="$SCRIPT_DIR/run_daily.sh"

# ── Verify Python ──────────────────────────────────────────
if [ -z "$PYTHON" ]; then
  echo "❌ Python 3 not found. Please install python3."
  exit 1
fi
echo "✅ Python: $PYTHON ($($PYTHON --version 2>&1))"

# ── Install Python dependencies ────────────────────────────
echo "Installing Python dependencies…"
$PYTHON -m pip install -q requests beautifulsoup4 lxml 2>&1 | tail -3

# ── Ensure run_daily.sh is executable ─────────────────────
chmod +x "$RUNNER"

# ── Create log directory ───────────────────────────────────
mkdir -p "$SCRIPT_DIR/logs"

# ── Build the cron entry ───────────────────────────────────
# 10:00 AM IST  =  04:30 UTC  (IST is UTC+5:30)
# Cron fields: minute  hour  day  month  weekday
CRON_TIME="30 4 * * *"
CRON_CMD="$CRON_TIME bash $RUNNER >> $SCRIPT_DIR/logs/cron.log 2>&1 # NaukriDhaba"

# ── Check if already installed ─────────────────────────────
if crontab -l 2>/dev/null | grep -q "NaukriDhaba"; then
  echo ""
  echo "⚠️  A Naukri Dhaba cron job already exists:"
  crontab -l 2>/dev/null | grep "NaukriDhaba"
  echo ""
  read -p "Replace it? (y/N): " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 0
  fi
  # Remove old entry
  ( crontab -l 2>/dev/null | grep -v "NaukriDhaba" ) | crontab -
fi

# ── Install the cron job ───────────────────────────────────
( crontab -l 2>/dev/null; echo "$CRON_CMD" ) | crontab -

echo ""
echo "✅ Cron job installed successfully!"
echo ""
echo "   Schedule : Every day at 10:00 AM IST (04:30 UTC)"
echo "   Command  : bash $RUNNER"
echo "   Log file : $SCRIPT_DIR/logs/cron.log"
echo ""
echo "Current crontab:"
crontab -l | grep "NaukriDhaba"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  To run the scraper manually right now:"
echo "    python3 $SCRIPT_DIR/sarkari_scraper.py"
echo ""
echo "  To view logs:"
echo "    tail -f $SCRIPT_DIR/logs/scraper.log"
echo ""
echo "  To remove the cron job:"
echo "    crontab -e   →  delete the NaukriDhaba line"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Naukri Dhaba — GitHub Actions Self-Hosted Runner Setup
# Run this on YOUR machine / VPS (not in the repo, on the server)
# ─────────────────────────────────────────────────────────────
set -e

REPO="ashoksingh-ayodhya/naukri-dhaba"
RUNNER_VERSION="2.323.0"
RUNNER_DIR="$HOME/actions-runner"

echo ""
echo "======================================================"
echo "  Naukri Dhaba — Self-Hosted Runner Setup"
echo "======================================================"
echo ""

# ── Step 1: Get registration token ───────────────────────────
echo "STEP 1: You need a registration token from GitHub."
echo ""
echo "  Open this URL in your browser:"
echo "  https://github.com/$REPO/settings/actions/runners/new"
echo ""
echo "  Select: Linux → x64"
echo "  Copy the token shown on that page (looks like: ABCDE...)"
echo ""
read -p "Paste your runner token here: " RUNNER_TOKEN

if [ -z "$RUNNER_TOKEN" ]; then
  echo "ERROR: Token cannot be empty."
  exit 1
fi

# ── Step 2: Install dependencies ─────────────────────────────
echo ""
echo "STEP 2: Installing dependencies..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv curl tar git

# ── Step 3: Download runner ───────────────────────────────────
echo ""
echo "STEP 3: Downloading GitHub Actions runner v$RUNNER_VERSION..."
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

curl -sSL -o runner.tar.gz \
  "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"

tar xzf runner.tar.gz
rm runner.tar.gz

echo "Runner downloaded."

# ── Step 4: Configure runner ──────────────────────────────────
echo ""
echo "STEP 4: Configuring runner for $REPO..."
./config.sh \
  --url "https://github.com/$REPO" \
  --token "$RUNNER_TOKEN" \
  --name "naukri-dhaba-runner" \
  --labels "self-hosted,Linux,x64" \
  --work "_work" \
  --unattended \
  --replace

# ── Step 5: Install as a system service ──────────────────────
echo ""
echo "STEP 5: Installing runner as a system service (runs 24/7)..."
sudo ./svc.sh install
sudo ./svc.sh start

echo ""
echo "======================================================"
echo "  SUCCESS! Runner is running."
echo ""
echo "  Check status:   sudo $RUNNER_DIR/svc.sh status"
echo "  Stop runner:    sudo $RUNNER_DIR/svc.sh stop"
echo "  Start runner:   sudo $RUNNER_DIR/svc.sh start"
echo ""
echo "  Verify on GitHub:"
echo "  https://github.com/$REPO/settings/actions/runners"
echo "  (You should see 'naukri-dhaba-runner' with green status)"
echo ""
echo "  The scraper will now run on YOUR IP every 5 minutes."
echo "======================================================"

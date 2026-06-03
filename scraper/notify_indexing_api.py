#!/usr/bin/env python3
"""
notify_indexing_api.py — Ping Google Indexing API for newly scraped URLs.

Usage:
    python notify_indexing_api.py --key-json "$GOOGLE_INDEXING_SA_KEY" \
                                   --urls-file new_urls.txt

Reads one URL per line from --urls-file, notifies Google in batches of 100.
Exits 0 always (failures are logged but don't break CI).
"""

import argparse
import json
import sys
import time

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-json", required=True, help="Service account JSON string")
    parser.add_argument("--urls-file", required=True, help="File with one URL per line")
    args = parser.parse_args()

    try:
        import google.auth.transport.requests
        from google.oauth2 import service_account
        import requests as req
    except ImportError:
        print("Installing google-auth + requests...", flush=True)
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "google-auth", "requests", "-q"], check=True)
        import google.auth.transport.requests
        from google.oauth2 import service_account
        import requests as req

    try:
        key_data = json.loads(args.key_json)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid service account JSON: {e}", flush=True)
        sys.exit(0)  # Don't fail CI

    try:
        with open(args.urls_file) as f:
            urls = [line.strip() for line in f if line.strip().startswith("http")]
    except FileNotFoundError:
        print(f"No URLs file found: {args.urls_file}")
        sys.exit(0)

    if not urls:
        print("No URLs to notify.")
        sys.exit(0)

    print(f"Notifying Google Indexing API for {len(urls)} URLs...", flush=True)

    creds = service_account.Credentials.from_service_account_info(
        key_data,
        scopes=["https://www.googleapis.com/auth/indexing"],
    )

    ok = 0
    fail = 0
    for i, url in enumerate(urls):
        try:
            authed = google.auth.transport.requests.Request()
            creds.refresh(authed)
            token = creds.token

            resp = req.post(
                "https://indexing.googleapis.com/v3/urlNotifications:publish",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"url": url, "type": "URL_UPDATED"},
                timeout=10,
            )
            if resp.status_code == 200:
                ok += 1
            else:
                fail += 1
                print(f"  WARN {resp.status_code}: {url} — {resp.text[:120]}", flush=True)
        except Exception as e:
            fail += 1
            print(f"  ERR: {url} — {e}", flush=True)

        # Rate limit: 200 req/day quota, batch with small delay
        if (i + 1) % 10 == 0:
            time.sleep(1)

    print(f"Indexing API done: {ok} notified, {fail} failed out of {len(urls)} URLs.", flush=True)

if __name__ == "__main__":
    main()

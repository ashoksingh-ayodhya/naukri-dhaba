#!/usr/bin/env python3
"""
Naukri Dhaba Monitor Agent
==========================
Runs daily via GitHub Actions.

Responsibilities:
  1. Count MDX content files (jobs, results, admit-cards, etc.)
  2. Compare with yesterday's count stored in agent/state.json
  3. Check if any content commits landed in the last 24 hours
  4. If NO refresh → create GitHub issue alert
  5. If count DECREASED → create GitHub issue alert (content deleted)
  6. Print open problem board items for the run log
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT   = Path(__file__).parent.parent
CONTENT_DIR = REPO_ROOT / "content"
STATE_FILE  = Path(__file__).parent / "state.json"
PROBLEMS_FILE = Path(__file__).parent / "problems.json"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO  = os.environ.get("GITHUB_REPOSITORY", "ashoksingh-ayodhya/naukri-dhaba")

CONTENT_TYPES = ["jobs", "results", "admit-cards", "answer-keys", "syllabus"]
FLAT_TYPES    = {"answer-keys", "syllabus"}   # no sub-category folders


# ── Helpers ────────────────────────────────────────────────────────────────────

def count_mdx() -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in CONTENT_TYPES:
        d = CONTENT_DIR / t
        if not d.exists():
            counts[t] = 0
        elif t in FLAT_TYPES:
            counts[t] = len(list(d.glob("*.mdx")))
        else:
            counts[t] = len(list(d.glob("**/*.mdx")))
    return counts


def recent_content_commits(hours: int = 24) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "log", f"--since={hours} hours ago", "--oneline", "--", "content/"],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=30,
        )
        return [l for l in result.stdout.strip().splitlines() if l]
    except Exception as exc:
        print(f"[monitor] git log failed: {exc}", file=sys.stderr)
        return []


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def create_github_issue(title: str, body: str) -> None:
    if not GITHUB_TOKEN:
        print("[monitor] No GITHUB_TOKEN — skipping issue creation.")
        return
    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "GH_TOKEN": GITHUB_TOKEN},
        )
        if result.returncode == 0:
            print(f"[monitor] Issue created: {result.stdout.strip()}")
        else:
            print(f"[monitor] Issue creation failed: {result.stderr.strip()}", file=sys.stderr)
    except Exception as exc:
        print(f"[monitor] Error creating issue: {exc}", file=sys.stderr)


def load_problems() -> list[dict]:
    if PROBLEMS_FILE.exists():
        try:
            return json.loads(PROBLEMS_FILE.read_text()).get("problems", [])
        except Exception:
            pass
    return []


def counts_table(counts: dict[str, int]) -> str:
    rows = "\n".join(f"| {t} | {n} |" for t, n in counts.items())
    total = sum(counts.values())
    return f"| Type | Count |\n|------|-------|\n{rows}\n| **Total** | **{total}** |"


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    now  = datetime.now()
    date = now.strftime("%Y-%m-%d")
    ts   = now.strftime("%Y-%m-%d %H:%M IST")

    print(f"[monitor] Starting at {ts}")

    # 1. Count current content
    counts  = count_mdx()
    total   = sum(counts.values())
    print(f"[monitor] Counts: {counts}  total={total}")

    # 2. Load previous state
    state    = load_state()
    prev     = state.get("counts", {})
    prev_tot = sum(prev.values()) if prev else None

    # 3. Check recent commits
    commits = recent_content_commits(24)
    print(f"[monitor] Content commits in last 24h: {len(commits)}")
    for c in commits[:5]:
        print(f"  {c}")

    # 4. Alerts
    alerts: list[tuple[str, str]] = []

    if not commits:
        body = f"""## ⚠️ No content refresh in the last 24 hours

**Checked at:** {ts}

**Current content:**
{counts_table(counts)}

No commit has touched `content/` in the last 24 hours. Possible causes:
- Scraper failed, was blocked (429/403/captcha), or GitHub Actions didn't run
- `seen_items.json` is preventing re-scrape of valid new jobs
- CF Worker proxy is down or rate-limited

**Immediate actions:**
1. Check the [Daily Scraper workflow](https://github.com/{GITHUB_REPO}/actions/workflows/daily-scraper.yml) for errors
2. Trigger a manual scraper run via workflow_dispatch
3. Review `scraper/logs/scraper.log` for block indicators

*— Naukri Dhaba Monitor Agent*"""
        alerts.append((f"⚠️ No content refresh in 24h — {now.strftime('%d %b %Y')}", body))

    if prev_tot is not None and total < prev_tot:
        diff = prev_tot - total
        body = f"""## 🚨 Content count DECREASED by {diff}

**Checked at:** {ts}

| | Count |
|--|--|
| Yesterday | {prev_tot} |
| Today | {total} |
| **Difference** | **-{diff}** |

**By type:**
{counts_table(counts)}

MDX files were deleted or lost. This could mean:
- A bad git reset or force-push wiped content files
- Scraper accidentally deleted files instead of adding them
- A branch merge conflict was resolved by discarding content

**Immediate action:** check `git log -- content/` and restore lost files.

*— Naukri Dhaba Monitor Agent*"""
        alerts.append((f"🚨 Content count dropped by {diff} — {now.strftime('%d %b %Y')}", body))

    for title, body in alerts:
        create_github_issue(title, body)

    if not alerts:
        print(f"[monitor] All good. Content is fresh. total={total}")

    # 5. Print open problem board
    problems = load_problems()
    open_p   = [p for p in problems if p.get("status") == "open"]
    print(f"\n[monitor] ── OPEN PROBLEMS ({len(open_p)}) ──")
    for p in open_p:
        print(f"  [{p['priority'].upper():8s}] {p['id']}: {p['title']}")

    # 6. Save state for next run
    save_state({"date": date, "counts": counts})
    print(f"\n[monitor] State saved. Done.")


if __name__ == "__main__":
    main()

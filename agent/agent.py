#!/usr/bin/env python3
"""
Naukri Dhaba — Autonomous Agent
================================
Runs daily via GitHub Actions.

Goals (in priority order):
  1. Fix branding contamination — remove "Sarkari Result" from all MDX files
  2. Audit content freshness — alert if no new content in 24h
  3. Audit content counts — alert if count drops
  4. Clear seen_items.json when content is stale — forces scraper to collect more
  5. Trigger scraper re-run by writing scraper/run-now
  6. Report all open problems from the board

The agent commits its own fixes and creates GitHub issues for anything
that needs human attention.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT     = Path(__file__).parent.parent
CONTENT_DIR   = REPO_ROOT / "content"
SCRAPER_DIR   = REPO_ROOT / "scraper"
STATE_FILE    = Path(__file__).parent / "state.json"
PROBLEMS_FILE = Path(__file__).parent / "problems.json"
SEEN_FILE     = SCRAPER_DIR / "seen_items.json"
RUN_NOW_FILE  = SCRAPER_DIR / "run-now"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO  = os.environ.get("GITHUB_REPOSITORY", "ashoksingh-ayodhya/naukri-dhaba")

CONTENT_TYPES = ["jobs", "results", "admit-cards", "answer-keys", "syllabus"]
FLAT_TYPES    = {"answer-keys", "syllabus"}

# Branding patterns to strip from MDX content
BRAND_PATTERNS = [
    (re.compile(r'(?i)sarkari\s*results?(?:\.(?:com|org|in))?'), "Naukri Dhaba"),
    (re.compile(r'(?i)www\.sarkariresults?\.(?:com|org|in)'),    "www.naukridhaba.in"),
    (re.compile(r'(?i)sarkariresult\.com'),                       "naukridhaba.in"),
    (re.compile(r'(?i)sarkariresults\.com'),                      "naukridhaba.in"),
    # Keep source URLs intact — only clean display text
]

ISSUES_CREATED: list[str] = []
FIXES_APPLIED:  list[str] = []


# ── Utilities ─────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(f"[agent] {msg}", flush=True)


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
        log(f"git log failed: {exc}")
        return []


def create_issue(title: str, body: str) -> str:
    if not GITHUB_TOKEN:
        log("No GITHUB_TOKEN — cannot create issue.")
        return ""
    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "GH_TOKEN": GITHUB_TOKEN},
        )
        url = result.stdout.strip()
        if result.returncode == 0:
            log(f"Issue created: {url}")
            ISSUES_CREATED.append(url)
            return url
        else:
            log(f"Issue creation failed: {result.stderr.strip()}")
    except Exception as exc:
        log(f"Error creating issue: {exc}")
    return ""


def git_commit(message: str, paths: list[str]) -> bool:
    try:
        subprocess.run(
            ["git", "config", "user.name", "Naukri Dhaba Agent"],
            cwd=REPO_ROOT, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "bot@naukridhaba.in"],
            cwd=REPO_ROOT, check=True, capture_output=True,
        )
        subprocess.run(["git", "add"] + paths, cwd=REPO_ROOT, check=True, capture_output=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=REPO_ROOT, capture_output=True,
        )
        if result.returncode == 0:
            log("Nothing to commit.")
            return False
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=REPO_ROOT, check=True, capture_output=True,
        )
        log(f"Committed: {message}")
        return True
    except subprocess.CalledProcessError as exc:
        log(f"Git commit failed: {exc}")
        return False


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


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


# ── Task 1: Fix branding contamination ────────────────────────────────────────

def fix_branding(dry_run: bool = False) -> int:
    """Scan all MDX files and remove 'Sarkari Result' mentions from YAML values and body text.

    Skips sourceUrl fields — we keep the original source URL for reference.
    Returns number of files fixed.
    """
    log("Task 1: Scanning for branding contamination...")

    fixed = 0
    mdx_files = list(CONTENT_DIR.rglob("*.mdx"))

    for fpath in mdx_files:
        original = fpath.read_text(encoding="utf-8")
        cleaned  = original

        # Split into frontmatter and body
        parts = cleaned.split("---", 2)
        if len(parts) < 3:
            # No proper frontmatter — clean whole file
            for pattern, replacement in BRAND_PATTERNS:
                cleaned = pattern.sub(replacement, cleaned)
        else:
            front = parts[1]
            body  = parts[2]

            # In frontmatter: only clean values that are NOT sourceUrl/source lines
            front_lines = front.split("\n")
            cleaned_front_lines = []
            for line in front_lines:
                # Preserve sourceUrl and source fields unchanged
                if re.match(r'\s*source(?:Url)?:', line, re.I):
                    cleaned_front_lines.append(line)
                    continue
                new_line = line
                for pattern, replacement in BRAND_PATTERNS:
                    new_line = pattern.sub(replacement, new_line)
                cleaned_front_lines.append(new_line)

            # Clean body text fully
            cleaned_body = body
            for pattern, replacement in BRAND_PATTERNS:
                cleaned_body = pattern.sub(replacement, cleaned_body)

            cleaned = "---" + "\n".join(cleaned_front_lines) + "---" + cleaned_body

        if cleaned != original:
            if not dry_run:
                fpath.write_text(cleaned, encoding="utf-8")
            fixed += 1

    log(f"Task 1: {'Would fix' if dry_run else 'Fixed'} {fixed}/{len(mdx_files)} files with branding contamination.")
    if fixed > 0:
        FIXES_APPLIED.append(f"Removed 'Sarkari Result' branding from {fixed} MDX files")
    return fixed


# ── Task 2: Audit content freshness + alert ───────────────────────────────────

def audit_freshness(counts: dict[str, int], prev_counts: dict[str, int]) -> None:
    """Check if scraper ran in last 24h. Alert if stale or if count dropped."""
    log("Task 2: Auditing content freshness...")

    total      = sum(counts.values())
    prev_total = sum(prev_counts.values()) if prev_counts else None
    commits    = recent_content_commits(24)

    log(f"  Content commits (24h): {len(commits)}")
    log(f"  Total MDX: {total}  (prev: {prev_total})")

    if not commits:
        body = f"""## ⚠️ No content refresh in the last 24 hours

**Detected at:** {datetime.now().strftime('%Y-%m-%d %H:%M IST')}

**Current content:**
{counts_table(counts)}

The scraper has not committed any new content in 24 hours. Possible causes:
- Scraper failed or was blocked (check [Daily Scraper logs](https://github.com/{GITHUB_REPO}/actions/workflows/daily-scraper.yml))
- `seen_items.json` is preventing re-scrape of valid new jobs
- CF Worker proxy is down

**The agent has cleared `seen_items.json` and touched `scraper/run-now` to force a re-run.**
Check the next scraper run to confirm new content is being collected.

*— Naukri Dhaba Agent*"""
        create_issue(f"⚠️ No content refresh in 24h — {datetime.now().strftime('%d %b %Y')}", body)

    if prev_total is not None and total < prev_total:
        diff = prev_total - total
        body = f"""## 🚨 Content count dropped by {diff}

**Detected at:** {datetime.now().strftime('%Y-%m-%d %H:%M IST')}

| | Count |
|--|--|
| Yesterday | {prev_total} |
| Today | {total} |
| **Drop** | **-{diff}** |

{counts_table(counts)}

MDX files were deleted. Check `git log -- content/` to find what was removed.

*— Naukri Dhaba Agent*"""
        create_issue(f"🚨 Content dropped by {diff} — {datetime.now().strftime('%d %b %Y')}", body)


# ── Task 3: Clear seen_items to unlock more scraping ─────────────────────────

def clear_seen_items_if_stale(commits: list[str]) -> bool:
    """If no new content in 24h, clear seen_items.json so scraper re-collects everything."""
    if commits:
        log("Task 3: Content is fresh — keeping seen_items.json.")
        return False

    if not SEEN_FILE.exists():
        log("Task 3: seen_items.json not found.")
        return False

    count = 0
    try:
        data = json.loads(SEEN_FILE.read_text())
        count = len(data) if isinstance(data, list) else len(data)
    except Exception:
        pass

    log(f"Task 3: Content stale — clearing seen_items.json ({count} entries). Scraper will re-collect everything.")
    SEEN_FILE.write_text("[]")
    FIXES_APPLIED.append(f"Cleared seen_items.json ({count} entries) to allow full re-scrape")
    return True


# ── Task 4: Trigger scraper re-run ───────────────────────────────────────────

def trigger_scraper_if_stale(commits: list[str]) -> bool:
    """Write scraper/run-now to trigger the daily-scraper workflow."""
    if commits:
        log("Task 4: Content is fresh — not triggering scraper.")
        return False

    ts = datetime.now().isoformat()
    RUN_NOW_FILE.write_text(f"Agent-triggered re-run at {ts}\n")
    log(f"Task 4: Wrote scraper/run-now — daily-scraper workflow will be triggered.")
    FIXES_APPLIED.append("Wrote scraper/run-now to trigger immediate scraper re-run")
    return True


# ── Task 5: Audit SEO issues in MDX files ────────────────────────────────────

def audit_seo() -> None:
    """Flag MDX files missing critical SEO fields."""
    log("Task 5: Auditing SEO fields...")

    missing_title     = []
    missing_org       = []
    missing_last_date = []
    bad_publish_date  = []

    for fpath in (CONTENT_DIR / "jobs").rglob("*.mdx"):
        text  = fpath.read_text(encoding="utf-8")
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        front = parts[1]

        has_title     = re.search(r'^title:', front, re.M)
        has_org       = re.search(r'^organization:', front, re.M)
        has_last_date = re.search(r'^lastDate:', front, re.M)
        has_published = re.search(r'^publishedAt:', front, re.M)

        slug = fpath.stem
        if not has_title:
            missing_title.append(slug)
        if not has_org:
            missing_org.append(slug)
        if not has_last_date:
            missing_last_date.append(slug)
        if not has_published:
            bad_publish_date.append(slug)

    log(f"  Missing title: {len(missing_title)}")
    log(f"  Missing organization: {len(missing_org)}")
    log(f"  Missing lastDate: {len(missing_last_date)}")
    log(f"  Missing publishedAt: {len(bad_publish_date)}")

    if missing_title:
        log(f"  ⚠️  Files missing title (first 5): {missing_title[:5]}")


# ── Task 6: Problem board summary ────────────────────────────────────────────

def print_problem_board() -> None:
    log("Task 6: Open problem board:")
    problems = load_problems()
    open_p   = [p for p in problems if p.get("status") == "open"]
    for p in open_p:
        log(f"  [{p['priority'].upper():8s}] {p['id']}: {p['title']}")
    if not open_p:
        log("  All problems resolved!")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M IST")
    date = datetime.now().strftime("%Y-%m-%d")

    log(f"=== Naukri Dhaba Agent starting at {ts} ===")

    # Current state
    counts  = count_mdx()
    total   = sum(counts.values())
    commits = recent_content_commits(24)
    state   = load_state()
    prev    = state.get("counts", {})

    log(f"Content: {counts} | Total: {total}")

    # --- Task 1: Fix branding contamination (commit separately) ---
    branded_fixed = fix_branding()
    if branded_fixed > 0:
        git_commit(
            f"fix(agent): remove Sarkari Result branding from {branded_fixed} MDX files [skip ci]",
            ["content/"],
        )

    # --- Task 2: Audit freshness and alert ---
    audit_freshness(counts, prev)

    # --- Task 3: Clear seen_items if stale ---
    cleared = clear_seen_items_if_stale(commits)

    # --- Task 4: Trigger scraper if stale ---
    triggered = trigger_scraper_if_stale(commits)

    if cleared or triggered:
        paths = []
        if cleared:
            paths.append(str(SEEN_FILE))
        if triggered:
            paths.append(str(RUN_NOW_FILE))
        git_commit(
            f"fix(agent): {'clear seen_items + ' if cleared else ''}trigger scraper re-run [skip ci]",
            paths,
        )

    # --- Task 5: SEO audit ---
    audit_seo()

    # --- Task 6: Problem board ---
    print_problem_board()

    # --- Save state ---
    save_state({"date": date, "counts": counts})

    # --- Summary ---
    log("\n=== AGENT RUN SUMMARY ===")
    log(f"Fixes applied ({len(FIXES_APPLIED)}):")
    for f in FIXES_APPLIED:
        log(f"  ✓ {f}")
    log(f"Issues created ({len(ISSUES_CREATED)}):")
    for i in ISSUES_CREATED:
        log(f"  → {i}")
    if not FIXES_APPLIED and not ISSUES_CREATED:
        log("  Nothing to fix — site is healthy.")
    log("=========================")


if __name__ == "__main__":
    main()

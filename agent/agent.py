#!/usr/bin/env python3
"""
Naukri Dhaba — Autonomous Agent
================================
Runs every 3 hours via GitHub Actions.

Goals (in priority order):
  0. PRIMARY: Full SEO rewrite of every MDX file —
       - Strip all Sarkari Result branding
       - Generate unique 200-word keyword-rich shortDescription per job
       - Replace stock howToApply with clean Naukri Dhaba copy
       - Enrich body: lead paragraph, key details table, eligibility,
         numbered steps, 5-Q FAQ — all unique per page
  1. Branding fast-pass — catch any missed Sarkari Result mentions
  2. Audit content freshness — alert if no new content in 24h
  3. Audit content counts — alert if count drops
  4. Clear seen_items.json when stale — forces scraper to re-collect
  5. Trigger scraper re-run by writing scraper/run-now
  6. Check Copilot PRs — test build, merge to main if passing
  7. Live schema audit — fetch real URLs, compare vs sarkariresult, escalate gaps
  8. Fix schema code gaps — lib/seo.ts + page wiring per agent/knowledge.md
  9. Report open problem board

Knowledge base: agent/knowledge.md — read this for all schema specs and SEO rules.

Escalation policy:
  When the agent cannot fix something itself, it creates a GitHub issue,
  assigns it to GitHub Copilot for resolution, and tracks it in state.json.
  On the next run, the agent checks whether Copilot opened a PR for it,
  runs a full build test, and merges to main if the build is green.
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
[GITHUB_OWNER, GITHUB_REPO_NAME] = (GITHUB_REPO.split("/", 1) + ["naukri-dhaba"])[:2]

sys.path.insert(0, str(REPO_ROOT / "scraper"))

CONTENT_TYPES = ["jobs", "results", "admit-cards", "answer-keys", "syllabus"]
FLAT_TYPES    = {"answer-keys", "syllabus"}

BRAND_PATTERNS = [
    (re.compile(r'(?i)sarkari\s*results?(?:\.(?:com|org|in))?'), "Naukri Dhaba"),
    (re.compile(r'(?i)www\.sarkariresults?\.(?:com|org|in)'),    "www.naukridhaba.in"),
    (re.compile(r'(?i)sarkariresults?\.(?:com|org|in)'),         "naukridhaba.in"),
]

ISSUES_CREATED: list[str] = []
FIXES_APPLIED:  list[str] = []
ESCALATED:      list[dict] = []


# ── Utilities ─────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(f"[agent] {msg}", flush=True)


def _gh(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a gh CLI command with the GitHub token."""
    return subprocess.run(
        ["gh"] + args,
        capture_output=True, text=True, timeout=timeout,
        env={**os.environ, "GH_TOKEN": GITHUB_TOKEN},
        cwd=REPO_ROOT,
    )


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
        r = subprocess.run(
            ["git", "log", f"--since={hours} hours ago", "--oneline", "--", "content/"],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=30,
        )
        return [l for l in r.stdout.strip().splitlines() if l]
    except Exception as exc:
        log(f"git log failed: {exc}")
        return []


def git_commit(message: str, paths: list[str]) -> bool:
    try:
        subprocess.run(["git", "config", "user.name", "Naukri Dhaba Agent"],
                       cwd=REPO_ROOT, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "bot@naukridhaba.in"],
                       cwd=REPO_ROOT, check=True, capture_output=True)
        subprocess.run(["git", "add"] + paths, cwd=REPO_ROOT, check=True, capture_output=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"],
                          cwd=REPO_ROOT, capture_output=True).returncode == 0:
            log("Nothing to commit.")
            return False
        subprocess.run(["git", "commit", "-m", message],
                       cwd=REPO_ROOT, check=True, capture_output=True)
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


# ── Copilot escalation ────────────────────────────────────────────────────────

def escalate_to_copilot(title: str, body: str, error: str = "") -> str:
    """
    Create a GitHub issue, assign it to GitHub Copilot, and track it in state.json.

    On the next agent run, check_copilot_prs() will pick up any PR Copilot
    opened for this issue, run a full build test, and merge to main if green.

    Returns the issue URL or '' on failure.
    """
    if not GITHUB_TOKEN:
        log("No GITHUB_TOKEN — cannot escalate.")
        return ""

    ts = datetime.now().strftime("%Y-%m-%d %H:%M IST")
    full_body = f"""{body}

---

## Error details
```
{error or "No error details captured."}
```

## Agent instructions for Copilot
1. Investigate the root cause described above
2. Create a PR with a minimal, correct fix
3. Do NOT modify unrelated files
4. The Naukri Dhaba Agent will automatically test your PR (`npm run build`) and merge it to `main` if it passes

*Escalated by Naukri Dhaba Agent at {ts}*"""

    # Try assigning to Copilot (requires Copilot to be enabled on the repo)
    r = _gh(["issue", "create",
              "--title", title,
              "--body", full_body,
              "--assignee", "Copilot",
              "--label", "agent-escalation,copilot"])

    if r.returncode != 0:
        # Copilot not assignable — create without assignee, mention in body
        fallback_body = full_body + "\n\n> @github-copilot please fix this issue."
        r = _gh(["issue", "create",
                 "--title", title,
                 "--body", fallback_body,
                 "--label", "agent-escalation"])

    url = r.stdout.strip()
    if r.returncode == 0 and url:
        log(f"Escalated to Copilot: {url}")
        ESCALATED.append({"title": title, "url": url, "created": ts})
        ISSUES_CREATED.append(url)

        # Extract issue number and track it
        m = re.search(r'/issues/(\d+)', url)
        if m:
            state = load_state()
            pending = state.get("copilot_issues", [])
            pending.append({"issue": int(m.group(1)), "title": title, "url": url, "created": ts})
            state["copilot_issues"] = pending
            save_state(state)
        return url
    else:
        log(f"Escalation failed: {r.stderr.strip()}")
        return ""


# ── Copilot PR tester ─────────────────────────────────────────────────────────

def _run_build() -> tuple[bool, str]:
    """Run `npm ci && npm run build`. Returns (passed, output)."""
    log("  Running npm ci...")
    r1 = subprocess.run(
        ["npm", "ci", "--prefer-offline"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=300,
    )
    if r1.returncode != 0:
        return False, r1.stdout[-3000:] + r1.stderr[-2000:]

    log("  Running npm run build...")
    r2 = subprocess.run(
        ["npm", "run", "build"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=600,
        env={**os.environ, "NEXT_PUBLIC_SITE_URL": "https://naukridhaba.in"},
    )
    output = (r2.stdout + r2.stderr)[-4000:]
    return r2.returncode == 0, output


def _comment_on_pr(pr_number: int, body: str) -> None:
    _gh(["pr", "comment", str(pr_number), "--body", body])


def check_copilot_prs() -> None:
    """
    Find PRs opened by GitHub Copilot that fix agent-escalated issues.
    For each: run npm build → merge to main if green, comment error if red.
    """
    log("Task 6: Checking for Copilot PRs to test and merge...")

    state   = load_state()
    pending = state.get("copilot_issues", [])
    if not pending:
        log("  No pending Copilot issues.")
        return

    # Get open PRs from Copilot
    r = _gh(["pr", "list",
              "--author", "app/github-copilot",
              "--state", "open",
              "--json", "number,title,headRefName,url,body"])

    if r.returncode != 0:
        # Try alternative author format
        r = _gh(["pr", "list",
                  "--state", "open",
                  "--json", "number,title,headRefName,url,body,author"])

    try:
        prs = json.loads(r.stdout or "[]")
    except Exception:
        log(f"  Could not parse PR list: {r.stdout[:200]}")
        return

    log(f"  Found {len(prs)} open PR(s) to evaluate.")

    resolved_issues: list[int] = []

    for pr in prs:
        pr_num    = pr["number"]
        pr_branch = pr.get("headRefName", "")
        pr_url    = pr.get("url", "")
        pr_title  = pr.get("title", "")
        pr_body   = pr.get("body", "") or ""

        # Check if this PR references any of our tracked issues
        issue_nums_in_pr = set(int(m) for m in re.findall(r'#(\d+)', pr_body + pr_title))
        tracked_nums     = {item["issue"] for item in pending}
        matched          = issue_nums_in_pr & tracked_nums

        if not matched and not any(
            item["title"].lower() in (pr_title + pr_body).lower() for item in pending
        ):
            log(f"  PR #{pr_num} doesn't match any tracked issue — skipping.")
            continue

        log(f"  Testing PR #{pr_num}: {pr_title} (branch: {pr_branch})")

        # Checkout the PR branch
        checkout = subprocess.run(
            ["git", "fetch", "origin", f"{pr_branch}:{pr_branch}"],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=60,
        )
        if checkout.returncode != 0:
            log(f"  Could not fetch branch {pr_branch}: {checkout.stderr[:200]}")
            continue

        # Stash current changes, test PR branch
        subprocess.run(["git", "stash"], cwd=REPO_ROOT, capture_output=True)
        subprocess.run(["git", "checkout", pr_branch], cwd=REPO_ROOT, capture_output=True)

        passed, output = _run_build()

        # Return to original branch
        current_branch = os.environ.get("GITHUB_REF_NAME", "main")
        subprocess.run(["git", "checkout", current_branch], cwd=REPO_ROOT, capture_output=True)
        subprocess.run(["git", "stash", "pop"], cwd=REPO_ROOT, capture_output=True)

        if passed:
            log(f"  ✅ PR #{pr_num} build PASSED — merging to main.")
            _comment_on_pr(pr_num, (
                "## ✅ Agent build test passed\n\n"
                f"The Naukri Dhaba Agent ran `npm run build` on branch `{pr_branch}` and it succeeded.\n\n"
                "Merging to `main` now.\n\n"
                "*— Naukri Dhaba Agent*"
            ))
            merge = _gh(["pr", "merge", str(pr_num),
                          "--merge", "--subject", f"fix: merge Copilot fix for #{pr_num}"])
            if merge.returncode == 0:
                log(f"  Merged PR #{pr_num} to main.")
                FIXES_APPLIED.append(f"Merged Copilot PR #{pr_num}: {pr_title}")
                resolved_issues.update(matched)
            else:
                log(f"  Merge failed: {merge.stderr[:200]}")
        else:
            log(f"  ❌ PR #{pr_num} build FAILED.")
            _comment_on_pr(pr_num, (
                "## ❌ Agent build test failed\n\n"
                f"The Naukri Dhaba Agent ran `npm run build` on branch `{pr_branch}` and it **failed**.\n\n"
                "```\n"
                f"{output[-2000:]}\n"
                "```\n\n"
                "Please fix the errors above and push an update to this PR.\n\n"
                "*— Naukri Dhaba Agent*"
            ))

    # Remove resolved issues from tracking
    if resolved_issues:
        state["copilot_issues"] = [
            item for item in pending if item["issue"] not in resolved_issues
        ]
        save_state(state)


# ── Task 0: SEO rewrite ───────────────────────────────────────────────────────

def run_seo_rewrite() -> None:
    log("Task 0 [PRIMARY]: Running SEO rewriter on all MDX files...")
    try:
        from tasks.seo_rewriter import run as seo_run
        changed = seo_run()
        if changed > 0:
            FIXES_APPLIED.append(f"SEO rewrite: {changed} MDX files — unique content, clean branding, FAQ")
            git_commit(
                f"fix(agent): SEO rewrite — {changed} files: unique content, branding removed, FAQ added [skip ci]",
                ["content/"],
            )
    except Exception as exc:
        log(f"  SEO rewriter failed: {exc}")
        escalate_to_copilot(
            title="🔧 Agent SEO rewriter crashed — needs fix",
            body=(
                "## Problem\n\n"
                "The agent's SEO rewriter (`agent/tasks/seo_rewriter.py`) crashed during execution. "
                "This means 218+ MDX files still contain 'Sarkari Result' branding and lack proper "
                "SEO content. This directly causes Google to suppress naukridhaba.in pages.\n\n"
                "## Expected behaviour\n"
                "The rewriter should scan all `content/**/*.mdx` files, replace branding, "
                "generate unique `shortDescription`, replace `howToApply`, and enrich the MDX body."
            ),
            error=str(exc),
        )


# ── Task 1: Branding fast-pass ────────────────────────────────────────────────

def fix_branding() -> int:
    log("Task 1: Branding fast-pass...")
    fixed = 0
    for fpath in CONTENT_DIR.rglob("*.mdx"):
        try:
            original = fpath.read_text(encoding="utf-8")
            cleaned  = original
            parts    = cleaned.split("---", 2)
            if len(parts) < 3:
                for p, r in BRAND_PATTERNS:
                    cleaned = p.sub(r, cleaned)
            else:
                front_lines = parts[1].split("\n")
                new_front   = []
                for line in front_lines:
                    if re.match(r'\s*source(?:Url)?:', line, re.I):
                        new_front.append(line)
                    else:
                        for p, r in BRAND_PATTERNS:
                            line = p.sub(r, line)
                        new_front.append(line)
                body = parts[2]
                for p, r in BRAND_PATTERNS:
                    body = p.sub(r, body)
                cleaned = "---" + "\n".join(new_front) + "---" + body

            if cleaned != original:
                fpath.write_text(cleaned, encoding="utf-8")
                fixed += 1
        except Exception:
            pass

    log(f"  Fixed {fixed} files.")
    if fixed > 0:
        FIXES_APPLIED.append(f"Branding fast-pass: removed Sarkari Result from {fixed} files")
    return fixed


# ── Task 2: Freshness audit ───────────────────────────────────────────────────

def audit_freshness(counts: dict[str, int], prev: dict[str, int], commits: list[str]) -> None:
    log("Task 2: Auditing content freshness...")
    total      = sum(counts.values())
    prev_total = sum(prev.values()) if prev else None
    log(f"  Commits (24h): {len(commits)} | Total MDX: {total} (prev: {prev_total})")

    if not commits:
        escalate_to_copilot(
            title=f"⚠️ Scraper stale — no content in 24h ({datetime.now().strftime('%d %b %Y')})",
            body=(
                "## No content refresh in 24 hours\n\n"
                f"**Current content:**\n{counts_table(counts)}\n\n"
                "The scraper has not committed any new MDX content in the last 24 hours. "
                "This may mean the scraper is blocked, crashing, or `seen_items.json` is too full.\n\n"
                "**The agent has already:**\n"
                "- Cleared `seen_items.json` to allow full re-scrape\n"
                "- Written `scraper/run-now` to trigger an immediate scrape\n\n"
                "**If the next scraper run also fails**, please investigate:\n"
                "1. `scraper/logs/scraper.log` for block/error patterns\n"
                "2. The CF Worker proxy secret (`CF_WORKER_PROXY_URL` in GitHub secrets)\n"
                "3. Whether sarkariresult.com changed its HTML structure"
            ),
        )

    if prev_total and total < prev_total:
        diff = prev_total - total
        escalate_to_copilot(
            title=f"🚨 Content dropped by {diff} files ({datetime.now().strftime('%d %b %Y')})",
            body=(
                f"## Content count decreased by {diff}\n\n"
                f"| | Count |\n|--|--|\n"
                f"| Yesterday | {prev_total} |\n"
                f"| Today | {total} |\n"
                f"| **Drop** | **-{diff}** |\n\n"
                f"{counts_table(counts)}\n\n"
                "MDX files have been deleted from the repo. "
                "Check `git log -- content/` to find what happened."
            ),
        )


# ── Task 3+4: seen_items + scraper trigger ────────────────────────────────────

def clear_and_trigger(commits: list[str]) -> None:
    if commits:
        log("Tasks 3+4: Content fresh — no action needed.")
        return

    cleared  = False
    triggered = False

    if SEEN_FILE.exists():
        try:
            count = len(json.loads(SEEN_FILE.read_text()))
        except Exception:
            count = 0
        log(f"Task 3: Clearing seen_items.json ({count} entries)...")
        SEEN_FILE.write_text("[]")
        FIXES_APPLIED.append(f"Cleared seen_items.json ({count} entries)")
        cleared = True

    ts = datetime.now().isoformat()
    RUN_NOW_FILE.write_text(f"Agent re-run triggered at {ts}\n")
    log("Task 4: Wrote scraper/run-now.")
    FIXES_APPLIED.append("Wrote scraper/run-now → triggers immediate scraper")
    triggered = True

    paths = []
    if cleared:  paths.append(str(SEEN_FILE))
    if triggered: paths.append(str(RUN_NOW_FILE))
    git_commit(
        "fix(agent): clear seen_items + trigger scraper re-run [skip ci]",
        paths,
    )


# ── Task 5: SEO field audit ───────────────────────────────────────────────────

def audit_seo_fields() -> None:
    log("Task 5: SEO field audit...")
    missing: dict[str, list[str]] = {"title": [], "organization": [], "lastDate": [], "publishedAt": []}
    for fpath in (CONTENT_DIR / "jobs").rglob("*.mdx"):
        front = fpath.read_text(encoding="utf-8").split("---", 2)
        if len(front) < 3: continue
        f = front[1]
        for key in missing:
            if not re.search(rf'^{key}:', f, re.M):
                missing[key].append(fpath.stem)

    for key, slugs in missing.items():
        log(f"  Missing {key}: {len(slugs)} files")
        if len(slugs) > 20:
            escalate_to_copilot(
                title=f"🔍 {len(slugs)} job MDX files missing `{key}` field",
                body=(
                    f"## Missing `{key}` in MDX frontmatter\n\n"
                    f"{len(slugs)} job MDX files are missing the `{key}` field. "
                    f"This field is required for SEO metadata and schema markup.\n\n"
                    f"**First 10 affected files:**\n"
                    + "\n".join(f"- `content/jobs/**/{s}.mdx`" for s in slugs[:10]) +
                    "\n\n**Fix:** Add a `{key}` field to each file's frontmatter. "
                    "For `publishedAt` use today's date (`YYYY-MM-DD`) if unknown."
                ),
            )


# ── Task 8: Schema code fixer ─────────────────────────────────────────────────

def fix_schema_code() -> None:
    """
    Task 8: Fix known schema code gaps in lib/seo.ts and wire schema into page
    components, as documented in agent/knowledge.md.

    Fixes applied (idempotent — safe to run every 3h):
    - buildOrganizationJsonLd: logo → ImageObject
    - buildAdmitJsonLd: add endDate + image
    - buildSyllabusJsonLd: add teaches field
    - app/answer-keys/[slug]/page.tsx: wire buildAnswerKeyJsonLd
    - app/syllabus/[slug]/page.tsx: wire buildSyllabusJsonLd
    - app/jobs/[category]/[slug]/page.tsx: wire buildFaqJsonLd
    - app/jobs/[category]/page.tsx: wire buildListingPageJsonLd
    - app/results/[category]/page.tsx: wire buildListingPageJsonLd
    - app/admit-cards/[category]/page.tsx: wire buildListingPageJsonLd
    """
    log("Task 8: Fixing schema code gaps (per agent/knowledge.md)...")
    try:
        from tasks.fix_schema import run as schema_fix_run
        fixed = schema_fix_run()
        if fixed > 0:
            FIXES_APPLIED.append(f"Schema code fixes: {fixed} changes in lib/seo.ts + page components")
            git_commit(
                f"fix(agent): schema markup — {fixed} fixes in seo.ts + page wiring [skip ci]",
                [
                    "lib/seo.ts",
                    "app/jobs/",
                    "app/results/",
                    "app/admit-cards/",
                    "app/answer-keys/",
                    "app/syllabus/",
                ],
            )
        else:
            log("  Schema code: all checks passed — no gaps.")
    except Exception as exc:
        log(f"  fix_schema crashed: {exc}")
        escalate_to_copilot(
            title="🔧 Agent schema fixer crashed — needs investigation",
            body=(
                "## Problem\n\n"
                "The agent's `fix_schema` task (`agent/tasks/fix_schema.py`) crashed.\n\n"
                "This means the following schema gaps remain unfixed:\n"
                "- `buildOrganizationJsonLd`: logo must be ImageObject (not bare URL)\n"
                "- `buildAdmitJsonLd`: missing `endDate` and `image` fields\n"
                "- `buildSyllabusJsonLd`: missing `teaches` field\n"
                "- `app/answer-keys/[slug]/page.tsx`: `buildAnswerKeyJsonLd` not wired\n"
                "- `app/syllabus/[slug]/page.tsx`: `buildSyllabusJsonLd` not wired\n"
                "- `app/jobs/[category]/[slug]/page.tsx`: `buildFaqJsonLd` not wired\n"
                "- Category listing pages: `buildListingPageJsonLd` not wired\n\n"
                "**Fix:** Debug `agent/tasks/fix_schema.py` and ensure the string patches "
                "match the current content of `lib/seo.ts` and the page.tsx files exactly.\n\n"
                "See `agent/knowledge.md` section 10 for full gap details."
            ),
            error=str(exc),
        )


# ── Task 9: Problem board ─────────────────────────────────────────────────────

def print_problem_board() -> None:
    log("Task 7: Open problem board:")
    open_p = [p for p in load_problems() if p.get("status") == "open"]
    for p in open_p:
        log(f"  [{p['priority'].upper():8s}] {p['id']}: {p['title']}")
    if not open_p:
        log("  All tracked problems resolved!")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M IST")
    date = datetime.now().strftime("%Y-%m-%d")

    log(f"=== Naukri Dhaba Agent — {ts} ===")
    log("GOALS:")
    log("  • Mirror all sarkariresult.com content from 2023→present")
    log("  • Zero Sarkari Result branding in any page")
    log("  • Full SEO: unique content, schema markup, meta, keywords")
    log("  • Every page indexed in Google with job rich results")

    counts  = count_mdx()
    total   = sum(counts.values())
    commits = recent_content_commits(24)
    state   = load_state()
    prev    = state.get("counts", {})
    log(f"Content: {counts} | Total: {total}")

    # 0. SEO rewrite (primary — fixes branding + generates unique content)
    run_seo_rewrite()

    # 1. Branding fast-pass (catch anything the rewriter missed)
    fixed = fix_branding()
    if fixed > 0:
        git_commit(
            f"fix(agent): branding fast-pass — {fixed} files [skip ci]",
            ["content/"],
        )

    # 2. Freshness audit (escalates to Copilot if stale)
    audit_freshness(counts, prev, commits)

    # 3+4. Clear seen_items + trigger scraper if stale
    clear_and_trigger(commits)

    # 5. SEO field audit (escalates missing fields to Copilot)
    audit_seo_fields()

    # 6. Check Copilot PRs → test build → merge to main if green
    if GITHUB_TOKEN:
        try:
            check_copilot_prs()
        except Exception as exc:
            log(f"  Copilot PR check failed: {exc}")

    # 7. Schema audit — fetch live pages, compare with sarkariresult, escalate gaps
    log("Task 7: Running live schema audit (fetches real URLs — no cached knowledge)...")

    try:
        from tasks.schema_audit import run as schema_run
        audit = schema_run()
        summary = audit.get("summary", {})
        issues  = audit.get("issues", [])

        # Log what we have vs what sarkariresult has
        log(f"  Our schema types:    {summary.get('our_schema_types', [])}")
        log(f"  Source schema types: {summary.get('source_schema_types', [])}")
        log(f"  We have, they don't: {summary.get('types_we_have_they_dont', [])}  ← our SEO advantage")
        they_have = summary.get("types_they_have_we_dont", [])
        if they_have:
            log(f"  They have, we don't: {they_have}  ← GAP to fix")
            escalate_to_copilot(
                title=f"🔍 Schema gap vs sarkariresult: {', '.join(they_have)}",
                body=(
                    "## Schema markup gap detected\n\n"
                    "The live schema audit found that sarkariresult.com uses schema types "
                    "that naukridhaba.in is missing:\n\n"
                    f"**Missing from naukridhaba.in:** `{'`, `'.join(they_have)}`\n\n"
                    f"**Our current types:** `{'`, `'.join(summary.get('our_schema_types', []))}`\n\n"
                    f"**Source types:** `{'`, `'.join(summary.get('source_schema_types', []))}`\n\n"
                    "Please add the missing schema type(s) to the relevant page components in `lib/seo.ts` "
                    "and wire them into the appropriate `app/.../page.tsx` files."
                ),
            )

        # Escalate individual page issues
        for issue in issues:
            escalate_to_copilot(
                title=f"🔍 Schema issue on {issue['url']}",
                body=(
                    f"## Missing/incomplete schema on live page\n\n"
                    f"**URL:** {issue['url']}\n\n"
                    f"**Problem:** {issue['problem']}\n\n"
                    f"**Missing fields:** `{'`, `'.join(issue.get('missing_fields', []))}`\n\n"
                    "Check `lib/seo.ts` → `buildJobJsonLd()` and ensure all required `JobPosting` "
                    "fields are populated from the MDX frontmatter."
                ),
            )
    except Exception as exc:
        log(f"  Schema audit failed: {exc}")

    # 8. Fix schema code gaps (idempotent — reads knowledge.md as spec)
    fix_schema_code()

    # 9. Problem board
    print_problem_board()

    # Save state
    s = load_state()
    s["date"]   = date
    s["counts"] = counts
    save_state(s)

    # Summary
    log("\n=== SUMMARY ===")
    log(f"Fixes ({len(FIXES_APPLIED)}):     " + " | ".join(FIXES_APPLIED) if FIXES_APPLIED else "Fixes (0): none")
    log(f"Escalated ({len(ESCALATED)}):  " + " | ".join(e["title"] for e in ESCALATED) if ESCALATED else "Escalated (0): none")
    log(f"Issues created: {len(ISSUES_CREATED)}")
    log("===============")


if __name__ == "__main__":
    main()

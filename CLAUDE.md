# Naukri Dhaba — Claude Code Notes

## RULE #1 — NON-SKIPPABLE

**When fixing the scraper: do not stop and do not report problems. Keep fixing until the scraper successfully runs and produces new MDX content.** No stopping to ask questions, no listing blockers — just fix and keep going until it works.

## Screenshots

For taking screenshots of HTML pages, follow `.claude/screenshot-guide.md` exactly.

**TL;DR**: Use `puppeteer-core` + playwright's chromium at `/root/.cache/ms-playwright/chromium-1194/chrome-linux/chrome`. Do NOT try selenium, html2image, snap chromium, or playwright's own API — they all fail in this environment. The guide has a copy-paste script.

## Preview Screenshots Location
- Desktop: `preview-screenshots/desktop/`
- Mobile: `preview-screenshots/mobile/`

# Restore / Rollback Instructions

## Pre-UI-redesign snapshot

Main branch before the single-Share-button + pills + resources changes:

```
commit 73f50536862f3edd29e1a3b91955656f373b9693
```

## To undo the UI changes after merging

```bash
# 1. Revert the three commits that introduced the changes
git revert --no-commit b537794 f11ac15 022d931

# 2. Commit the revert
git commit -m "revert: undo share button + pills + resources redesign"

# 3. Push to main
git push origin main
```

## To restore a single page

```bash
git checkout 73f5053 -- jobs/railway/railway-group-d-apply-online-2026.html
```
Replace the path with whichever page you need.

## To restore ALL generated pages only (keep static page changes)

```bash
git checkout 73f5053 -- jobs/ results/ admit-cards/ css/style.css
git commit -m "revert: restore all job/result/admit-card pages to pre-redesign"
```

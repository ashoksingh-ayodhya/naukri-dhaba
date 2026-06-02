# Scraper Fixes Applied

All fixes deployed to main branch. See commit history for details.

## Key Fixes

1. **page_type missing from sitemap items** - root cause of results/admits never growing
2. **CF Worker 404 skip** - prevents wasting time on dead pages
3. **Challenge page rejection** - rejects Cloudflare bot-challenge pages
4. **repository_dispatch self-trigger** - GITHUB_TOKEN push doesn't fire push triggers
5. **80-min workflow timeout** - was 55 min, now 80 min
6. **File reclassification** - 227 misplaced result/admit/syllabus files moved
7. **MIN_POST_DATE** - lowered from 2023 to 2022-01-01

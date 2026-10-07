---
id: '004'
title: Untrack generated data and images; retire fetch-data.sh
status: done
use-cases:
- SUC-003
depends-on:
- '001'
- '003'
github-issue: ''
issue: 69-build-the-site-from-the-bucket-and-stop-committing-scraped-data.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Untrack generated data and images; retire fetch-data.sh

## Description

git rm --cached all generated files (src/data opportunities, scrape-meta, ads, yield-history, teams, places, clubs; public/data/** ; public/images/opportunities/**) and add them to .gitignore. src/data/partners.json stays tracked. Delete scripts/fetch-data.sh. The uncommitted working-tree data refresh is superseded and may be discarded/untracked. Do NOT touch src/pages/index.astro, clasi/issues/67, 68, or scraper/docker/.

## Acceptance Criteria

- [x] git ls-files shows no generated data/image file; src/data/partners.json still tracked and unchanged
- [x] Generated paths are in .gitignore (verify partners.json is not ignored)
- [x] scripts/fetch-data.sh removed; no remaining references (grep)
- [x] After a clean checkout, `npm ci && npm run build` succeeds
- [x] Only generated data files and ignore/script changes are in the commit

## Implementation Plan

Files to create/modify: .gitignore, git index, scripts/fetch-data.sh

## Testing

- **Existing tests to run**: `uv run pytest` (scraper) if scraper touched; `npm run build`
- **New tests to write**: as listed in acceptance criteria
- **Verification command**: `git ls-files check; npm run build`

---
id: '005'
title: Update README and data-access docs for build-time fetch
status: done
use-cases:
- SUC-003
depends-on:
- '004'
github-issue: ''
issue: 69-build-the-site-from-the-bucket-and-stop-committing-scraped-data.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Update README and data-access docs for build-time fetch

## Description

Update README, scraper/README.md, src/pages/data-access.astro (and for-agents / llms.txt only where they mention how data is produced) to describe build-time fetching, npm run fetch-data, --local, and that the published /data and /images URLs are unchanged. SCHEMA.md remains outside the site contract.

## Acceptance Criteria

- [x] README documents fetch-on-missing, fetch-data, --local and CI always-fetch
- [x] /data-access wording matches; URL contract text unchanged
- [x] No mention of fetch-data.sh, aws CLI or committed data remains
- [x] npm run build passes

## Implementation Plan

Files to create/modify: README.md, scraper/README.md, src/pages/data-access.astro

## Testing

- **Existing tests to run**: `uv run pytest` (scraper) if scraper touched; `npm run build`
- **New tests to write**: as listed in acceptance criteria
- **Verification command**: `npm run build`

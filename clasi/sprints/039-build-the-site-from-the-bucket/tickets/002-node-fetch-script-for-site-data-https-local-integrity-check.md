---
id: '002'
title: Node fetch script for site data (HTTPS, --local, integrity check)
status: done
use-cases:
- SUC-002
depends-on: []
github-issue: ''
issue: 69-build-the-site-from-the-bucket-and-stop-committing-scraped-data.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Node fetch script for site data (HTTPS, --local, integrity check)

## Description

Replace scripts/fetch-data.sh with scripts/fetch-data.mjs (Node 22 fetch, no dependencies, no credentials, no aws/rsync/python). Base URL https://jtl-stem-ecosystem-scrape.sfo3.digitaloceanspaces.com/data/ (overridable by env). Fetch root files, then per-partner events_url/past_events_url from the partners.json envelope, then images referenced by image_src; no bucket listing. Keep the existing destination mapping (opportunities, scrape-meta, ads, yield-history -> src/data; teams, places, clubs -> src/data and public/data; partners.json envelope -> public/data only). Never touch src/data/partners.json; SCHEMA.md is not fetched.

## Acceptance Criteria

- [x] Downloads all required files over HTTPS and writes them to the same destinations as fetch-data.sh
- [x] Mirrors: removes stale public/data/partners/<slug> dirs and unreferenced images
- [x] Integrity check kept: any referenced image missing, any non-200, or invalid JSON exits non-zero with a clear message
- [x] --local <dir> copies from a local scraper output dir with the same mapping and checks
- [x] src/data/partners.json is never written (test asserts it)
- [x] Fixture-based node test (node --test) covers success, missing image, HTTP error

## Implementation Plan

Files to create/modify: scripts/fetch-data.mjs, scripts/test/ fixtures

## Testing

- **Existing tests to run**: `uv run pytest` (scraper) if scraper touched; `npm run build`
- **New tests to write**: as listed in acceptance criteria
- **Verification command**: `node --test scripts/`

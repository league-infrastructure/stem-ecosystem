---
id: '001'
title: Scraper publishes data/ public-read; backfill existing objects
status: open
use-cases: [SUC-001]
depends-on: []
github-issue: ''
issue: 69-build-the-site-from-the-bucket-and-stop-committing-scraped-data.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Scraper publishes data/ public-read; backfill existing objects

## Description

The coordinator's spike (2026-10-07) showed put_object_acl(ACL='public-read') works with the scoped key: anonymous GET of data/scrape-meta.json returns 200 and anonymous list of cache/ returns 403. No console/policy step needed. Make it permanent: the bucket Store sets ACL='public-read' on writes whose key is under data/ (never cache/), and a one-time backfill script makes the ~917 existing data/ objects public.

## Acceptance Criteria

- [ ] Store.write_bytes passes ACL='public-read' for data/ keys only; cache/ writes carry no ACL
- [ ] Unit tests with a mocked client cover data/ and cache/ keys
- [ ] Backfill script (scraper/scripts or a partner-scrape subcommand, idempotent, supports --dry-run) sets public-read on every data/ object
- [ ] Backfill run against the bucket; anonymous GET of data/scrape-meta.json, one partners/<slug>/events.json and one images/opportunities/ file return 200
- [ ] Anonymous GET of a cache/ object returns 403; finding recorded in the ticket
- [ ] Check whether --site-dir writes conflict with the now-ignored paths; note result

## Implementation Plan

Files to create/modify: scraper/partner_scrape/storage.py, new backfill script, scraper tests

## Testing

- **Existing tests to run**: `uv run pytest` (scraper) if scraper touched; `npm run build`
- **New tests to write**: as listed in acceptance criteria
- **Verification command**: `uv run pytest (from scraper/)`

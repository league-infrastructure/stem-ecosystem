---
id: '005'
title: Migration tooling and equality verification
status: open
use-cases: [SUC-004]
depends-on: ["003", "004"]
github-issue: "77-per-partner-records-in-the-bucket-as-the-source-of-truth.md"
issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Migration tooling and equality verification

## Description

Add `partners/migrate.py` with CLI `partners migrate [--site-dir ..] [--dry-run]` and `partners verify-migration --baseline <path>`. Migrate: split `src/data/partners.json` into records; slug = current `slugify(name)`, stored in the record; upload via the writer with actor `migration`; upload logos from `public/images/logos/` to `data/partners/<slug>/logo.<ext>` and set `logo_src` to `partners/<slug>/logo.<ext>`; copy (never move/delete) `cache/partner_log/**` to `history/partner_log/**`, idempotent and skipping identical objects. Verify: consolidate and compare to baseline, ignoring logo paths, reporting any other diff.

## Acceptance Criteria

- [ ] Dry-run writes nothing and prints a report (counts, slug collisions, missing logos)
- [ ] Slug collisions or unusable names fail the migration before writing
- [ ] Rerun is idempotent (no new history entries for unchanged records)
- [ ] cache/partner_log is never modified or deleted (test)
- [ ] verify-migration exits non-zero on any difference other than logo_src
- [ ] Handles current `logo_src` shapes: bare filenames in public/images/logos (about 187 entries) and 17 entries with no logo; flag any logo_src whose file is missing, or a non-bare/URL value

## Implementation Plan

Programmer must first survey the actual `logo_src` values in src/data/partners.json against files in public/images/logos/ (planner found bare filenames and 17 empty; site pages' usage of logo_src was not checked: grep `src/` for `logo_src` and `/images/logos/` and record findings in the ticket). Test fixture: small roster + logos in tmp dirs, LocalStore. Never touch the real bucket or .env.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest` (and `npm test`/node tests for ticket 006)
- **New tests to write**: as listed in the plan
- **Verification command**: `cd scraper && uv run pytest`

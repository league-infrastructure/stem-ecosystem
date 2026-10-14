---
id: '001'
title: Fix wheel smoke test
status: open
use-cases:
- SUC-001
depends-on: []
github-issue: ''
issue: 91-wheel-smoke-test-fails-since-roster-moved-to-bucket.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Fix wheel smoke test

## Description

Update `scraper/dev/wheel_smoke_test.py` and `.github/workflows/wheel-smoke.yml` so the offline dry run works now that the roster, history, hints and logs stores default to the bucket (issue 91). The team lead pushes and confirms CI.

## Acceptance Criteria

- [ ] Every store env var in `scraper/partner_scrape/config.py` (CACHE, DATA, HISTORY, HINTS, LOGS, any others) points at a local temp dir; `_clean_env` strips them from the inherited environment.
- [ ] A one-partner local roster is seeded (via `partner-scrape partners add` or a `partners/<slug>/partner.json`) before the dry run.
- [ ] No credentials or network used; dry run still writes nothing.
- [ ] `python dev/wheel_smoke_test.py` passes locally from `scraper/`; docstring and workflow comments updated.

## Implementation Plan

Edit the script (env vars, roster seed, docstring) and workflow comment; run the script locally.

## Testing

- **Existing tests to run**: `uv run pytest` in `scraper/`
- **New tests to write**: none (the smoke script is the test)
- **Verification command**: `cd scraper && python dev/wheel_smoke_test.py`

---
id: '003'
title: Consolidation and partners CLI
status: done
use-cases:
- SUC-001
- SUC-002
depends-on:
- '002'
github-issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Consolidation and partners CLI

## Description

Add `partners/consolidate.py`: list `data/partners/*/partner.json`, validate each (extend `registry/validate_roster.py` with an entry point accepting records, not a file path), merge `events_url`/`past_events_url`, write `data/partners.json` in the existing envelope (`generated_at`, `partner_count`, `partners[]`). Bad record fails loudly. Add CLI `partner-scrape partners get <slug> | put <slug> <file> | add | consolidate`, put/add through the writer, add assigns slug (slugify, uniqueness check) and next id.

## Acceptance Criteria

- [x] `partners consolidate` output envelope matches what `export/publish.py` writes today (same fields, same order)
- [x] Invalid record causes non-zero exit naming the slug; no partial overwrite of data/partners.json
- [x] get/put/add work against a local store; put validates before writing
- [x] `--by` option sets actor (default person:$USER)

## Implementation Plan

Reuse the publish.py envelope logic (refactor into a shared function; publish.project keeps working until ticket 004 swaps it). Tests with LocalStore.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest` (and `npm test`/node tests for ticket 006)
- **New tests to write**: as listed in the plan
- **Verification command**: `cd scraper && uv run pytest`

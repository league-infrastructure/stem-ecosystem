---
id: '004'
title: Scraper reads roster from the bucket; partner_log to history
status: done
use-cases:
- SUC-002
depends-on:
- '003'
github-issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Scraper reads roster from the bucket; partner_log to history

## Description

Switch every scraper reader of `$SITE_DIR/src/data/partners.json` to the bucket Roster: `pipeline.py`, `cli.py` (publish_site_dir/partners_path), `export/publish.py`, `export/partner_log.py` (`_default_partners_path`), `directory/pipeline.py` (`_check_related_partner_references`), `normalize/partners.py`/`run.py`, `registry/validate_roster.py`. Call consolidate at the end of `scrape` (replacing publish's hand-built roster) and for the future `updates` job. `export/partner_log.py` writes to prefix `history/partner_log` instead of `cache/partner_log` (migration copy is ticket 005). Remove baking of the roster from `scraper/docker/Dockerfile` (COPY line 69, comments) and `.dockerignore` if present; update docker README ("roster is baked in" text) and DESIGN docs.

## Acceptance Criteria

- [x] No code path reads src/data/partners.json (grep clean except historical comments/migrate tool input)
- [x] --site-dir still controls site-side outputs but no longer the roster; local-dev can point the data store at a local dir
- [x] scrape ends by writing consolidated data/partners.json
- [x] partner_log reads/writes history/partner_log
- [x] Dockerfile no longer copies the roster; README updated
- [x] Existing pytest suite updated and green

## Implementation Plan

READ FIRST: `config.py` (get_site_dir, store accessors) and `storage.py`. Tests use a LocalStore data dir seeded with records. This ticket is the largest; keep the Roster interface compatible with `load_partners` callers (list of dict, or dict keyed by normalized name) so changes are mechanical.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest` (and `npm test`/node tests for ticket 006)
- **New tests to write**: as listed in the plan
- **Verification command**: `cd scraper && uv run pytest`

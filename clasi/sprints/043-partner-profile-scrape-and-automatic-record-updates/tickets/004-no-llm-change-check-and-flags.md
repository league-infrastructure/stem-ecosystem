---
id: '004'
title: No-LLM change check and flags
status: done
use-cases:
- SUC-003
depends-on:
- '003'
github-issue: ''
issue: 75-post-scrape-partner-record-update-check-with-haiku.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# No-LLM change check and flags

## Description

`updates/checks.py`: compare each partner's profile snapshot (and notable redirect) with its record and emit flags with severity; no LLM (issue 75 step 1).

## Acceptance Criteria

- [x] Examines only partners whose snapshot hashes changed since the previous check (state in `cache/updates/state.json` in the scrape-cache store) or that have a notable redirect, or all when `--all`
- [x] Flags: website host vs final URL (high); name vs title/site_name/JSON-LD name (medium); phone, email domain vs website domain, address (medium); social links vs site's links, including dead-link liveness (medium; HEAD/GET via PoliteFetcher); logo URL (low, report-only)
- [x] Severity enum low|medium|high; a partner is sent to Haiku when any flag is medium or higher (stakeholder decision)
- [x] A CMOD-style fixture (rename + domain move + dead twitter + old-domain email) yields high/medium flags; an unchanged partner yields none
- [x] Pure comparison logic is unit-tested; fuzzy name comparison is normalized (case, punctuation, suffix words) to avoid noise

## Implementation Plan

partner_scrape/updates/checks.py, updates/DESIGN.md. Read partners/records.py validator for field names (name, website, phone, email, location, twitter, facebook, instagram, linkedin, description, logo_src).

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: as listed in the acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

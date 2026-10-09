---
id: 009
title: Production run and redeploy (team-lead run)
status: in-progress
use-cases:
- SUC-001
- SUC-002
- SUC-003
- SUC-004
- SUC-006
depends-on:
- 008
- '010'
- '011'
github-issue: ''
issue:
- 73-detect-and-record-redirects-on-every-fetch.md
- 74-weekly-scrape-of-partner-home-about-and-contact-pages.md
- 75-post-scrape-partner-record-update-check-with-haiku.md
- 76-per-partner-event-quality-checks-in-the-post-scrape-report.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Production run and redeploy (team-lead run)

## Description

Team-lead-run production steps with real credentials. Programmers do not read the real `.env`.

## Acceptance Criteria

- [ ] Live redirect check: fetch `http://sdcdm.org`; `final_url` is visitcmod.org and flagged notable
- [ ] `partner-scrape profiles` run for real; report reviewed
- [ ] `partner-scrape updates --dry-run` reviewed (known test case: San Diego Children's Discovery Museum -> Children's Museum of Discovery, sdcdm.org -> visitcmod.org)
- [ ] `partner-scrape updates` run for real; `history/partners/changes.jsonl` shows actor `haiku` entries; archived old records exist; `data/partners.json` consolidated
- [ ] amd64 image built and pushed; swarm stack redeployed (scraper/docker/README.md); first scheduled Sunday run produces logs/profiles and logs/updates objects

## Implementation Plan

Follow the team-lead checklist in sprint.md. Record results in this ticket.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: as listed in the acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

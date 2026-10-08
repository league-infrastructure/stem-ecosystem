---
id: '005'
title: README rewrite and end-to-end image verification
status: open
use-cases: [SUC-001, SUC-002, SUC-003, SUC-004]
depends-on: ['004']
github-issue: ''
issue: 70-run-the-scraper-on-a-schedule-from-a-container-cron.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# README rewrite and end-to-end image verification

## Description

Rewrite `scraper/docker/README.md` for the long-running container and verify the built image end to end.

## Acceptance Criteria

- [ ] README covers: build, `make-secrets.sh`, `docker run -d --ipc=host -e SCRAPER_SECRETS_B64=... partner-scrape`, schedule table, per-job secrets, manual runs (`docker exec ... run-job`, one-shot `docker run --rm`), reading `docker logs`, updating by rebuild, roster baked at build, legacy one-shot usage
- [ ] Image verification recorded in the ticket: decode/env check, `run-job scrape --source <one> --dry-run --no-enrich` one-shot succeeds, supercronic starts and logs the schedule
- [ ] `cd scraper && uv run pytest` passes
- [ ] Update scraper docs/README mention of scheduling if present; mark issue 70 ready to close via normal ticket completion

## Implementation Plan

Files: scraper/docker/README.md. Uses a real image build; no site/deploy changes.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: see acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

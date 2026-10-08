---
id: '005'
title: README rewrite and end-to-end image verification
status: done
use-cases:
- SUC-001
- SUC-002
- SUC-003
- SUC-004
depends-on:
- '004'
github-issue: ''
issue: 70-run-the-scraper-on-a-schedule-from-a-container-cron.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# README rewrite and end-to-end image verification

## Description

Rewrite `scraper/docker/README.md` for the long-running container and verify the built image end to end.

## Acceptance Criteria

- [x] README covers: build, `make-secrets.sh`, `docker run -d --ipc=host -e SCRAPER_SECRETS_B64=... partner-scrape`, schedule table, per-job secrets, manual runs (`docker exec ... run-job`, one-shot `docker run --rm`), reading `docker logs`, updating by rebuild, roster baked at build, legacy one-shot usage
- [x] Image verification recorded in the ticket: decode/env check, `run-job scrape --source <one> --dry-run --no-enrich` one-shot succeeds, supercronic starts and logs the schedule
- [x] `cd scraper && uv run pytest` passes
- [x] Update scraper docs/README mention of scheduling if present; mark issue 70 ready to close via normal ticket completion

## Implementation Plan

Files: scraper/docker/README.md. Uses a real image build; no site/deploy changes.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: see acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

## Verification Evidence (2026-10-08, freshly built image)

- Real-secrets one-shot (run by team lead, bundle from make-secrets.sh, 524 chars): `docker run --rm --ipc=host -e SCRAPER_SECRETS_B64=... partner-scrape run-job scrape --source fleet-science-center --dry-run --no-enrich --no-report` logged START, "wrote 1 opportunity (dry run -- nothing written)", `SUCCESS job=scrape exit=0 duration=15s`. `run-job directory --help` logged SUCCESS. This also proves the bundle decodes into the environment.
- Scheduler start (fake bundle): `docker run -d` with no args printed "starting supercronic with schedule:" with the three crontab entries (CRON_TZ=America/Los_Angeles; scrape 1,4; teams 3; directory 6) and supercronic logged "read crontab" and TZ America/Los_Angeles.
- `cd scraper && uv run pytest`: 2652 passed, 3 skipped.
- Docs: scraper/docker/README.md rewritten; README.md, CLAUDE.md, scraper/README.md, scraper/docs/deploy/scheduled-run.md point at it. Issue 70 is complete with this ticket.

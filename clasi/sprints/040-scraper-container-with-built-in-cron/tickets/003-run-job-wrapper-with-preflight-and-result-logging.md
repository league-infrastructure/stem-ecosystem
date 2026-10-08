---
id: '003'
title: run-job wrapper with preflight and result logging
status: open
use-cases: [SUC-003, SUC-004]
depends-on: ['002']
github-issue: ''
issue: 70-run-the-scraper-on-a-schedule-from-a-container-cron.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# run-job wrapper with preflight and result logging

## Description

Add `scraper/docker/run-job`: `run-job scrape|teams|directory [extra args]`. Maps scrape to `partner-scrape`, teams to `partner-scrape teams`, directory to `partner-scrape directory`; sources load-secrets; preflights required secrets (scrape: DO_SPACES_ACCESS_KEY, DO_SPACES_SECRET_KEY, ANTHROPIC_API_KEY, LEAGUESYNC_API_KEY; teams: DO_SPACES_ACCESS_KEY, DO_SPACES_SECRET_KEY, ANTHROPIC_API_KEY, TBA_KEY; directory: DO_SPACES_ACCESS_KEY, DO_SPACES_SECRET_KEY); logs timestamped lines.

## Acceptance Criteria

- [ ] Prints `<UTC ISO ts> START job=X` then `SUCCESS` or `FAILURE job=X exit=N duration=Ns`; exits with the job's status
- [ ] Missing secrets: FAILURE line naming variable names only, partner-scrape not invoked, non-zero exit
- [ ] Extra args pass through (e.g. `--source foo --dry-run --no-enrich`); with `--no-enrich`/`--dry-run` the ANTHROPIC_API_KEY requirement is waived for scrape; `--no-sponsors --no-descriptions` waive it for teams
- [ ] Unknown job prints usage and exits 2
- [ ] Secret values never appear in output
- [ ] Tests with a stub `partner-scrape` on PATH cover success, failure exit code, missing secrets, pass-through, unknown job

## Implementation Plan

Files: scraper/docker/run-job, extend scraper/tests/test_docker_scripts.py.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: see acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

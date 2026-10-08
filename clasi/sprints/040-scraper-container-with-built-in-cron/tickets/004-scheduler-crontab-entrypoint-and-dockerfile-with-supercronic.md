---
id: '004'
title: 'Scheduler: crontab, entrypoint and Dockerfile with supercronic'
status: done
use-cases:
- SUC-001
- SUC-003
depends-on:
- '003'
github-issue: ''
issue: 70-run-the-scraper-on-a-schedule-from-a-container-cron.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Scheduler: crontab, entrypoint and Dockerfile with supercronic

## Description

Add `scraper/docker/crontab` (CRON_TZ=America/Los_Angeles; scrape `0 3 * * 1,4`, teams `0 3 * * 3`, directory `0 3 * * 6`, each calling `run-job`), `scraper/docker/entrypoint.sh`, and Dockerfile changes: checksum-pinned supercronic for amd64/arm64 via TARGETARCH, tzdata if absent, `TZ=America/Los_Angeles`, copy scripts to a PATH dir, `ENTRYPOINT ["entrypoint.sh"]`, update header comments.

## Acceptance Criteria

- [x] entrypoint.sh: no args or `cron` loads secrets then `exec supercronic` on the crontab, logging the schedule; `run-job ...` execs run-job; any other args exec `partner-scrape "$@"` (legacy one-shot preserved)
- [x] Cron jobs verified to see secrets (e.g. container with a stub or `supercronic` test crontab that runs `env | cut -d= -f1`-style check of names only)
- [x] Verified on the built image: CRON_TZ honored by the pinned supercronic (fallback TZ env) and tzdata present
- [x] Runs as pwuser; image builds with `docker build -f scraper/docker/Dockerfile -t partner-scrape .`
- [x] supercronic download verified by sha256
- [x] Entrypoint dispatch tested in pytest with stubs

## Implementation Plan

Files: scraper/docker/{crontab,entrypoint.sh,Dockerfile}, tests. Container stays up when a job fails.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: see acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

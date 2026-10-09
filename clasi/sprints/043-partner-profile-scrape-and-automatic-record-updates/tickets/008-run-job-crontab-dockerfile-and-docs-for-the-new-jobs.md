---
id: 008
title: run-job, crontab, Dockerfile, and docs for the new jobs
status: open
use-cases:
- SUC-006
depends-on: ['006', '007']
github-issue: ''
issue:
- 73-detect-and-record-redirects-on-every-fetch.md
- 74-weekly-scrape-of-partner-home-about-and-contact-pages.md
- 75-post-scrape-partner-record-update-check-with-haiku.md
- 76-per-partner-event-quality-checks-in-the-post-scrape-report.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# run-job, crontab, Dockerfile, and docs for the new jobs

## Description

Wire the new jobs into the container: run-job, crontab, log types, Dockerfile, and docs.

## Acceptance Criteria

- [ ] `run-job profiles|updates` accepted; required secrets: profiles = DO_SPACES_ACCESS_KEY, DO_SPACES_SECRET_KEY; updates = those plus ANTHROPIC_API_KEY (waived only with `--no-llm`)
- [ ] `logs.LOG_TYPES` maps profiles->profiles and updates->updates so logs land in logs/profiles/ and logs/updates/; `parse_counts` handles the new counts lines or degrades gracefully
- [ ] Crontab: Sunday 03:00 `run-job profiles`, Sunday 05:00 `run-job updates`; comment updated; does not overlap Mon/Thu 03:00 scrape
- [ ] Dockerfile includes anything new (nothing expected); scraper/README.md and docker/README.md document both jobs, flags, safeguards, and log locations
- [ ] Bash test for run-job additions with stub commands (existing style); `uv run pytest` passes

## Implementation Plan

Edit scraper/docker/run-job, crontab, scraper/partner_scrape/logs.py, READMEs. Follow the existing run-job test.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: as listed in the acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

---
id: '007'
title: Make deploy manual-only and remove the GitHub scheduled scrape
status: done
use-cases:
- SUC-004
depends-on:
- '006'
github-issue: ''
issue: 69-build-the-site-from-the-bucket-and-stop-committing-scraped-data.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Make deploy manual-only and remove the GitHub scheduled scrape

## Description

Stakeholder direction (Eric, 2026-10-07): "disable deploy.yml right now... we are going to maintain the cron job that does the scraping" in a container. No automatic rebuilds until the stakeholder confirms the pipeline works. A site-rebuild cron will be a separate, independently controlled job later. This supersedes ticket 006 (scrape-triggered deploy).

- `.github/workflows/deploy.yml`: remove the `push` trigger; keep `workflow_dispatch` only; no schedule. It still runs `npm run fetch-data` then build (ticket 003 unchanged).
- Delete `.github/workflows/scheduled-run.yml` entirely, including the deploy-dispatch job added in ticket 006.
- `scraper/docs/deploy/scheduled-run.md`: state the GitHub scheduled run is retired and scraping moves to a container cron (see `clasi/issues/70-run-the-scraper-on-a-schedule-from-a-container-cron.md`); the 30-minute timeout risk is moot.
- `README.md` and `scraper/README.md`: drop push-to-deploy and weekly-GitHub-scrape wording; say deploy is manual (Actions -> Deploy -> Run workflow, or `gh workflow run deploy.yml`).
- Leave `build.yml` alone unless it deploys.

Out of scope: the container cron (issue 70) and any rebuild cron.

## Acceptance Criteria

- [x] deploy.yml triggers are `workflow_dispatch` only
- [x] `scheduled-run.yml` is deleted and no live references remain (grep, excluding historical clasi sprint/issue docs)
- [x] scheduled-run.md, README.md and scraper/README.md updated as described
- [x] All edited workflow YAML parses

## Implementation Plan

Files to modify: `.github/workflows/deploy.yml`, `README.md`, `scraper/README.md`, `scraper/docs/deploy/scheduled-run.md`.
Files to delete: `.github/workflows/scheduled-run.yml`.

## Testing

- **Existing tests to run**: `npm run build`
- **New tests to write**: none
- **Verification command**: `python -c "import yaml,sys;[yaml.safe_load(open(f)) for f in sys.argv[1:]]" .github/workflows/*.yml` and `grep -rn scheduled-run --exclude-dir=clasi --exclude-dir=node_modules .`

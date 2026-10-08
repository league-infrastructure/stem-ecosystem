---
id: '006'
title: Scheduled scrape triggers a site deploy
status: done
use-cases:
- SUC-004
depends-on:
- '004'
github-issue: ''
issue: 69-build-the-site-from-the-bucket-and-stop-committing-scraped-data.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Scheduled scrape triggers a site deploy

## Description

After a successful scheduled scrape, trigger deploy.yml so the live site picks up new data without a commit (also helps issue 67). GITHUB_TOKEN pushes do not trigger workflows, so use workflow_dispatch via gh/API with actions: write permission, as a step that runs only on success. Verify deploy.yml's paths-ignore does not matter for dispatch.

## Acceptance Criteria

- [x] Deploy is dispatched only after the scrape step succeeds
- [x] Workflow permissions include actions: write (minimal)
- [x] Concurrency of deploy.yml unaffected
- [x] Documented manual verification via workflow_dispatch of scheduled-run

## Implementation Plan

Files to create/modify: .github/workflows/scheduled-run.yml

## Testing

- **Existing tests to run**: `uv run pytest` (scraper) if scraper touched; `npm run build`
- **New tests to write**: as listed in acceptance criteria
- **Verification command**: `actionlint/yaml check; manual dispatch run`

## Notes

- Implemented as a separate `deploy` job (`needs: scrape`, job-level `actions: write`) dispatching deploy.yml on the default branch. Not run live (cannot execute Actions locally); YAML parse-checked only. Verify via manual dispatch per scraper/docs/deploy/scheduled-run.md.
- Risk: `timeout-minutes: 30` on the scrape job vs ~80 min for a full local scrape. Left unchanged; a timeout fails the job and skips the deploy.

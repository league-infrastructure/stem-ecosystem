---
id: '006'
title: Scheduled scrape triggers a site deploy
status: open
use-cases: [SUC-004]
depends-on: ["004"]
github-issue: ''
issue: 69-build-the-site-from-the-bucket-and-stop-committing-scraped-data.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Scheduled scrape triggers a site deploy

## Description

After a successful scheduled scrape, trigger deploy.yml so the live site picks up new data without a commit (also helps issue 67). GITHUB_TOKEN pushes do not trigger workflows, so use workflow_dispatch via gh/API with actions: write permission, as a step that runs only on success. Verify deploy.yml's paths-ignore does not matter for dispatch.

## Acceptance Criteria

- [ ] Deploy is dispatched only after the scrape step succeeds
- [ ] Workflow permissions include actions: write (minimal)
- [ ] Concurrency of deploy.yml unaffected
- [ ] Documented manual verification via workflow_dispatch of scheduled-run

## Implementation Plan

Files to create/modify: .github/workflows/scheduled-run.yml

## Testing

- **Existing tests to run**: `uv run pytest` (scraper) if scraper touched; `npm run build`
- **New tests to write**: as listed in acceptance criteria
- **Verification command**: `actionlint/yaml check; manual dispatch run`

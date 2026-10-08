---
id: '001'
title: Commit scraper/docker baseline
status: open
use-cases: [SUC-001]
depends-on: []
github-issue: ''
issue: 70-run-the-scraper-on-a-schedule-from-a-container-cron.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Commit scraper/docker baseline

## Description

Commit the currently untracked `scraper/docker/` (Dockerfile, Dockerfile.dockerignore, README.md) as the baseline verified on 2026-10-07, before later tickets change them.

## Acceptance Criteria

- [ ] `scraper/docker/Dockerfile`, `Dockerfile.dockerignore`, `README.md` committed unchanged
- [ ] Only those paths staged (`git add scraper/docker/...`); `src/pages/index.astro`, `clasi/issues/README.md`, `clasi/issues/67-*`, `clasi/issues/68-*` not staged or modified

## Implementation Plan

Plan: `git add` the three explicit paths, commit. No code changes. Test: `git status` shows the unrelated files still unstaged.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: see acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

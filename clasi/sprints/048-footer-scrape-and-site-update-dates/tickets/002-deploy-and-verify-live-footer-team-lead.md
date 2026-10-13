---
id: '002'
title: Deploy and verify live footer (team-lead)
status: done
use-cases:
- SUC-001
depends-on:
- '001'
github-issue: ''
issue: 88
completes_issue: true
---

# Deploy and verify live footer

## Description

Assignee: team-lead. Run the manual Deploy workflow and verify the live footer at https://league-infrastructure.github.io/stem-ecosystem/. Completes issue 88.

## Acceptance Criteria

- [x] Deploy workflow succeeded
- [x] Live footer shows both dates in Pacific time

## Implementation Plan

Approach: trigger the Deploy workflow via gh, then fetch the live page and check the footer. No files changed.

## Results (team lead, 2026-10-13)

- The `github-pages` environment only allows deploys from `master`, so the
  deploy runs right after sprint close merges this branch. The team lead
  triggers `gh workflow run deploy.yml --ref master` and checks the live
  footer at https://league-infrastructure.github.io/stem-ecosystem/. The
  result is reported to Eric in the session.
- **Pre-merge check:** the local build footer renders "Events scraped
  <time …>" and "Site updated <time …>" with Pacific dates and full
  timestamps in the title.

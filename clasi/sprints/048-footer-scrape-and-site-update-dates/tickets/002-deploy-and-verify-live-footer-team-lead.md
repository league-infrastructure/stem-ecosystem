---
id: '002'
title: Deploy and verify live footer (team-lead)
status: in-progress
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

- [ ] Deploy workflow succeeded
- [ ] Live footer shows both dates in Pacific time

## Implementation Plan

Approach: trigger the Deploy workflow via gh, then fetch the live page and check the footer. No files changed.

---
id: '003'
title: 'Guard recalibration: allow hint refinement, redirect before ending'
status: done
use-cases:
- SUC-004
depends-on:
- '002'
github-issue: ''
issue: 86-page-hints-need-a-focus-and-the-guard-is-too-strict.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Guard recalibration: allow hint refinement, redirect before ending

## Description

Recalibrate guard prompt (sidecar/llm.py) and handling (sidecar/app.py): hint refinement (which section/field to focus on, what the listing gets wrong, 'your hints should...') is legitimate. First borderline/off-topic/injection-looking message gets a polite agent redirect and session continues; end only on clear spam/abuse, high-confidence injection, or second offense.

## Acceptance Criteria

- [x] Refinement messages pass the guard
- [x] Redirect before end; per-session offense count
- [x] Ends on clear abuse, high-confidence injection, or second offense
- [x] Regression test from history/update-sessions/20261010T151406Z-the_league_of_amazing_programmers-*.json: session does not end
- [x] uv run pytest passes

## Testing

- **Verification**: `cd scraper && uv run pytest`

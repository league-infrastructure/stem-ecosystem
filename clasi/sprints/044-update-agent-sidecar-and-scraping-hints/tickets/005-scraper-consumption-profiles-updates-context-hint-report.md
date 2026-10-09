---
id: '005'
title: 'Scraper consumption: profiles, updates context, hint report'
status: open
use-cases: [SUC-006]
depends-on: ["001"]
github-issue: ''
issue: 83-update-agent-sidecar-and-scraping-hints.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Scraper consumption: profiles, updates context, hint report

## Description

Scraper reads hints: `profiles` uses page hints (about/contact/other) to override discovery; `updates` passes note/identity to the proposer prompt and counts identity as rebrand evidence only with existing redirect/title evidence; reports/run logs list hints used. Policy untouched.

See architecture-update.md for the design and API contract.

## Acceptance Criteria

- [ ] No hints file means identical behavior to today
- [ ] Hints never set a record field directly
- [ ] Updates report and profiles log show which hints were used
- [ ] Tests for each path
- [ ] Tests pass (`uv run pytest` from scraper/)

## Implementation Plan

Touch `profiles/{job,discover}.py`, `updates/{proposer,job}.py`, report formatting.

## Testing

- **Existing tests to run**: `uv run pytest` from scraper/
- **New tests to write**: fakes only; no real Anthropic/OpenRouter or bucket
- **Verification command**: `uv run pytest`

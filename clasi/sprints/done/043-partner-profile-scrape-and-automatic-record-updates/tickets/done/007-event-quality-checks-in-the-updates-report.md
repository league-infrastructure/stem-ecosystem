---
id: '007'
title: Event-quality checks in the updates report
status: done
use-cases:
- SUC-005
depends-on:
- '006'
github-issue: ''
issue: 76-per-partner-event-quality-checks-in-the-post-scrape-report.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Event-quality checks in the updates report

## Description

`updates/quality.py`: report-only per-partner event-quality checks included in the updates report (issue 76).

## Acceptance Criteria

- [x] Checks from existing scrape output (`data/partners/<slug>/events.json`, `data/opportunities.json`) with no web calls or LLM: non-event titles (member's only, holiday hours, early closure, closed); duplicate/near-duplicate titles in the same slot; date vs link-occurrence mismatch; past events in the current list; implausible age tags (e.g. grades 6-12 on a partner serving ages 0-10 or toddler text); missing/blank/Free cost where text mentions admission or price; recurring sessions collapsed (multiple times in text, one stored)
- [x] Each finding: partner slug, check id, event title/url, short detail; summary count per check
- [x] Appended to the updates report section 'Event quality'; runs in dry-run and real runs; never modifies data
- [x] Unit tests per check with small fixtures

## Implementation Plan

updates/quality.py plus integration in updates/job.py. Inspect actual events.json shape before coding. Note follow-up issues are out of scope.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: as listed in the acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

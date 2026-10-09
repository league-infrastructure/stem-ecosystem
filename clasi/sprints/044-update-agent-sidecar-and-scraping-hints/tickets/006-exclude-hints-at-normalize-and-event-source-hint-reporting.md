---
id: '006'
title: Exclude hints at normalize and event-source hint reporting
status: done
use-cases:
- SUC-006
depends-on:
- '005'
github-issue: ''
issue: 83-update-agent-sidecar-and-scraping-hints.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Exclude hints at normalize and event-source hint reporting

## Description

Normalize drops events matching a partner's exclude hints (substring or `re:` regex) and counts them in the run log; updates report lists page hints with role events/camps/programs as 'add or adjust source' items. Auto-created generic sources are deferred.

See architecture-update.md for the design and API contract.

## Acceptance Criteria

- [x] Confirm normalize hook point in `normalize/run.py` and note it in the ticket (hook: `normalize.run()` filters events by title right after the datetime coercion and before collapse/dedup; partner joined by org name -> slug; `pipeline.run(hint_store=)` builds per-slug matchers and prints `HINT EXCLUDED <slug>: N event(s)...` to the run log)
- [x] Excluded events counted per partner in the run log
- [x] Event-source page hints appear in the updates report
- [x] Tests for match, non-match and regex safety
- [x] Tests pass (`uv run pytest` from scraper/)

## Implementation Plan

Touch `normalize/run.py` (or `partners.py`), `updates/job.py`.

## Testing

- **Existing tests to run**: `uv run pytest` from scraper/
- **New tests to write**: fakes only; no real Anthropic/OpenRouter or bucket
- **Verification command**: `uv run pytest`

## Added requirement: hints fingerprint in updates state

`updates.checks.run_checks(hints_fp=)` folds a hints fingerprint into the per-partner state value (`<snapshot hash>+h:<fp>`; no hints keeps the plain hash), so a hints change re-examines the partner at the next scheduled run. Event-source page reporting was already delivered in 005 and is covered by its tests.

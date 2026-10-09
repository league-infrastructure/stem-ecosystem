---
id: '001'
title: Hint model, validation and archiving HintWriter
status: done
use-cases:
- SUC-002
- SUC-004
depends-on: []
github-issue: ''
issue: 83-update-agent-sidecar-and-scraping-hints.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Hint model, validation and archiving HintWriter

## Description

Create `partner_scrape/hints/`: hint schema, server-side validation, `HintStore` and archiving `HintWriter` (mirrors `PartnerWriter`).

See architecture-update.md for the design and API contract.

## Acceptance Criteria

- [x] Kinds page/exclude/note/identity validated; unknown kinds, oversize text, bad regex and too many hints rejected
- [x] Page URL host must equal or be a subdomain of the entity's website domain(s)
- [x] Identity website accepted only if an injected fetcher shows the record's current website redirects to that host; no private-IP fetches
- [x] `hints/<slug>.json` written private; prior version archived to `history/hints/<slug>/<ts>.json`; line appended to `history/hints/changes.jsonl` with actor `update-agent:<session>`; identical write is a no-op
- [x] Read helper returns empty hints when file absent
- [x] Tests pass (`uv run pytest` from scraper/)

## Implementation Plan

New `hints/{model,validate,store,writer}.py`; tests `tests/hints/` with LocalStore and fake fetcher. Slug checked with existing `check_slug`.

## Testing

- **Existing tests to run**: `uv run pytest` from scraper/
- **New tests to write**: fakes only; no real Anthropic/OpenRouter or bucket
- **Verification command**: `uv run pytest`

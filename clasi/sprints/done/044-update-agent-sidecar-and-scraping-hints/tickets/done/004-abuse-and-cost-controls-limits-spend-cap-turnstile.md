---
id: '004'
title: 'Abuse and cost controls: limits, spend cap, Turnstile'
status: done
use-cases:
- SUC-005
depends-on:
- '002'
github-issue: ''
issue: 83-update-agent-sidecar-and-scraping-hints.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Abuse and cost controls: limits, spend cap, Turnstile

## Description

Add `sidecar/limits`: per-IP and per-listing sliding-window rate limits, turn and message-length caps, persisted daily spend cap, optional Turnstile.

See architecture-update.md for the design and API contract.

## Acceptance Criteria

- [x] 429 with Retry-After when limits exceeded; 413 for long messages; session ends at turn cap
- [x] Daily spend counter persisted per UTC day in the history store, survives restart; new sessions refused with `spend_cap_reached` at cap
- [x] Turnstile enforced only when secret configured, verifier injected (fake in tests)
- [x] All thresholds configurable via env with documented defaults
- [x] Tests pass (`uv run pytest` from scraper/)

## Implementation Plan

Injected clock for tests; price table constant for spend estimate.

## Testing

- **Existing tests to run**: `uv run pytest` from scraper/
- **New tests to write**: fakes only; no real Anthropic/OpenRouter or bucket
- **Verification command**: `uv run pytest`

---
id: '003'
title: Guard and agent with tool-based hint editing
status: done
use-cases:
- SUC-002
- SUC-003
depends-on:
- '002'
github-issue: ''
issue: 83-update-agent-sidecar-and-scraping-hints.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Guard and agent with tool-based hint editing

## Description

Implement `sidecar/llm` (Protocols, Anthropic and fake implementations, optional OpenRouter guard backend default off) and `sidecar/agent` (prompt, context builder, single edit-hints tool).

See architecture-update.md for the design and API contract.

## Acceptance Criteria

- [x] Guard uses `claude-haiku-4-5-20251001` by default; verdict legitimate vs off-topic/spam/abuse/injection/supplying content; non-legitimate ends the session with polite message, email fallback and logged reason
- [x] Agent uses `claude-sonnet-5-5`; edits proposed hints only through the tool; tool calls validated by `hints`; rejections returned to the model and surfaced as notices
- [x] Context: entity record, latest profile snapshot summary, recent scraped events; user text delimited as untrusted
- [x] Token usage returned for spend accounting
- [x] No real network calls in tests
- [x] Tests pass (`uv run pytest` from scraper/)

## Implementation Plan

Reuse Anthropic client patterns from `enrich/llm_client.py` (single model constant per client). Tests with scripted fakes.

## Testing

- **Existing tests to run**: `uv run pytest` from scraper/
- **New tests to write**: fakes only; no real Anthropic/OpenRouter or bucket
- **Verification command**: `uv run pytest`

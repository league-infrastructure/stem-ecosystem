---
id: '004'
title: 'Scraper consumes focus: updates proposer and event enrichment'
status: done
use-cases:
- SUC-005
depends-on:
- '002'
github-issue: ''
issue: 86-page-hints-need-a-focus-and-the-guard-is-too-strict.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Scraper consumes focus: updates proposer and event enrichment

## Description

Pass page-hint focus text plus URL as untrusted context to the updates proposer (alongside notes) and to LLM event enrichment for that partner (ages, grades). Profiles still fetch the page. Focus is never a fact source. Updates and enrichment logs say when a focus hint was used. Files: updates/proposer.py, enrich/*.

## Acceptance Criteria

- [x] Proposer prompt includes focus context, marked untrusted
- [x] Enrichment prompt includes focus context for that partner's events
- [x] Logs record focus-hint use
- [x] Focus not treated as a fact source (test)
- [x] uv run pytest passes

## Testing

- **Verification**: `cd scraper && uv run pytest`

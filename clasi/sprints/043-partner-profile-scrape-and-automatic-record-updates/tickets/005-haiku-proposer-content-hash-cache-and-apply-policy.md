---
id: '005'
title: Haiku proposer, content-hash cache, and apply policy
status: in-progress
use-cases:
- SUC-004
depends-on:
- '004'
github-issue: ''
issue: 75-post-scrape-partner-record-update-check-with-haiku.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Haiku proposer, content-hash cache, and apply policy

## Description

`updates/proposer.py` (Haiku, cached) and `updates/policy.py` (the only gate to the writer) (issue 75 step 2).

## Acceptance Criteria

- [ ] Proposer uses `claude-haiku-4-5-20251001` via the anthropic SDK (follow enrich/llm_client.py patterns: no explicit api_key, JSON-schema output_config), input = cached home/About/Contact text (trimmed) + current record + flags; output = per-field {value, confidence 0-1, reason} and a description in original wording (prompt forbids copying; a similarity check rejects descriptions sharing long verbatim runs with page text)
- [ ] Results cached at `updates/<slug>/<sha256(pages + record + prompt version)>.json` in the scrape-cache store; unchanged content makes zero API calls (test with a counting fake)
- [ ] Fake proposer for tests; tests never hit the network
- [ ] Policy: auto-apply allowlist = name, website, phone, email, location, twitter, facebook, instagram, linkedin, description; logo changes report-only; latitude/longitude, organization_type, id, slug never auto-change
- [ ] Policy: confidence >= 0.8 (configurable); never blank/empty a field; social fields: a dead link may be replaced with the site's current link but never removed unless the site links none for that network, and then it is report-only; resulting record must pass the record validator
- [ ] Policy returns {applied: new record or None, applied_fields, rejected: [(field, reason)]} and is pure

## Implementation Plan

updates/proposer.py, updates/policy.py with tests for each rule. Add to updates/DESIGN.md. Sole path to writer is enforced in ticket 006 (job calls policy output only).

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: as listed in the acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

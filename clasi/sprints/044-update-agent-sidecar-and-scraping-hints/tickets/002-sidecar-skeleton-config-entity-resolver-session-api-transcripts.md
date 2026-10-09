---
id: '002'
title: 'Sidecar skeleton: config, entity resolver, session API, transcripts'
status: open
use-cases: [SUC-001, SUC-005]
depends-on: ["001"]
github-issue: ''
issue: 83-update-agent-sidecar-and-scraping-hints.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sidecar skeleton: config, entity resolver, session API, transcripts

## Description

Add `partner_scrape/sidecar/` skeleton: config from env, Starlette app with CORS and `/healthz`, entity resolver, in-memory sessions, start/get/confirm routes with a fake agent, private transcripts with salted IP hash, error model from the architecture doc. Add `sidecar` extra (starlette, uvicorn) and httpx dev dep via uv.

See architecture-update.md for the design and API contract.

## Acceptance Criteria

- [ ] Routes and error codes match the API contract in architecture-update.md
- [ ] Entity resolution for partner and opportunity; confirm the data source for team/club/place, else `not_found` with fallback email (record decision in ticket)
- [ ] CORS only for configured origins
- [ ] Transcript written each turn to `history/update-sessions/<ts>-<slug>-<id>.json`; IP only as sha256(salt+ip)
- [ ] Confirm writes via HintWriter, idempotent; idle sessions expire (410)
- [ ] Tests pass (`uv run pytest` from scraper/)

## Implementation Plan

Files: `sidecar/{config,app,sessions,resolver,transcripts}.py`, `pyproject.toml`, `uv.lock`. Tests use TestClient, in-memory stores, fake agent.

## Testing

- **Existing tests to run**: `uv run pytest` from scraper/
- **New tests to write**: fakes only; no real Anthropic/OpenRouter or bucket
- **Verification command**: `uv run pytest`

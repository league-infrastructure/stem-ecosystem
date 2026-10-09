---
id: '002'
title: 'Sidecar skeleton: config, entity resolver, session API, transcripts'
status: done
use-cases:
- SUC-001
- SUC-005
depends-on:
- '001'
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

- [x] Routes and error codes match the API contract in architecture-update.md
- [x] Entity resolution for partner and opportunity; confirm the data source for team/club/place, else `not_found` with fallback email (record decision in ticket)
- [x] CORS only for configured origins
- [x] Transcript written each turn to `history/update-sessions/<ts>-<slug>-<id>.json`; IP only as sha256(salt+ip)
- [x] Confirm writes via HintWriter, idempotent; idle sessions expire (410)
- [x] Tests pass (`uv run pytest` from scraper/)

## Implementation Plan

Files: `sidecar/{config,app,sessions,resolver,transcripts}.py`, `pyproject.toml`, `uv.lock`. Tests use TestClient, in-memory stores, fake agent.

## Testing

- **Existing tests to run**: `uv run pytest` from scraper/
- **New tests to write**: fakes only; no real Anthropic/OpenRouter or bucket
- **Verification command**: `uv run pytest`

## Decisions

- **Entity data source (open question 2)**: the published data store (`data/` in the bucket). partner -> `partners/<slug>/partner.json`; opportunity -> `opportunities.json` (`slug`); team/club/place -> `teams.json`/`clubs.json`/`places.json` (`team_id`/`club_id`/`place_id`). Unknown id -> `not_found` with the fallback email. `partner_slug` is derived for opportunities (`partner_id` -> `partners.json`) and places (`related_partner_id`); null for teams/clubs. Hint domains come from the entity website plus partner/organization website.
- Hints are stored at `hints/<entity slug>.json` for every type; slugs of different types share one namespace (collisions judged unlikely: partner slugs use underscores, team/club ids hyphens, opportunity slugs start `https_`).
- Unknown/expired session ids both answer `session_expired` (410), since a restart loses sessions.
- A `guard`-ended session cannot confirm (409); a `turn_cap`-ended one can.
- Sidecar tests `importorskip` starlette/httpx: run with `uv run --extra sidecar pytest`; the default run skips them cleanly.

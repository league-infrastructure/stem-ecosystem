---
id: '044'
title: Update-agent sidecar and scraping hints
status: planning-docs
branch: sprint/044-update-agent-sidecar-and-scraping-hints
use-cases:
- SUC-001
- SUC-002
- SUC-003
- SUC-004
- SUC-005
- SUC-006
- SUC-007
issues:
- 83-update-agent-sidecar-and-scraping-hints.md
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 044: Update-agent sidecar and scraping hints

## Goals

1. A private, versioned **scraping-hint** model (kinds page, exclude, note, identity) stored at `hints/<slug>.json` through an archiving `HintWriter`, validated server-side.
2. A new **update-agent sidecar** HTTP service (Starlette + uvicorn, in the `partner_scrape` package) with a guard model (Haiku) and a tool-using agent (Sonnet) that only ever edits proposed hints.
3. Abuse and cost controls: CORS, rate limits, turn and length caps, persisted daily spend cap, optional Turnstile, salted IP hashing, private transcripts.
4. The scraper consumes hints: `profiles` (page hints), `updates` (note/identity context), normalize (exclude), updates report (events/camps/programs page hints).
5. Deploy the sidecar as a second service of the `stem-ecosystem` swarm stack at `https://updates.jtlapp.net`, verified live, and recorded in league-network.

## Problem

Partners cannot tell us when their listing is wrong. We must not accept facts from a chat (anyone can submit, no identity check), but we do want their help finding where the truth lives on their own website, and what to skip.

## Solution

Issue 83 (Eric's decisions, 2026-10-09; approved as planned). The chat produces hints only; a hint steers where we look or what we skip and can never supply a published fact. Hints apply automatically and take effect at the next scheduled scrape. See `architecture-update.md` for the module design and the HTTP API contract that the site sprint (issue 84) builds against.

## Success Criteria

- Unit tests with fakes only (no Anthropic/OpenRouter calls, no real bucket) cover hint validation, writer archiving, guard routing, agent tool edits, limits, spend cap, API contract, and each scraper consumption point.
- `docker compose config` valid; `check-release` passes.
- `https://updates.jtlapp.net/healthz` is healthy on the swarm and a live smoke conversation produces and confirms a hint file in the bucket.

## Scope

### In Scope

Everything in issue 83: sidecar, hint model/storage, controls, scraper consumption, deployment, league-network record. Decisions made in planning:

- Model IDs: guard `claude-haiku-4-5-20251001`, agent `claude-sonnet-5-5`; OpenRouter guard backend optional, default off.
- Hostname `updates.jtlapp.net`; image `ghcr.io/league-infrastructure/stem-ecosystem-updates`; swarm secret `stem-ecosystem_updates_secrets` (same base64 bundle pattern).
- Single replica; rate-limit counters in memory, daily spend persisted.
- Event-source hints (events/camps/programs): **reported only** in the updates report. Auto-creating a generic source is deferred (see open questions).
- Hints for team/club/place/opportunity are stored under the resolved entity slug; only partner hints are consumed by the scraper this sprint.

### Out of Scope

Site pages and links (issue 84, separate sprint), on-demand re-scrape, identity verification, OpenRouter beyond an optional guard backend, auto-created generic sources.

## Test Strategy

pytest in `scraper/tests/`. LLM clients are Protocol-typed with scripted fakes; storage uses `LocalStore`/in-memory stores (moto only if needed); fetcher for redirect verification is a fake. API tests use Starlette `TestClient`. Deployment verified manually in the final ticket.

## Architecture Notes

New packages `partner_scrape/hints/` (shared model, validation, store, writer, consumption helpers) and `partner_scrape/sidecar/` (service). Dependency direction: sidecar and scraper jobs depend on hints; hints depends on storage and partners. Sidecar deps live in an optional `sidecar` extra so the scraper image does not grow.

## GitHub Issues

None.

## Definition of Ready

- [x] Sprint planning documents are complete (sprint.md, use cases, architecture)
- [x] Architecture review passed
- [x] Stakeholder has approved the sprint plan (Eric, 2026-10-09; recorded by team lead)

## Tickets

| # | Title | Depends On |
|---|-------|------------|
| 001 | Hint model, validation and archiving HintWriter | none |
| 002 | Sidecar skeleton: config, entity resolver, session API, transcripts | 001 |
| 003 | Guard and agent with tool-based hint editing | 002 |
| 004 | Abuse and cost controls: limits, spend cap, Turnstile | 002 |
| 005 | Scraper consumption: profiles, updates context, hint report | 001 |
| 006 | Exclude hints at normalize and event-source hint reporting | 005 |
| 007 | Sidecar Dockerfile, compose service and docs | 003, 004 |
| 008 | Deploy to the swarm, verify live, record in league-network | 006, 007 |

Tickets execute serially in the order listed.

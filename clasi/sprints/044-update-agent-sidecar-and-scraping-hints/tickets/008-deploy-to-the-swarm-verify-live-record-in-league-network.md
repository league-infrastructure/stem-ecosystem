---
id: 008
title: Deploy to the swarm, verify live, record in league-network
status: open
use-cases: [SUC-007]
depends-on: ["006", "007"]
github-issue: ''
issue: 83-update-agent-sidecar-and-scraping-hints.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Deploy to the swarm, verify live, record in league-network

## Description

Operational ticket with the team lead: create the swarm secret (team lead pipes keys), build and push amd64 images, redeploy the stack, verify, and record in league-network.

See architecture-update.md for the design and API contract.

## Acceptance Criteria

- [ ] Secret `stem-ecosystem_updates_secrets` created on the swarm
- [ ] amd64 images built and pushed; `docker --context swarm1 stack deploy` of stem-ecosystem succeeds; service healthy
- [ ] `https://updates.jtlapp.net/healthz` returns 200 over TLS; `check-release --live` passes
- [ ] Live smoke conversation: session, message, confirm produces `hints/<slug>.json` in the bucket and a transcript; test hint then removed or reverted
- [ ] Recorded in league-network `services/` and `sites/` per its AGENTS.md (and host change log if touched), committed there
- [ ] Tests pass (`uv run pytest` from scraper/)

## Implementation Plan

No code expected; fix-ups found during deploy go in this ticket. Do not print secrets.

## Testing

- **Existing tests to run**: `uv run pytest` from scraper/
- **New tests to write**: fakes only; no real Anthropic/OpenRouter or bucket
- **Verification command**: `uv run pytest`

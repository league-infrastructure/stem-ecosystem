---
id: 008
title: Deploy to the swarm, verify live, record in league-network
status: done
use-cases:
- SUC-007
depends-on:
- '006'
- '007'
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

- [x] Secret `stem-ecosystem_updates_secrets` created on the swarm
- [x] amd64 images built and pushed; `docker --context swarm1 stack deploy` of stem-ecosystem succeeds; service healthy
- [x] `https://updates.jtlapp.net/healthz` returns 200 over TLS; `check-release --live` passes
- [x] Live smoke conversation: session, message, confirm produces `hints/<slug>.json` in the bucket and a transcript; test hint then removed or reverted
- [x] Recorded in league-network `services/` and `sites/` per its AGENTS.md (and host change log if touched), committed there
- [x] Tests pass (`uv run pytest` from scraper/)

## Implementation Plan

No code expected; fix-ups found during deploy go in this ticket. Do not print secrets.

## Testing

- **Existing tests to run**: `uv run pytest` from scraper/
- **New tests to write**: fakes only; no real Anthropic/OpenRouter or bucket
- **Verification command**: `uv run pytest`

## Results (team lead, 2026-10-09)

- **Secret:** created `stem-ecosystem_updates_secrets` with
  `make-secrets.sh --updates` plus a random `IP_HASH_SALT`, piped straight
  in, so nothing was displayed or written.
- **Images:** `stem-ecosystem-scraper` and `stem-ecosystem-updates`
  0.20261009.7 (linux/amd64) were pushed. The updates package was created
  internal and Eric made it public.
- **Deploy:** `check-release --tag v0.20261009.7 --live` gave 0 errors (the
  known tmpfs warning). `TAG=0.20261009.7 stack deploy` was run, and both
  services are running.
- **Live checks:**
  - `https://updates.jtlapp.net/healthz` returns 200.
  - A CMOD session proposed exclude hints for "Only Hours" and "Holiday
    Hours". Confirm returned `saved:true` and
    `effective: next scheduled scrape`.
  - `hints/san_diego_children_s_discovery_museum.json` returns 403
    publicly, and `history/hints/changes.jsonl` has an actor
    `update-agent:<id>` line.
  - The two transcripts and the spend file are present.
  - A prompt-injection session was ended by the guard (`ended_reason: guard`)
    and later messages return 409.
  - A disallowed origin gets no CORS header.
- **league-network:** recorded in commit f8b2b90 (sites/updates.jtlapp.net,
  the sites table and the service change log). That commit also swept in one
  pre-existing uncommitted row, `brt.jtlapp.net`, from another session's
  work in the sites table.

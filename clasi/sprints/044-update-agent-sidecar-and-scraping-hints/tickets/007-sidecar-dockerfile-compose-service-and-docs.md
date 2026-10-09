---
id: '007'
title: Sidecar Dockerfile, compose service and docs
status: open
use-cases: [SUC-007]
depends-on: ["003", "004"]
github-issue: ''
issue: 83-update-agent-sidecar-and-scraping-hints.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sidecar Dockerfile, compose service and docs

## Description

Add `scraper/docker/Dockerfile.sidecar` (slim Python, uv, non-root, uvicorn on 8000, HEALTHCHECK), a second `updates` service in root `docker-compose.yml` per releasing.md, secrets bundle docs and `make-secrets`/`load-secrets` support for the updates bundle.

See architecture-update.md for the design and API contract.

## Acceptance Criteria

- [ ] Compose: image `ghcr.io/league-infrastructure/stem-ecosystem-updates:${TAG:-latest}`, caddy external network, deploy labels `caddy: updates.jtlapp.net` and `caddy.reverse_proxy: "{{upstreams 8000}}"`, healthcheck, no ports, secret `stem-ecosystem_updates_secrets` declared external
- [ ] `docker compose config` valid and `check-release` file checks pass
- [ ] Image builds locally and /healthz responds
- [ ] scraper/docker/README.md and scraper/README.md document env vars, secrets keys and ops
- [ ] Tests pass (`uv run pytest` from scraper/)

## Implementation Plan

Files: `scraper/docker/Dockerfile.sidecar`, `docker-compose.yml`, `scraper/docker/make-secrets.sh`, docs.

## Testing

- **Existing tests to run**: `uv run pytest` from scraper/
- **New tests to write**: fakes only; no real Anthropic/OpenRouter or bucket
- **Verification command**: `uv run pytest`

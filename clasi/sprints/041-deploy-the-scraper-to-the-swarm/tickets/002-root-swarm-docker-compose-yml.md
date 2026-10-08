---
id: "002"
title: "Root swarm docker-compose.yml"
status: open
use-cases: [SUC-002]
depends-on: ["001"]
github-issue: ""
issue: "71"
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Root swarm docker-compose.yml

## Description

Add root `docker-compose.yml` as the swarm stack file: `x-league: stack: stem-ecosystem`; one service `scraper`; image `ghcr.io/league-infrastructure/stem-ecosystem-scraper:${TAG:-latest}`; `build:` context `.` dockerfile `scraper/docker/Dockerfile`; external secret `stem-ecosystem_scraper_secrets` mounted with `SCRAPER_SECRETS_FILE` pointing at it; tmpfs `/dev/shm` ~1g; healthcheck confirming supercronic is alive (e.g. pgrep); `deploy.restart_policy`; memory limit/reservation. No ports, caddy label/network, `container_name`, or `restart`.

## Acceptance Criteria

- [ ] `docker compose config` succeeds
- [ ] `~/proj/league/infrastructure/league-network/scripts/check-release . -v` reports no errors
- [ ] Local run of the image with a fake secret file (native arch; other arch if emulation available) starts the scheduler and the healthcheck passes
- [ ] No real secrets used or printed

## Implementation Plan

Files: `docker-compose.yml`. Use the existing Dockerfile unchanged unless the healthcheck needs a tool missing from the image.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: none (config validation and local run)
- **Verification command**: `docker compose config && ~/proj/league/infrastructure/league-network/scripts/check-release . -v`

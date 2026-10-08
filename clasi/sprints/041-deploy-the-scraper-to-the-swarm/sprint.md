---
id: '041'
title: Deploy the scraper to the swarm
status: planning-docs
branch: sprint/041-deploy-the-scraper-to-the-swarm
use-cases: [SUC-001, SUC-002, SUC-003]
issues: ['71']
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 041: Deploy the scraper to the swarm

## Goals

Run the sprint-040 scraper container (supercronic schedule, `run-job`) on
the League docker swarm, following league-network's `releasing.md`.

## Problem

The scraper image only runs where an operator starts it by hand. The repo
has no root compose file (`check-release` reports one error), the secrets
loader reads only an environment variable (swarm secrets are files), and
there is no documented deploy procedure.

## Solution

Stakeholder decisions (Eric, 2026-10-08, approved): public ghcr image,
swarm secret, manual stack deploy.

- `load-secrets` also reads the bundle from a file (`SCRAPER_SECRETS_FILE`).
- A root `docker-compose.yml` defines stack `stem-ecosystem` with one
  `scraper` service and the external secret `stem-ecosystem_scraper_secrets`.
- `scraper/docker/README.md` documents the swarm deploy steps.
- The team lead performs the live operations (below).

## Success Criteria

- `check-release . -v` passes (and `--live` once the secret exists).
- The scraper task runs on the swarm, logs show the schedule, and a manual
  `run-job scrape --source <one> --dry-run --no-enrich` succeeds.

## Scope

### In Scope

- `load-secrets` file support with tests (fake values only).
- Root swarm `docker-compose.yml`.
- README swarm-deploy section.
- Post-ticket live deploy (team lead).

### Out of Scope

- GitHub build-on-release workflow (waits for league-network `templates/release.yml`).
- Any rebuild trigger on the site; `deploy.yml` stays manual.
- Changes to the `partner_scrape` package.

## Test Strategy

Unit tests for `load-secrets` file mode (fake values, bad path, empty file,
precedence). `docker compose config` and `check-release . -v` for the
compose file. Local run of the image (native arch, and the other arch if
emulation is available) with a fake secret file. Live verification after
deploy.

## Architecture Notes

See `architecture-update.md`. Image is built `--platform linux/amd64`
(swarm nodes are x86_64; Eric's Mac is arm64). Chromium needs `/dev/shm`;
swarm has no `--ipc=host`, so a ~1 GB tmpfs is mounted.

## GitHub Issues

None. Source: `clasi/issues/71-deploy-the-scraper-container-to-the-docker-swarm.md`.

## Definition of Ready

Before tickets can be created, all of the following must be true:

- [x] Sprint planning documents are complete (sprint.md, use cases, architecture)
- [x] Architecture review passed
- [x] Stakeholder has approved the sprint plan (Eric, 2026-10-08, in conversation)

## Tickets

| # | Title | Depends On |
|---|-------|------------|
| 001 | load-secrets file support | none |
| 002 | Root swarm docker-compose.yml | 001 |
| 003 | Swarm deploy docs in docker README | 002 |

Tickets execute serially in the order listed.

## Post-ticket deploy checklist (team lead, not programmer tickets)

These touch production and real secrets; agents never read or print secret values.

1. `docker build --platform linux/amd64` and push
   `ghcr.io/league-infrastructure/stem-ecosystem-scraper:<version>` (version from the
   `v<major>.<YYYYMMDD>.<n>` tag, without the `v`) and `:latest`.
2. Make the package public and link it to the repo.
3. Create the secret by pipe only:
   `make-secrets.sh | docker --context swarm1 secret create stem-ecosystem_scraper_secrets -`.
4. `check-release . -v --live`.
5. `TAG=<version> docker --context swarm1 stack deploy --with-registry-auth -c docker-compose.yml stem-ecosystem`.
6. Verify: task running, logs show the schedule, manual `run-job scrape --source <one> --dry-run --no-enrich`.
7. Add a service record in league-network (per its AGENTS.md) and commit it there.

---
id: '040'
title: Scraper container with built-in cron
status: done
branch: sprint/040-scraper-container-with-built-in-cron
use-cases:
- SUC-001
- SUC-002
- SUC-003
- SUC-004
issues:
- 70-run-the-scraper-on-a-schedule-from-a-container-cron.md
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 040: Scraper container with built-in cron

## Goals

Turn the one-shot `partner-scrape` Docker image into a long-running
container that runs the scraper on a schedule by itself, with secrets
supplied as a single base64 environment variable. The image must run
anywhere with `docker run -d`.

Source issue: `clasi/issues/70-run-the-scraper-on-a-schedule-from-a-container-cron.md`.

## Problem

GitHub Actions scheduling was dropped (no secrets, a 30 min timeout against
an ~80 min scrape, false-success exit status). The image from sprint 039
only does a single run and expects a host-side `.env` file.

## Solution

- Run `supercronic` (static binary, logs to stdout, honors `CRON_TZ`) as the
  container's main process, driven by a crontab baked into the image.
- A `run-job` wrapper runs one named job (`scrape`, `teams`, `directory`),
  checks its required secrets, and prints timestamped start/success/failure
  lines. It is used by both cron and by hand.
- An entrypoint decodes `SCRAPER_SECRETS_B64` (base64 of `KEY=value` lines)
  and exports the variables before the scheduler starts, so every job
  inherits them. A host helper `make-secrets.sh` builds the bundle from the
  repo-root `.env`, selecting only the needed keys, never echoing values.

Schedule (America/Los_Angeles):

| Job | Command | When |
|---|---|---|
| scrape | `partner-scrape` (scrape, enrich, normalize, export) | Mon and Thu 03:00 |
| teams | `partner-scrape teams` | Wed 03:00 |
| directory | `partner-scrape directory` | Sat 03:00 |

Secrets per job (verified from code):

| Job | Required | Notes |
|---|---|---|
| scrape | DO_SPACES_ACCESS_KEY, DO_SPACES_SECRET_KEY, ANTHROPIC_API_KEY, LEAGUESYNC_API_KEY | LeagueSync source is active (`leaguesync.toml`, `jointheleague.toml`); enrichment uses Anthropic |
| teams | DO_SPACES_ACCESS_KEY, DO_SPACES_SECRET_KEY, ANTHROPIC_API_KEY, TBA_KEY | sponsor and description LLM extraction; FRC via TBA; ROBOTEVENTS_KEY optional (not provisioned, VEX source fails as today) |
| directory | DO_SPACES_ACCESS_KEY, DO_SPACES_SECRET_KEY | static rosters only; bucket output |

The bundle holds the union: DO_SPACES_ACCESS_KEY, DO_SPACES_SECRET_KEY,
ANTHROPIC_API_KEY, LEAGUESYNC_API_KEY, TBA_KEY, plus ROBOTEVENTS_KEY if
present in `.env`.

## Success Criteria

- `docker run -d -e SCRAPER_SECRETS_B64=... partner-scrape` starts, logs the
  schedule, and fires jobs at the scheduled times with secrets visible.
- `docker exec <c> run-job scrape|teams|directory` and
  `docker run --rm partner-scrape run-job <job>` work and exit with the job's status.
- Logs show timestamped START / SUCCESS / FAILURE lines; no secret values.
- Old one-shot usage (`docker run ... partner-scrape --dry-run ...`,
  `... teams`) still works.

## Scope

### In Scope

- Commit existing `scraper/docker/` as baseline.
- `load-secrets`, `make-secrets.sh`, `run-job`, `entrypoint.sh`, crontab,
  Dockerfile changes (supercronic, tzdata check), README.
- pytest coverage of the shell scripts (run without Docker, using a fake
  `partner-scrape`) plus an image-level smoke check.

### Out of Scope

- Host-specific deployment, registry, auto-update.
- Overlap locking, notifications.
- Runtime roster fetch (roster stays baked from `src/data/partners.json`).
- Site rebuild/deploy trigger; ROBOTEVENTS_KEY provisioning.
- Uncommitted unrelated files: `src/pages/index.astro`, `clasi/issues/README.md`,
  `clasi/issues/67-*`, `clasi/issues/68-*` (never stage or modify; stage specific paths only).

## Test Strategy

Shell scripts are tested from `scraper/tests/test_docker_scripts.py` via
subprocess with a stub `partner-scrape` on PATH (secret decoding, quoting,
missing-key failure, no value leakage, exit-code propagation, log lines,
entrypoint dispatch). Final ticket builds the image and runs a decode/env
check, `run-job` one-shot with `--dry-run --no-enrich --source ...`, and
confirms supercronic sees the crontab and secrets.

## Architecture Notes

See `architecture-update.md`. Decision: supercronic over system cron
(non-root, stdout logging, env inheritance, no daemon/syslog setup).

## GitHub Issues

None.

## Definition of Ready

Before tickets can be created, all of the following must be true:

- [x] Sprint planning documents are complete (sprint.md, use cases, architecture)
- [x] Architecture review passed
- [x] Stakeholder has approved the sprint plan

## Tickets

| # | Title | Depends On |
|---|-------|------------|
| 001 | Commit scraper/docker baseline | none |
| 002 | Secrets bundle: load-secrets and make-secrets.sh | 001 |
| 003 | run-job wrapper with preflight and result logging | 002 |
| 004 | Scheduler: crontab, entrypoint and Dockerfile with supercronic | 003 |
| 005 | README rewrite and end-to-end image verification | 004 |

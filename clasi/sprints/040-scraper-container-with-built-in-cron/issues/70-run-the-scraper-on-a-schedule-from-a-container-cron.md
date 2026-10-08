---
status: in-progress
related: clasi/sprints/039-build-the-site-from-the-bucket
sprint: '040'
tickets:
- 040-001
- 040-002
- 040-003
- 040-004
- 040-005
---

# Run the scraper on a schedule from a container with its own cron

## Description

Stakeholder direction (Eric, 2026-10-07): the scheduled scrape should not
run in GitHub Actions. Instead, the scraper's Docker image should contain a
cron schedule and run the scrape on a regular basis. Sprint 039 retires the
GitHub `scheduled-run.yml`.

Why GitHub Actions was dropped:

- The one scheduled run in this repo (2026-10-05) crashed at startup:
  "DO_SPACES_ACCESS_KEY, DO_SPACES_SECRET_KEY not set". The repo has no
  Actions secrets.
- That run still reported success, because the step piped the scraper
  through `tee` without `pipefail`.
- The job had `timeout-minutes: 30`, but a full scrape takes about 80
  minutes (2026-10-07 Docker run, mostly LLM enrichment).

Starting point: `scraper/docker/Dockerfile` (one-shot image, built from the
repo root) was verified on 2026-10-07. It runs a full scrape against the
`jtl-stem-ecosystem-scrape` bucket with `--env-file .env`.

## Scope

- Add a cron inside the container. It should run the full scrape (the
  default command) on a schedule, plus `teams` and `directory`, which
  publish `teams.json`, `places.json`, `clubs.json` and `offerings.json`.
  Their order and frequency are to be decided.
- The container should be long-running and keep its secrets from runtime
  env only, never baked into the image. Logging should be visible via
  `docker logs`.
- A run must not overlap a previous one that is still going (a lock).
- Failures should be visible: a non-zero exit, a clear log line, and maybe
  a notification.
- Out of scope: rebuilding the site after a scrape. That will be a
  **separate**, independently controlled job, added only once the
  stakeholder confirms the scraping works. `deploy.yml` is manual-only
  until then.

## Open questions

- Where the container runs: a DO droplet, an existing server, App
  Platform, or something else.
- The schedule: weekly, as GitHub had it, or more often.
- Image registry, if the host pulls the image rather than building it.

## References

- `scraper/docker/Dockerfile`, `scraper/docker/README.md`
- Sprint 039: `clasi/sprints/039-build-the-site-from-the-bucket/`

---
sprint: '040'
status: done
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Architecture Update -- Sprint 040: Scraper container with built-in cron

## What Changed

Adds a container runtime layer under `scraper/docker/`; no change to the
`partner_scrape` Python package.

```mermaid
graph LR
  Op[Operator] -->|SCRAPER_SECRETS_B64| EP[entrypoint.sh]
  Mk[make-secrets.sh] -.builds bundle from .env.-> Op
  EP -->|sources| LS[load-secrets]
  EP -->|exec| SC[supercronic + crontab]
  SC -->|run-job X| RJ[run-job]
  Op -->|docker exec run-job X| RJ
  RJ -->|sources| LS
  RJ -->|invokes| CLI[partner-scrape CLI]
  CLI --> B[(Spaces bucket)]
```

Modules (all in `scraper/docker/`):

- `load-secrets` -- decodes the secrets bundle into exported env vars (boundary: parsing only; knows nothing about jobs).
- `make-secrets.sh` -- builds the bundle on the host from `.env` for a fixed key list (boundary: host-side only, not in the image's runtime path).
- `run-job` -- runs one named job with required-secret preflight and timestamped result logging (owns the job-to-command and job-to-secrets mapping).
- `crontab` -- the schedule (data only).
- `entrypoint.sh` -- dispatch: no args/`cron` loads secrets and execs supercronic; `run-job` execs the wrapper; anything else is passed to `partner-scrape` (legacy one-shot).
- `Dockerfile` -- adds a checksum-pinned supercronic (amd64/arm64), tzdata, copies the scripts, sets `TZ=America/Los_Angeles`, `ENTRYPOINT ["entrypoint.sh"]`.

Dependencies are acyclic: entrypoint -> load-secrets, supercronic -> run-job -> load-secrets, partner-scrape.

## Why

Issue 70 and the 2026-10-07 stakeholder decisions: self-contained scheduling, runs anywhere, secrets only from runtime env, failures visible in `docker logs`.

## Impact on Existing Components

- Image default behaviour changes: no args now means "run the scheduler", not "run a scrape". Arguments starting with `-` or a CLI subcommand still go to `partner-scrape`, preserving documented one-shot use.
- `partner_scrape` code, tests, and `deploy.yml` untouched.
- README updated.

## Migration Concerns

None for data. Operators previously using `--env-file .env` can keep doing so for one-shots (individual variables still work); the bundle is only required for the cron mode, and individually set env vars take precedence over bundle values.

## Design Rationale

**Decision: supercronic instead of system cron.** Context: container needs cron as non-root, logs to docker logs, and children must see secrets. Alternatives: Debian `cron` (needs root, drops the environment so secrets must be dumped into /etc/environment or crontab, logs to syslog/files), a sleep-loop script (reinvents scheduling, no TZ handling), Ofelia/host cron (needs host config, violates "runs anywhere"). Why: supercronic is a static binary, runs as pwuser, streams job output to stdout/stderr, honors `CRON_TZ`, and passes its own environment to jobs, so exporting before `exec supercronic` is sufficient. Consequences: one extra pinned binary to bump; checksum verified at build.

**Decision: secrets decoded in a shell script, not Python.** The values must exist in the environment before the scheduler starts and for `docker exec`; a sourced POSIX-ish script serves both. Parsing is line-based with a key-name allowlist regex and no `eval`.

**Decision: no lock.** Per stakeholder: runs are infrequent; schedule spaces the jobs days apart (an ~80 min scrape cannot reach the next job). supercronic would simply start the next run if one overran.

## Open Questions

- Confirm supercronic honors `CRON_TZ` in the crontab file with the pinned version (ticket 004 verifies; fallback is `TZ` env).
- Confirm tzdata present in the Playwright noble image (ticket 004 verifies; install if absent).

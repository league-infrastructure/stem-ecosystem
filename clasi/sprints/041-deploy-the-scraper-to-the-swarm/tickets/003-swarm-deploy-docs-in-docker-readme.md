---
id: "003"
title: "Swarm deploy docs in docker README"
status: open
use-cases: [SUC-003]
depends-on: ["002"]
github-issue: ""
issue: "71"
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Swarm deploy docs in docker README

## Description

Add a swarm deploy section to `scraper/docker/README.md`: build `--platform linux/amd64`, push to ghcr, make package public and link to repo, create the secret via pipe (`make-secrets.sh | docker --context swarm1 secret create stem-ecosystem_scraper_secrets -`), `check-release --live`, `TAG=<version> docker --context swarm1 stack deploy --with-registry-auth -c docker-compose.yml stem-ecosystem`, verify (task, logs, `run-job scrape --source <one> --dry-run --no-enrich`), update/rotate procedure.

## Acceptance Criteria

- [ ] All steps present and in order
- [ ] No real secret values
- [ ] Notes that secrets are immutable (rotate by new name/version)

## Implementation Plan

Files: `scraper/docker/README.md` only.

## Testing

- **Existing tests to run**: none
- **New tests to write**: none
- **Verification command**: review README

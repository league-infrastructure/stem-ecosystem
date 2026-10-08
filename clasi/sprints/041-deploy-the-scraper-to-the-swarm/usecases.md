---
status: draft
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 041 Use Cases

## SUC-001: Container reads its secrets from a swarm secret file
Parent: issue 71

- **Actor**: Scraper container in a swarm task
- **Preconditions**: `SCRAPER_SECRETS_FILE` points at a mounted secret (`/run/secrets/...`) holding the base64 bundle.
- **Main Flow**:
  1. entrypoint or `run-job` sources `load-secrets`.
  2. The bundle is read from the file and exported as env vars.
- **Postconditions**: Same variables as the env-var path; env-var mode (`SCRAPER_SECRETS_B64`) still works for plain `docker run`.
- **Acceptance Criteria**:
  - [ ] File mode decodes identically to env mode
  - [ ] Missing/unreadable file is an error that never prints values
  - [ ] Already-set env vars still win

## SUC-002: Operator deploys the scraper as a swarm stack
Parent: issue 71

- **Actor**: Operator (team lead)
- **Preconditions**: Public ghcr image pushed; external secret created.
- **Main Flow**:
  1. `check-release . -v --live` passes.
  2. `stack deploy` with `TAG`.
  3. The scheduler task starts and passes its healthcheck.
- **Postconditions**: One `scraper` task runs on the swarm; Chromium has 1 GB `/dev/shm`.
- **Acceptance Criteria**:
  - [ ] Compose has no ports, caddy label/network, container_name, or restart key
  - [ ] Healthcheck confirms supercronic is alive

## SUC-003: Operator follows documented deploy and update steps
Parent: issue 71

- **Actor**: Operator
- **Main Flow**: Follow the README: build amd64, push, make public, create secret, deploy, verify, update.
- **Acceptance Criteria**:
  - [ ] README steps are complete and contain no real secret values

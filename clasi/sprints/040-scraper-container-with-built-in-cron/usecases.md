---
status: draft
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 040 Use Cases

## SUC-001: Container runs scheduled scrapes unattended
Parent: issue 70

- **Actor**: Operator (starts the container once); cron inside it
- **Preconditions**: Image built; `SCRAPER_SECRETS_B64` supplied
- **Main Flow**:
  1. Operator runs `docker run -d --ipc=host -e SCRAPER_SECRETS_B64=... partner-scrape`.
  2. Entrypoint decodes and exports secrets, then starts supercronic.
  3. At the scheduled times supercronic runs `run-job scrape|teams|directory`.
- **Postconditions**: Bucket `data/` refreshed twice a week (opportunities) and weekly (teams, directory)
- **Acceptance Criteria**:
  - [ ] Crontab: scrape Mon+Thu 03:00, teams Wed 03:00, directory Sat 03:00, America/Los_Angeles
  - [ ] Jobs see the secrets (inherited from the pre-scheduler environment)
  - [ ] Container keeps running after a job fails

## SUC-002: Operator supplies secrets as one variable
Parent: issue 70

- **Actor**: Operator
- **Preconditions**: Repo-root `.env` assembled by dotconfig
- **Main Flow**:
  1. Operator runs `scraper/docker/make-secrets.sh` and gets a base64 string.
  2. Operator passes it as `SCRAPER_SECRETS_B64`.
  3. Container decodes it at startup.
- **Postconditions**: Only the needed keys are in the container; none in the image or logs
- **Acceptance Criteria**:
  - [ ] Helper selects only the needed keys and prints no values to the terminal except the bundle on stdout
  - [ ] Decoder handles quoted values and ignores comments/blank lines
  - [ ] Missing or malformed bundle gives a clear error naming missing variables, never values

## SUC-003: Operator triggers a job by hand
Parent: issue 70

- **Actor**: Operator
- **Main Flow**: `docker exec <c> run-job teams` or `docker run --rm -e SCRAPER_SECRETS_B64=... partner-scrape run-job scrape --dry-run --no-enrich`.
- **Postconditions**: Job runs with same env/logging as the scheduled one; exit status is the job's
- **Acceptance Criteria**:
  - [ ] Extra args pass through to `partner-scrape`
  - [ ] Unknown job name is rejected with usage
  - [ ] Legacy one-shot invocation (`partner-scrape` args directly) still works

## SUC-004: Operator sees run outcome in container logs
Parent: issue 70

- **Actor**: Operator
- **Main Flow**: `docker logs <c>` shows timestamped lines per job.
- **Acceptance Criteria**:
  - [ ] `START job=... ` and `SUCCESS`/`FAILURE job=... exit=N duration=Ns` lines with UTC ISO timestamps
  - [ ] Missing required secrets produce a FAILURE line naming the variables
  - [ ] Secret values never logged

---
id: '001'
title: 'Run logs: tee and upload run-job output'
status: open
use-cases: [SUC-005]
depends-on: []
github-issue: "72-capture-every-scraper-run-to-a-logs-directory-in-the-bucket.md"
issue: 72-capture-every-scraper-run-to-a-logs-directory-in-the-bucket.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Run logs: tee and upload run-job output

## Description

Make every `run-job` run (scheduled or manual) tee full stdout+stderr to a temp file and, on exit (success or failure), upload it to `logs/<type>/<UTC ts>-<job>.log` in the bucket, and append one line to `logs/index.jsonl` (job, start, end, exit code, duration, log path, headline counts when parseable: sources, events written, errors). Types: scrape, teams, directory (profiles/updates reserved). START/SUCCESS/FAILURE lines still reach `docker logs`.

## Acceptance Criteria

- [ ] Log object and index line produced for each job, including failed and preflight-failed runs
- [ ] Upload failure is reported on stdout and never changes the job exit code
- [ ] logs/ objects are written private (no public-read ACL); test asserts it
- [ ] No secret values in logs or index (test with a sentinel secret in the environment)
- [ ] Index append is read-modify-write safe enough for serial jobs (jobs are days apart); document it
- [ ] `scraper/docker/README.md` documents logs/

## Implementation Plan

READ FIRST: `scraper/partner_scrape/storage.py` (S3Store `public_read` defaults False; only the data store from `config.py` sets it True) and `config.py` `_store_for`. Add a small python helper `partner_scrape/logs.py` (upload_log, append_index) using the cache-style private store (a new `logs` store accessor in config.py, or the bucket root with public_read=False); invoke it from `scraper/docker/run-job` via `partner-scrape logs upload ...` or `python -m`. Tests: pytest for the helper (LocalStore + fake S3 client asserting no ACL kwarg), bash test with a stub `partner-scrape` for run-job exit-code behavior. Never read the real .env.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest` (and `npm test`/node tests for ticket 006)
- **New tests to write**: as listed in the plan
- **Verification command**: `cd scraper && uv run pytest`

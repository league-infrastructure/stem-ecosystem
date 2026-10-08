---
id: '002'
title: 'Secrets bundle: load-secrets and make-secrets.sh'
status: done
use-cases:
- SUC-002
depends-on:
- '001'
github-issue: ''
issue: 70-run-the-scraper-on-a-schedule-from-a-container-cron.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Secrets bundle: load-secrets and make-secrets.sh

## Description

Add `scraper/docker/load-secrets` (sourced script that decodes `SCRAPER_SECRETS_B64`, or the var named by `SCRAPER_SECRETS_VAR`, into exported env vars) and host helper `scraper/docker/make-secrets.sh` (builds the bundle from the repo-root `.env`).

## Acceptance Criteria

- [x] load-secrets: base64-decodes the bundle; parses `KEY=value` lines; ignores blanks/comments; strips matching surrounding single/double quotes; accepts only `[A-Za-z_][A-Za-z0-9_]*` keys; no `eval`; already-set env vars win
- [x] Malformed base64 or bad line gives a clear error that never prints values; unset bundle is a no-op
- [x] make-secrets.sh [path-to-.env] selects only DO_SPACES_ACCESS_KEY, DO_SPACES_SECRET_KEY, ANTHROPIC_API_KEY, LEAGUESYNC_API_KEY, TBA_KEY, ROBOTEVENTS_KEY (optional); single-line base64 on stdout; warnings on stderr name missing keys only; never echoes values
- [x] Scripts are executable; shellcheck-clean where available
- [x] pytest `scraper/tests/test_docker_scripts.py` covers round trip, quotes, comments, special characters (spaces, `=`, `$`), bad input, no leakage in stdout/stderr

## Implementation Plan

Files: scraper/docker/load-secrets, scraper/docker/make-secrets.sh, scraper/tests/test_docker_scripts.py (subprocess with bash). Docs deferred to ticket 005.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: see acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

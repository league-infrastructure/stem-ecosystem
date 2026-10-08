---
id: "001"
title: "load-secrets file support"
status: open
use-cases: [SUC-001]
depends-on: []
github-issue: ""
issue: "71"
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# load-secrets file support

## Description

Extend `scraper/docker/load-secrets` so the base64 bundle can come from a file named by `SCRAPER_SECRETS_FILE` (a swarm secret at `/run/secrets/...`), falling back to the existing env var (`SCRAPER_SECRETS_B64` / `SCRAPER_SECRETS_VAR`). Never print values.

## Acceptance Criteria

- [ ] File mode decodes identically to env mode
- [ ] Missing or unreadable file gives an error without printing values
- [ ] Empty file is a no-op; already-set env vars still win
- [ ] Env-var mode unchanged
- [ ] Header comment in load-secrets documents the new variable

## Implementation Plan

Files: `scraper/docker/load-secrets` (read file content into the bundle before the existing decode path), existing tests for load-secrets (find under `scraper/tests`), add cases with fake values only.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: file mode, missing file, empty file, precedence over env bundle, env precedence
- **Verification command**: `cd scraper && uv run pytest`

---
id: '006'
title: 'updates job: apply via writer, cap, dry-run, report'
status: open
use-cases:
- SUC-003
- SUC-004
depends-on: ['005']
github-issue: ''
issue: 75-post-scrape-partner-record-update-check-with-haiku.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# updates job: apply via writer, cap, dry-run, report

## Description

`partner-scrape updates`: orchestrate check, propose, policy, apply via `PartnerWriter.put_record(actor="haiku")`, consolidate, and report (issue 75).

## Acceptance Criteria

- [ ] Flags: `--dry-run` (report only, no record writes, no consolidate; Haiku still called and cached), `--no-llm` (flags only), `--max-changes N` (default 20), `--slug S`, `--all`
- [ ] Applies only policy-approved records through PartnerWriter with actor `haiku`; old record archived by the writer; per-run cap on records changed, remainder listed as deferred in the report
- [ ] Runs consolidate at the end of a real run that changed anything
- [ ] Report printed to stdout (captured by run-job into logs/updates/): flags, proposals with old->new per field, applied, rejected with reasons, deferred, errors, notable redirects, counts line; also writes machine-readable `updates/<ts>.json` (proposed, old record, diff) to the private history store
- [ ] Tests with LocalStore: CMOD fixture end to end applies name+website; dry-run writes no records; cap defers extras; policy rejection leaves record untouched; a test asserts no code path calls the writer except via policy output

## Implementation Plan

updates/job.py, cli.py `updates` subcommand, partners.default_writer(). Consolidate via partners.consolidate. Document in updates/DESIGN.md.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: as listed in the acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

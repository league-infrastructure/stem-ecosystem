---
id: '042'
title: Partner records in the bucket, and run logs
status: ticketing
branch: sprint/042-partner-records-in-the-bucket-and-run-logs
use-cases: [SUC-001, SUC-002, SUC-003, SUC-004, SUC-005]
issues: [77-per-partner-records-in-the-bucket-as-the-source-of-truth.md, 72-capture-every-scraper-run-to-a-logs-directory-in-the-bucket.md]
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 042: Partner records in the bucket, and run logs

## Goals

1. Make `data/partners/<slug>/partner.json` in bucket `jtl-stem-ecosystem-scrape`
   the source of truth for the curated roster (issue 77), with a single
   archiving writer, a private `history/` area, and a recomposed
   `data/partners.json`.
2. Capture every `run-job` run to a private `logs/` prefix with an index (issue 72).

## Problem

The roster lives in Git (`src/data/partners.json`, 211 entries, 204 logos),
is baked into the scraper image, and is imported by 7 site pages and ~10
scraper modules. It cannot be updated by the scraper or by agents without a
rebuild/commit. Run output is lost when swarm tasks are replaced.

## Solution

Per-partner records plus logos in the bucket, written only through one
archiving writer (archive current to `history/partners/<slug>/<ts>-...`, write new,
append `history/partners/changes.jsonl`). Consolidation lists/validates records and
writes `data/partners.json`; it runs at the end of scrape and updates and as
`partner-scrape partners consolidate`. CLI `partners get|put|add|consolidate` for hand edits.
Scraper reads the roster from the bucket; the image stops baking it. The site's
`scripts/fetch-data.mjs` builds `src/data/partners.json` and `public/images/logos/*`
from the consolidated file (both gitignored at the end). `run-job` tees output and uploads it.

## Success Criteria

- Consolidated output built from migrated records equals the pre-migration roster
  (apart from `logo_src`), verified by a script.
- Scraper and site build run with no `src/data/partners.json` in Git.
- A `run-job` run produces a log object and an index line; upload failure never changes exit code.
- Real migration done and verified; new image ready for team-lead redeploy.

## Scope

### In Scope

Tickets 001-007 below.

### Out of Scope

- Deleting `cache/partner_log/` (the deployed 0.20261008.4 image still writes it until redeploy; follow-up).
- Issues 73-76 (redirects, profiles, Haiku update check); only the `updates` log type name is reserved.
- GitHub push, site deploy. Bucket lifecycle rules.

## Test Strategy

pytest with LocalStore and moto-style fakes for S3; node tests (existing style) for
fetch-data; bash test (stub commands) for run-job. No test reads the real `.env` or
touches the real bucket. The only real-bucket work is the team-lead checklist (ticket 007).

## Architecture Notes

See architecture-update.md. Decisions already made by the stakeholder (not reopened):
slug stored in record; history/ private; copy-not-move for partner_log; logs private.
Design call: logos live at `data/partners/<slug>/logo.<ext>`; `logo_src` in the record is
the bucket-relative path `partners/<slug>/logo.<ext>`; fetch-data downloads them to
`public/images/logos/<slug>.<ext>` and rewrites `logo_src` to `/images/logos/<slug>.<ext>`
in the fetched `src/data/partners.json`. Justification: pages and `<img>` URLs stay
unchanged (no page churn, no runtime dependency on the bucket host, same-origin on GitHub Pages).

## Team-lead checklist (real-credential operations, after tickets 001-006 are done)

Programmers never read the real `.env`. Ticket 007 is run/supervised by the team lead.
1. `dotconfig load prod`; `cd scraper; set -a; source ../.env; set +a`.
2. `uv run partner-scrape partners migrate --site-dir .. --dry-run` and review the report.
3. Run it for real (records + logos via writer, actor "migration"; copies `cache/partner_log` to `history/partner_log`, never deleting).
4. `partner-scrape partners consolidate`, then `partner-scrape partners verify-migration --baseline <git show HEAD:src/data/partners.json>`.
5. `node scripts/fetch-data.mjs`, `npm run build`, compare site output.
6. Then `git rm` roster and logos, gitignore, commit.
7. Build the new amd64 image, push it, and redeploy the swarm stack BEFORE the old image's Monday 03:00 PT scrape (see scraper/docker/README.md). If the old image wrote to `cache/partner_log` in the interim, re-run the (idempotent) copy.
8. After the new image is verified, file a follow-up issue to delete `cache/partner_log/` (out of scope here).

## GitHub Issues

(None.)

## Definition of Ready

- [x] Sprint planning documents are complete (sprint.md, use cases, architecture)
- [x] Architecture review passed (self-review recorded)
- [ ] Stakeholder has approved the sprint plan (Eric, 2026-10-08, "plan this ... and start executing"; team lead records gate)

## Tickets

| # | Title | Depends On |
|---|-------|------------|
| 001 | Run logs: tee and upload run-job output | none |
| 002 | Partner record store and archiving writer | none |
| 003 | Consolidation and partners CLI | 002 |
| 004 | Scraper reads roster from the bucket; partner_log to history | 003 |
| 005 | Migration tooling and equality verification | 003, 004 |
| 006 | Site reads fetched roster and logos | 003 |
| 007 | Real migration, cutover, redeploy (team-lead run) | 001, 004, 005, 006 |

Tickets execute serially in the order listed.

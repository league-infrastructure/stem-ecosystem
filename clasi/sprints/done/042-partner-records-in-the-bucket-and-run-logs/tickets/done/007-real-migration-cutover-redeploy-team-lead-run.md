---
id: '007'
title: Real migration, cutover, redeploy (team-lead run)
status: done
use-cases:
- SUC-004
depends-on:
- '001'
- '004'
- '005'
- '006'
github-issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Real migration, cutover, redeploy (team-lead run)

## Description

Team-lead-run: the real-credential cutover. Follow the checklist in sprint.md. Programmers do not run this ticket and never read the real .env.

## Acceptance Criteria

- [x] Dry-run report reviewed, then real migration run; verify-migration clean (only logo_src differs)
- [x] `cache/partner_log` copied to `history/partner_log`; the old prefix is left in place (deletion is a follow-up)
- [x] Site build via fetch-data succeeds and matches the pre-migration build
- [x] src/data/partners.json and public/images/logos/* removed from git and gitignored
- [x] New amd64 image built, pushed, and the swarm stack redeployed BEFORE the old image's Monday 03:00 PT scrape; partner_log copy re-run after redeploy if the old image wrote in the interim
- [x] Follow-up issue filed: delete cache/partner_log after the new image is verified
- [x] Bucket versioning note recorded for league-network services/spaces

## Implementation Plan

Checklist: see sprint.md (updated to include image build, push and swarm redeploy as part of this ticket). Use scraper/docker/README.md swarm deploy docs from sprint 041. No GitHub push of the sprint and no site deploy.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest` (and `npm test`/node tests for ticket 006)
- **New tests to write**: as listed in the plan
- **Verification command**: `cd scraper && uv run pytest`

## Results (team lead, 2026-10-08/09)

- **Migration:**
  - The dry run reported 211 records, 194 logos and 208 partner_log objects,
    with 0 errors.
  - The real run wrote the same counts, and `consolidate` wrote
    `partners.json` (211).
  - `verify-migration` against `git show HEAD:src/data/partners.json`
    reported OK; only the order note differed.
- **Access:**
  - `data/partners/<slug>/partner.json` and `logo.*` return 200
    anonymously.
  - `history/` and `logs/` return 403.
- **Image and deploy:**
  - Image 0.20261008.10 (linux/amd64) was pushed to ghcr and the stack was
    redeployed (`TAG=0.20261008.10`) right away, so the old image never ran
    a scrape in between. No partner_log re-copy was needed.
  - A full `run-job scrape` in the swarm container returned SUCCESS in
    1632s with 356 opportunities.
  - The run log was uploaded, and `logs/index.jsonl` has the entry.
  - CMOD `past-events.json` still has 8 events.
  - Opportunity `logo_src` values are in `partners/<slug>/logo.<ext>` form.
- **Site:**
  - `npm run fetch-data` fetched 356 opportunities, 211 partners and 194
    logos, with 0 missing.
  - `npm run build` built 921 pages, and every `/images/logos/` reference
    resolves.
- **Git:** `src/data/partners.json` and 203 logos were untracked and are
  ignored (commit 2fef87d). `default-partner.svg` is kept.
- **Records and follow-ups:**
  - Follow-up issue 78 (delete `cache/partner_log`).
  - league-network commit 8138f8c covers the spaces versioning/layout and
    the scraper change log.

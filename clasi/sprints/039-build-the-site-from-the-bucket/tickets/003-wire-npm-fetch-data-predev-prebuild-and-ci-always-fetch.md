---
id: '003'
title: Wire npm fetch-data, predev/prebuild, and CI always-fetch
status: done
use-cases:
- SUC-002
depends-on:
- '002'
github-issue: ''
issue: 69-build-the-site-from-the-bucket-and-stop-committing-scraped-data.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Wire npm fetch-data, predev/prebuild, and CI always-fetch

## Description

Add npm scripts: fetch-data (always fetches, forwards args such as --local), and predev/prebuild that run the fetch only if the required files are missing (stakeholder decision: fetch only if missing; explicit npm run fetch-data refreshes). deploy.yml must always fetch fresh: run `npm run fetch-data` explicitly before the build step (or set a FORCE flag honored by prebuild), so a deploy can never build stale or absent data.

## Acceptance Criteria

- [x] `npm run fetch-data` always refreshes; `npm run fetch-data -- --local <dir>` works
- [x] predev/prebuild fetch only when required files are absent; no network when present
- [x] deploy.yml fetches fresh data explicitly before `npm run build`, with no secrets
- [x] Fresh clone: `npm ci && npm run build` succeeds with network only
- [x] dist/data and dist/images file lists match a pre-sprint build (documented diff)

## Implementation Plan

Files to create/modify: package.json, .github/workflows/deploy.yml

## Testing

- **Existing tests to run**: `uv run pytest` (scraper) if scraper touched; `npm run build`
- **New tests to write**: as listed in acceptance criteria
- **Verification command**: `npm run build; fresh-clone build in temp dir`

## Implementation Notes

- package.json: `fetch-data` (always fetches), `predev`/`prestart`/`prebuild` (`--if-missing`), `test` (node --test).
- build.yml and deploy.yml: explicit `npm run fetch-data` step before the build (Node 22 in CI; global fetch OK). No secrets.
- Fresh-clone build (generated files deleted, `npm ci && npm run build`) succeeded. dist/data file list is identical (426 files). dist/images/opportunities differs (562 vs 534 files) because the bucket holds a newer scrape than the committed snapshot (358 vs 360 opportunities; content-hashed image names). Expected, not a defect.

---
id: 039
title: Build the site from the bucket
status: planning-docs
branch: sprint/039-build-the-site-from-the-bucket
use-cases:
- SUC-001
- SUC-002
- SUC-003
- SUC-004
issues:
- 69-build-the-site-from-the-bucket-and-stop-committing-scraped-data.md
---

# Sprint 039: Build the site from the bucket

## Goals

The site build fetches the scraper's published data from the bucket over
plain HTTPS and no scraped data is committed to Git.

## Problem

Scraped data is copied into tracked files by hand (`scripts/fetch-data.sh`,
needs aws CLI and credentials) and committed. A refresh touches ~570 files,
most differing only in `generated_at`. `deploy.yml` builds whatever is
committed, so the live site is only as fresh as the last manual commit
(2026-09-02).

## Solution

1. Make bucket `data/` publicly readable (scraper writes `public-read`;
   one-time backfill; fallback is a stakeholder-set bucket policy).
2. Replace `fetch-data.sh` with a dependency-free Node script
   (`scripts/fetch-data.mjs`, Node 22 `fetch`) that downloads the published
   files into gitignored build inputs, derives per-partner and image file
   lists from the fetched JSON (no bucket listing), and keeps the image
   integrity check and a `--local <dir>` mode.
3. Run it automatically via `predev`/`prebuild`; CI needs only `npm ci`.
4. `git rm --cached` all generated files and gitignore them.
5. Update docs and have the weekly scrape trigger a deploy.

## Success Criteria

- Fresh clone + `npm run build` succeeds with only network access.
- `/data/**`, `/images/opportunities/**` URLs unchanged.
- `src/data/partners.json` untouched and tracked; no generated file tracked.
- Weekly scrape is followed by a deploy with fresh data.

## Scope

### In Scope

Public-read publishing and backfill, fetch script, npm hooks, untracking,
deploy workflow, scheduled-run deploy trigger, README / `/data-access`
wording, retire `fetch-data.sh`.

### Out of Scope

Snapshots/backups; issue 67 (hiding ended opportunities); cache/ access;
scraper's `--site-dir` semantics beyond verifying it does not conflict.

## Test Strategy

Scraper: `uv run pytest` for the ACL change (mocked client asserts
`ACL='public-read'` for `data/` keys only). Fetch script: a node test
against a local fixture dir via `--local` plus a failure-path check
(missing image, missing file exits non-zero). End-to-end: fresh `git clone`
style build (`npm ci && npm run build`) and diff of `dist/data` file list
against the pre-sprint build.

## Architecture Notes

See architecture-update.md. No bucket listing permission is required.

## GitHub Issues

None.

## Definition of Ready

- [x] Sprint planning documents are complete (sprint.md, use cases, architecture)
- [x] Architecture review passed
- [ ] Stakeholder has approved the sprint plan

## Tickets

| # | Title | Depends On |
|---|-------|------------|
| 001 | Scraper publishes data/ public-read; backfill existing objects | - |
| 002 | Node fetch script for site data (HTTPS, --local, integrity check) | - |
| 003 | Wire npm fetch-data, predev/prebuild, and CI always-fetch | 002 |
| 004 | Untrack generated data and images; retire fetch-data.sh | 001, 003 |
| 005 | Update README and data-access docs for build-time fetch | 004 |
| 006 | Scheduled scrape triggers a site deploy | 004 |
| 007 | Make deploy manual-only and remove the GitHub scheduled scrape | 006 |

Tickets execute serially in the order listed.

---
id: '006'
title: Site reads fetched roster and logos
status: done
use-cases:
- SUC-003
depends-on:
- '003'
github-issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Site reads fetched roster and logos

## Description

Extend `scripts/fetch-data.mjs` so it fetches the consolidated `data/partners.json` (already fetched as the envelope) and also writes `src/data/partners.json` (array of curated fields; events urls dropped or kept harmlessly) and downloads each partner's `partners/<slug>/logo.<ext>` to `public/images/logos/<slug>.<ext>`, rewriting `logo_src` accordingly (bare filename form matching what the pages expect, to be confirmed by reading how pages use `logo_src`). Staged and validated like the rest. `--local` mode supported. `.gitignore` entries added for the fetched files (git rm is ticket 007). Remove the 'hand-curated is never written' comment. Ensure the build runs fetch-data before astro (check package.json scripts).

## Acceptance Criteria

- [x] fetch-data produces src/data/partners.json and logo files from a local fixture data dir
- [x] Failed fetch leaves previous files intact
- [x] Page output unchanged (pages untouched, or minimal edit if logo_src shape requires it)
- [x] `--if-missing` accounts for the new files
- [x] Existing node tests pass; new tests added

## Implementation Plan

Follow existing test style for fetch-data (look for tests next to scripts/). Also update CLAUDE.md/README site docs about where the roster lives and how to edit it (`partner-scrape partners ...`).

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest` (and `npm test`/node tests for ticket 006)
- **New tests to write**: as listed in the plan
- **Verification command**: `cd scraper && uv run pytest`

## Implementation Notes

- `scripts/fetch-data.mjs` now also builds `src/data/partners.json` (array; `events_url`/`past_events_url` dropped, `slug` kept) and downloads each `data/partners/<slug>/logo.<ext>` to `public/images/logos/<slug>.<ext>`, rewriting `logo_src` to that bare filename so `getLogoPath` and all 7 pages are unchanged. Missing logo, non-`partners/<slug>/logo.<ext>` logo_src, or duplicate target names fail the staged fetch before anything is installed. Logos are added, never deleted (default-partner.svg stays).
- Post-ticket-004 scraper writes the record's bucket-form `logo_src` into `opportunities.json` and `ads.json`; fetch-data rewrites those too (matching the roster's bucket paths; unknown/legacy bare names pass through). `registry_data/ads/league.toml` logo_src changed from `the_league_of_amazing.png` to `partners/the_league_of_amazing_programmers/logo.png` (+ its test) so the ad resolves to the fetched `the_league_of_amazing_programmers.png`. Until the first post-cutover scrape regenerates the bucket's ads.json, the old bare name remains and resolves only while the tracked logo file is still in git (ticket 007 should run a scrape/ads export, or edit bucket ads.json, before `git rm` of logos).
- `--if-missing` (`dataPresent`) now also requires `src/data/partners.json` and `public/images/logos`.
- Verified: local migrated store (scratch) -> `fetch-data --local` into a scratch copy of the site -> `npm run build` (923 pages); partner/opportunity pages reference only existing logo files. `.gitignore` has the new entries; roster and logos remain tracked (ticket 007).

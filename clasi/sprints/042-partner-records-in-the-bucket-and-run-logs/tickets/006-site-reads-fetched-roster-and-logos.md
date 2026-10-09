---
id: '006'
title: Site reads fetched roster and logos
status: open
use-cases: [SUC-003]
depends-on: ["003"]
github-issue: "77-per-partner-records-in-the-bucket-as-the-source-of-truth.md"
issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Site reads fetched roster and logos

## Description

Extend `scripts/fetch-data.mjs` so it fetches the consolidated `data/partners.json` (already fetched as the envelope) and also writes `src/data/partners.json` (array of curated fields; events urls dropped or kept harmlessly) and downloads each partner's `partners/<slug>/logo.<ext>` to `public/images/logos/<slug>.<ext>`, rewriting `logo_src` accordingly (bare filename form matching what the pages expect, to be confirmed by reading how pages use `logo_src`). Staged and validated like the rest. `--local` mode supported. `.gitignore` entries added for the fetched files (git rm is ticket 007). Remove the 'hand-curated is never written' comment. Ensure the build runs fetch-data before astro (check package.json scripts).

## Acceptance Criteria

- [ ] fetch-data produces src/data/partners.json and logo files from a local fixture data dir
- [ ] Failed fetch leaves previous files intact
- [ ] Page output unchanged (pages untouched, or minimal edit if logo_src shape requires it)
- [ ] `--if-missing` accounts for the new files
- [ ] Existing node tests pass; new tests added

## Implementation Plan

Follow existing test style for fetch-data (look for tests next to scripts/). Also update CLAUDE.md/README site docs about where the roster lives and how to edit it (`partner-scrape partners ...`).

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest` (and `npm test`/node tests for ticket 006)
- **New tests to write**: as listed in the plan
- **Verification command**: `cd scraper && uv run pytest`

---
id: '005'
title: Migration tooling and equality verification
status: done
use-cases:
- SUC-004
depends-on:
- '003'
- '004'
github-issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Migration tooling and equality verification

## Description

Add `partners/migrate.py` with CLI `partners migrate [--site-dir ..] [--dry-run]` and `partners verify-migration --baseline <path>`. Migrate: split `src/data/partners.json` into records; slug = current `slugify(name)`, stored in the record; upload via the writer with actor `migration`; upload logos from `public/images/logos/` to `data/partners/<slug>/logo.<ext>` and set `logo_src` to `partners/<slug>/logo.<ext>`; copy (never move/delete) `cache/partner_log/**` to `history/partner_log/**`, idempotent and skipping identical objects. Verify: consolidate and compare to baseline, ignoring logo paths, reporting any other diff.

## Acceptance Criteria

- [x] Dry-run writes nothing and prints a report (counts, slug collisions, missing logos)
- [x] Slug collisions or unusable names fail the migration before writing
- [x] Rerun is idempotent (no new history entries for unchanged records)
- [x] cache/partner_log is never modified or deleted (test)
- [x] verify-migration exits non-zero on any difference other than logo_src
- [x] Handles current `logo_src` shapes: bare filenames in public/images/logos (about 187 entries) and 17 entries with no logo; flag any logo_src whose file is missing, or a non-bare/URL value

## Implementation Plan

Programmer must first survey the actual `logo_src` values in src/data/partners.json against files in public/images/logos/ (planner found bare filenames and 17 empty; site pages' usage of logo_src was not checked: grep `src/` for `logo_src` and `/images/logos/` and record findings in the ticket). Test fixture: small roster + logos in tmp dirs, LocalStore. Never touch the real bucket or .env.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest` (and `npm test`/node tests for ticket 006)
- **New tests to write**: as listed in the plan
- **Verification command**: `cd scraper && uv run pytest`

## Implementation Notes

**logo_src survey** (against `src/data/partners.json`, 211 entries, and `public/images/logos/`, 204 files):
- 194 bare filenames (all exist in `public/images/logos/`; none shared by two partners), 17 empty strings, 0 URLs / non-bare values, 0 absent keys, 0 logo_src pointing at a missing file.
- Extensions of used logos: png 110, jpg 64, svg 12, webp 4, jpeg 2, gif 2.
- 10 logo files have no partner (not migrated; listed by the migrate report): default-partner.svg (site fallback, stays a site asset), elementary_institute_of_science_2.png, fleet_science_center_2.jpg, greater_san_diego_science_2.jpg, ocean_connectors_2.jpg, san_diego_automotive_museum_2.png, the_living_coast_discovery.jpg, the_salk_institute_education.png, the_san_diego_river_2.jpg, viasat_2.png.
- Site usage: `src/lib/helpers.ts` `getLogoPath` prefixes `${base}/images/logos/` to the bare filename (empty -> default-partner.svg); used by PartnerCard, partners/[id], index.astro; opportunities carry their own `logo_src` (and `src/data/ads.json` uses `the_league_of_amazing.png` from the same dir, which is NOT a partner logo and not in the roster: ticket 006/007 must keep public/images/logos/ files used by ads when removing logos from Git; check it is among the 10 orphans or a partner logo).
- No slug collisions among the 211 names; all slugify to valid keys; roster passes validation.

**Rename-safe history key (team lead request)**: `export/partner_log.py` `log_slug_for` resolves partner_name -> roster record -> stored slug (fallback `slugify(name)` when unmatched or the record has no slug); `export/publish.py` reads the same key. Test class `TestRenameKeepsHistory` in `tests/test_export_partner_log.py`. At migration stored slug == slugify(name), so existing history paths are unchanged.

**Decisions**: bad `logo_src` (missing/non-bare) and slug problems are errors that block both dry-run success and real run. partner_log copy: identical skipped; differing `opportunities.jsonl` is merged (missing source lines appended by (slug, content_hash)), differing `partner.json` snapshot keeps destination (so a re-run after redeploy never clobbers newer history). verify-migration is read-only (consolidates in memory), checks logo presence/existence, and treats partner order as a non-fatal NOTE (baseline is not id-ordered; consolidation sorts by id; the partners page sorts by name itself).

**Full dry-run + real run + verify on a local copy** of the real roster and logos (LocalStore dirs in scratchpad): 211 records, 194 logos, rerun 0 new/0 updated, verification OK.

---
id: 009
title: Production run and redeploy (team-lead run)
status: done
use-cases:
- SUC-001
- SUC-002
- SUC-003
- SUC-004
- SUC-006
depends-on:
- 008
- '010'
- '011'
github-issue: ''
issue:
- 73-detect-and-record-redirects-on-every-fetch.md
- 74-weekly-scrape-of-partner-home-about-and-contact-pages.md
- 75-post-scrape-partner-record-update-check-with-haiku.md
- 76-per-partner-event-quality-checks-in-the-post-scrape-report.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Production run and redeploy (team-lead run)

## Description

Team-lead-run production steps with real credentials. Programmers do not read the real `.env`.

## Acceptance Criteria

- [x] Live redirect check: fetch `http://sdcdm.org`; `final_url` is visitcmod.org and flagged notable
- [x] `partner-scrape profiles` run for real; report reviewed
- [x] `partner-scrape updates --dry-run` reviewed (known test case: San Diego Children's Discovery Museum -> Children's Museum of Discovery, sdcdm.org -> visitcmod.org)
- [x] `partner-scrape updates` run for real; `history/partners/changes.jsonl` shows actor `haiku` entries; archived old records exist; `data/partners.json` consolidated
- [x] amd64 image built and pushed; swarm stack redeployed (scraper/docker/README.md); first scheduled Sunday run produces logs/profiles and logs/updates objects

## Implementation Plan

Follow the team-lead checklist in sprint.md. Record results in this ticket.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: as listed in the acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

## Results (team lead, 2026-10-09)

- **Live redirect check:** `http://sdcdm.org` → `https://visitcmod.org/` (301)
  was recorded by the profiles job.
- **Deploys:** images 0.20261008.19, then .20, .21 and .22 (after tickets
  010 and 011) were built for linux/amd64, pushed to ghcr, and the swarm was
  redeployed each time. .22 is live.
- **profiles (real):**
  - Ran for 990s: 211 partners, 165 fetched, 49 failed (mostly HTTP 403 bot
    walls; issue 79), 13 notable redirects, 211 snapshots written.
- **First updates dry run:** 106 partners had approvable changes, many of
  them harmful (named contacts replaced by generic ones, lossy renames, a
  staging host). The real run was halted, and tickets 010 and 011 were added
  to tighten the policy.
- **Final dry run:** would apply 20 (mostly filling empty fields), 40
  deferred, 186 needs-review.
- **Real CMOD run (`--slug`):** applied name, website and description
  (actor `haiku`), archived to
  `history/partners/san_diego_children_s_discovery_museum/20261009T050137Z-partner.json`,
  and consolidated. Email, Facebook and phone went to needs-review.
- **Real updates run:** 20 partners and 45 fields applied, 39 deferred, 185
  needs-review, 0 errors, consolidated. The applied changes were:
  - mostly filling empty social links, phones and emails;
  - redirect-backed websites for aops, brain_balance and
    escondido_public_library;
  - the aops rename.
- **Event-quality report:** 157 findings across 527 events, report-only.
- **Follow-ups:** issue 79 (headless fallback for profiles) and issue 80
  (review queue for needs-review items).

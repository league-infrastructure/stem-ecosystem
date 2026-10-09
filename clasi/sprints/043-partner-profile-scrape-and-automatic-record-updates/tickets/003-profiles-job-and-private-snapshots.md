---
id: '003'
title: profiles job and private snapshots
status: done
use-cases:
- SUC-002
depends-on:
- '001'
- '002'
github-issue: ''
issue: 74-weekly-scrape-of-partner-home-about-and-contact-pages.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# profiles job and private snapshots

## Description

The `profiles` job: for every roster partner with a website, fetch home + About + Contact via PoliteFetcher, extract facts, write a private snapshot with per-page content hashes (issue 74).

## Acceptance Criteria

- [x] `partner-scrape profiles [--slug S] [--limit N]` iterates the bucket Roster; partners without a website are listed in the report and skipped
- [x] Fetch uses PoliteFetcher (robots, throttle, cache, headless fallback); a failure for one partner/page is recorded and never aborts the run
- [x] Snapshot at `history/profiles/<slug>/profile.json` in the history (private) store: facts, page URLs, per-page sha256 of body, final_url, redirect chain, fetched_at, status; overwritten each run; written only when content changed or nothing exists
- [x] Unchanged pages give identical hashes across runs
- [x] Notable redirects (ticket 001) appear in the printed report; summary counts line printed (partners, fetched, failed, redirects, skipped)
- [x] No LLM; tests with fake fetcher and LocalStore; snapshot is never written to a public-read store (test)

## Implementation Plan

partner_scrape/profiles/snapshot.py (model, read/write, hash), job.py (run_profiles), cli.py subcommand `profiles`. Use config.get_history_store() and the scrape-cache store; mirror how cli `partners` and the scrape build stores. Document key layout in profiles/DESIGN.md.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: as listed in the acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

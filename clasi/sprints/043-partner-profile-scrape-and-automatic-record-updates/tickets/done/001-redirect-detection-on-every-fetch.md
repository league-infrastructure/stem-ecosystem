---
id: '001'
title: Redirect detection on every fetch
status: done
use-cases:
- SUC-001
depends-on: []
github-issue: ''
issue: 73-detect-and-record-redirects-on-every-fetch.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Redirect detection on every fetch

## Description

Record `final_url` and `redirect_chain` on every fetch, plain and headless, store them in the fetch cache, and collect notable redirects for run reports (issue 73).

## Acceptance Criteria

- [x] `FetchResponse` has `final_url` (default = url) and `redirect_chain` (list of [status, url]); `UrllibFetcher` fills them via a redirect-recording handler; `PlaywrightFetcher` fills `final_url` from the navigation response
- [x] Cache entries store both fields; old entries without them load with `final_url == url` and empty chain
- [x] `is_notable_redirect(requested, final)`: True when host differs ignoring `www.`; False for http->https on same host, www-only, and no redirect
- [x] `fetch/redirects.py` `RedirectLog` collects notable redirects (source/partner, requested, final, status); `PoliteFetcher` reports to it when one is supplied; summarized as lines in run output so run logs carry them
- [x] Following redirects stays on; no change to scraping behavior; existing tests pass

## Implementation Plan

READ FIRST: fetch/fetcher.py (`_execute`, urllib follows redirects silently), fetch/headless.py, fetch/cache.py (`write_cache_entry`, `entry_to_response`). Tests: fake opener returning 301 to other host, http->https, no redirect; headless fake page with a final URL; cache round trip and legacy entry. Update fetch/DESIGN.md.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: as listed in the acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

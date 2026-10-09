---
status: in-progress
sprint: '043'
tickets:
- 043-001
- 043-008
- 043-009
---

# Detect and record redirects on every fetch

## Description

Stakeholder direction (Eric, 2026-10-08): every time we visit a site,
check whether we got a redirect. This should be a natural part of every
fetch, not a separate audit.

Motivating case (2026-10-08): San Diego Children's Discovery Museum
rebranded as Children's Museum of Discovery. `http://sdcdm.org` now returns
**301 → https://visitcmod.org/**. Our partner record still says `sdcdm.org`,
and nothing noticed.

Today `partner_scrape/fetch/fetcher.py` (`_execute`) uses `urllib`,
which follows redirects silently. The `FetchResponse` records the
*requested* URL, and the final URL (`response.geturl()`) and the redirect
chain are discarded. The headless fetcher (`fetch/headless.py`) also
ignores the navigation's final URL.

## Proposal

- `FetchResponse` gains `final_url` (and ideally `redirect_chain`: a list
  of `(status, url)`). Both the plain and headless fetchers fill it in.
  The fetch cache stores it.
- A redirect is **notable** when the final host differs from the requested
  host, ignoring a `www.` difference and http→https upgrades on the same
  host.
- Notable redirects are collected per run into the run report and log
  (issue 72): source or partner, requested URL, final URL and status.
- For partner websites (issue 74), a notable redirect is a flagged change
  that feeds the update check (issue 75).
- No behavior change for scraping itself: following redirects stays on.

## Acceptance

- Unit tests with a fake opener: 301 to another host is recorded and
  flagged; http→https on the same host is not flagged; no redirect leaves
  `final_url == url`.
- A live check against `http://sdcdm.org` records the visitcmod.org
  redirect.

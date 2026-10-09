---
status: pending
---

# Profiles job: fall back to headless fetching when a site blocks the plain fetcher

## Description

The first real `profiles` run (2026-10-09, image 0.20261008.19) fetched 165
of 211 partner sites. **49 failed**, mostly with `HTTP 403` bot walls (e.g.
4_h_san_diego_ucce, barnes_noble, barrio_logan_college_institute,
boy_scouts_national_foundation, boys_girls_clubs_of_greater_san_diego). Those
partners get no snapshot, so their records are never checked.

The scraper already has a headless (Playwright) fetcher that event sources use
when `fetch_strategy = "headless"`.

## Proposal

- In the profiles job, when the home page returns 403/429/503 or a transport
  error, retry the home, About and Contact pages with the headless fetcher
  (shared PlaywrightFetcher, existing PoliteFetcher wrapping and robots
  rules).
- Record which strategy produced each page in the snapshot.
- Report the remaining failures by status in the profiles run log.
- Watch for issue 68 (Wix `ERR_ABORTED`) in the headless path.

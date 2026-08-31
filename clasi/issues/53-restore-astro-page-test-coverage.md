---
status: pending
---

# Restore the Astro page and schema test coverage deleted with partner-scrape's site/ checkout

## Description

This repo has **no automated tests at all**. It should have 28, and the
reason it doesn't is a side effect of the repo split rather than a decision
anyone made about this site.

partner-scrape's sprint 019 ticket 002 deleted 24 tests that read from its
`site/` checkout when that directory became a build-time-only checkout of
this repo. Its issue 48 recovers the ones with data-quality value by moving
the logic into the pipeline, and explicitly disclaims the rest: the 22 tests
in `test_site_teams_pages.py` and the 6 in `test_site_data_access_page.py`
"test Astro page/schema content that now lives exclusively in
stem-ecosystem — genuinely not partner-scrape's concern anymore, not
proposed for recovery here."

That reasoning is correct, and it leaves the coverage homeless. Nothing
tracks it today. These tests asserted things this site is now solely
responsible for: that team pages render the fields they claim to, and that
`/data-access`'s published schema table actually matches the shape of the
data being published. The second is the more valuable of the two — that page
is a public contract that agents and downstream consumers read, and it can
silently drift from reality with no other check in the system.

The tests should not be recovered verbatim. They were written to run inside
a Python test suite reading a checked-out site directory, which is precisely
the arrangement the consolidation removed. They need to be re-expressed as
this repo's own tests.

## Proposed fix

- Pick a test runner for this repo. Astro projects conventionally use
  Vitest; there is no existing choice to be consistent with, since there is
  no test suite.
- Recover the `/data-access` schema assertions first. Assert that every
  field the page documents exists in the published data, and that the
  published data has no documented-nowhere fields — the drift check in both
  directions.
- Recover the team page assertions second: that a team detail page renders
  the fields it should, including the cases issue 49 touches (website link
  present when a URL exists, no blurb block when there is no blurb).
- Add a roster invariant while building the harness: the slugified names in
  `src/data/partners.json` must be unique. This is the missing check behind
  partner-scrape's issue 46, where 9 exact duplicate rows in the 153-entry
  roster silently collapsed to 144 published partner directories, each
  overwriting the other's `events.json`. The duplicates are gone as of the
  211-row roster landed in `a86a93d`, and partner-scrape is adding its own
  pipeline-side guard — but `partners.json` is hand-edited *here*, so the
  cheapest place to catch a reintroduced duplicate is a test in this repo
  that runs before the file ever reaches the pipeline.
- Wire the suite into `.github/workflows/build.yml` so it gates branches the
  way the build already does.

## References

partner-scrape issue 48 (which disclaims this coverage and explains why);
sprint 019 ticket 002 (the deletion). Original files, for reference when
reconstructing intent: `tests/test_site_teams_pages.py` and
`tests/test_site_data_access_page.py` in partner-scrape's history. Site
files under test: `src/pages/teams/[slug].astro`,
`src/pages/data-access.astro`.

For the roster invariant: partner-scrape issue 46 (the collision discovery)
and its slug derivation, `slugify()` in `partner_scrape/model.py` — the
assertion here must match that function's behavior, not approximate it.

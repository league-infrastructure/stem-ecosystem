---
status: pending
split_from: partner-scrape issue 14-improve-volunteer-opportunity-discovery.md
---

# Volunteer org profiles: define the roster field and render it

## Description

Website half of partner-scrape issue 14, split out when the site moved to
this repo. That issue's 2026-08-30 research addendum killed the original
plan of scraping third-party volunteer platforms (ToS and JS-only barriers)
and settled on a curated per-org volunteer profile instead: organization,
what volunteers actually do, age minimums, and a link to the org's own
portal.

That record is a different kind of thing from everything else in the
opportunities listing. It has no date. It is a standing "this org takes
volunteers, here's where to apply" pointer, and the listing it would appear
in is organized around dated events. partner-scrape's issue leaves the
display question explicitly open: "For Strategy B, what does the site render
— a card that links out, vs. a synthesized listing? How does it sit
alongside dated opportunities?"

**Strategy B is entirely this repo's**, not just its rendering. The profile
is a new field or section on `src/data/partners.json`, which is the
hand-curated roster this repo owns — so defining the field shape and
populating it are both site-side work, and there is no upstream dependency
to wait on. partner-scrape keeps only the genuinely dated volunteer events,
which continue to arrive through the normal opportunities path.

**Age minimums have to be visible.** The addendum is specific that Fleet is
18+, San Diego Zoo Wildlife Alliance is 18+, and Birch is 16+, and that this
matters for the teen audience. A teenager filtering for volunteering and
finding a list they are mostly ineligible for is a worse outcome than not
listing those orgs — so the minimum belongs on the card, not only on the
detail page, and it likely wants to be filterable.

## Open questions

- Where do these live? Three plausible shapes, and they are not equivalent:
  mixed into `/opportunities` as undated cards, given their own standing-
  entity section like teams and places, or surfaced on the existing partner
  detail page as a "this org takes volunteers" block. The third is the
  cheapest and reuses a page visitors already reach; the second matches the
  established pattern for undated content; the first risks diluting a
  listing whose whole affordance is "what's happening and when."
- If they mix into `/opportunities`, how does an undated card sort and
  filter against dated ones? Every existing filter and sort assumes a date.
- Does the existing `Volunteering` opportunity_type stay for genuinely dated
  volunteer events, with profiles as a separate concept? partner-scrape is
  registering a handful of real dated volunteer sources, so both kinds will
  exist and the site needs to not conflate them.

## References

partner-scrape issue 14, including its Research update (2026-08-30) that
established Strategy B as primary and listed the age minimums; the dated
volunteer sources it registers separately (UCSD Localist Volunteer type,
Coastkeeper, Surfrider SD, ILACSD) which continue to flow through the normal
opportunities path.

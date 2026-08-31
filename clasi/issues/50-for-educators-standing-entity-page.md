---
status: pending
split_from: partner-scrape issue 33-educator-programs-layer.md
---

# A For-Educators section: standing-entity pages for teacher PD and school programs

## Description

Website half of partner-scrape issue 33, split out when the site moved to
this repo. Educators are a named audience of this site and currently get
nothing — there is no route, nav entry, or filter that serves a teacher
looking for professional development or a free/Title I program to bring to
their school.

The content this renders is **not dated events**. Teacher PD offerings and
free school programs are standing, bookable things with eligibility rules
and no fixed calendar date, so they do not fit the opportunities model. They
fit the standing-entity pattern this site already uses three times: teams,
places, and clubs each have an index route, a `[slug]` detail route, a card
component, and a filter component. A For-Educators section should be the
fourth instance of that pattern rather than a new invention.

The record shape is partner-scrape's to define and populate (org, program,
eligibility, how to book, last-verified). This issue is blocked on that
shape existing, but the site work is otherwise independent: routes,
components, filters, and nav.

## Proposed fix

- `src/pages/for-educators/index.astro` and `[slug].astro`, following
  `src/pages/places/` as the closest structural precedent.
- A card component alongside `PlaceCard.astro` / `ClubCard.astro`, and a
  filter component alongside `PlaceFilters.astro`.
- Filters that match how a teacher actually narrows: eligibility (Title I,
  grade band) and how-to-book. Reuse the existing facet markup and
  `src/scripts/filters.js` behavior rather than writing a third filter
  implementation.
- A nav entry in `src/components/Header.astro`, and a mention in
  `src/pages/data-access.astro` if the records are published under
  `public/data/`.
- Surface `last-verified` on the detail page. For undated, bookable content
  the freshness date is the visitor's only signal that a listing is still
  real.

## Open questions

- Does this become a fourth top-level nav item, or sit under an audience
  menu? Nav is already at six items; a seventh may be the point at which
  the header needs restructuring rather than another entry.
- Do educator programs get published into `public/data/` as part of the
  data contract, or stay site-only? If published, `/data-access` and
  `llms.txt` need a new section.

## References

partner-scrape issue 33 (the data half: curated registry of educator-program
pages, LLM extraction typed `Professional Development / Conferences`, the
record shape, and the note that SDCOE's k12oms.org is robots-disallowed and
must not be scraped). Structural precedent: `src/pages/places/`,
`src/pages/clubs/`, `src/pages/teams/`.

---
status: pending
split_from: partner-scrape issue 34-audience-gaps-spanish-regional-accessibility.md
---

# Spanish-language listings: render `es` descriptions and add a bilingual facet

## Description

Website half of partner-scrape issue 34's Spanish-language section, split
out when the site moved to this repo. The site's equity framing promises to
serve underserved communities, but nothing on it is in Spanish. CMOD's
"Bilingual" events are already captured in the data, and SHPE's Noche de
Ciencias and Fleet's San Ysidro STEM Fair are natural hooks, so the content
exists — it just has no representation in the interface.

Partner-scrape owns carrying a `bilingual` / Spanish-available flag and
producing the translated `es` description text at export. This issue is the
display half: showing that text, and letting someone filter for it.

Worth stating plainly, because it changes the scope: rendering a Spanish
description on an otherwise English page is a half-measure. A visitor who
needs the Spanish description also needs the surrounding page to be
navigable. This issue should decide early whether it is delivering
per-record bilingual content or the first step of site localization, because
the two have very different sizes and the first can quietly become an
awkward permanent state.

## Proposed fix

- A Spanish-available facet in `src/components/OpportunityFilters.astro`,
  wired through `src/scripts/filters.js` like the existing facets, and
  participating in facet counts and clear behavior.
- An indicator on `src/components/OpportunityCard.astro` so bilingual
  offerings are visible while browsing.
- On the opportunity detail page, render the `es` description when present.
  Mark it with `lang="es"` so screen readers switch pronunciation — without
  that attribute a Spanish paragraph inside an English document is read with
  English phonetics, which defeats the purpose for exactly the users this is
  meant to serve.

## Open questions

- Per-record bilingual content, or full site localization? See above; this
  is the decision that sizes the work.
- If the `es` text is machine-translated at export, does it carry a marker
  saying so? Presenting an unreviewed translation as if a partner wrote it
  is a small honesty problem that gets larger as coverage grows.

## References

partner-scrape issue 34 (the data half: the `bilingual` flag, LLM
translation of `es` descriptions at export, and the open stakeholder call on
listing El Trompo in Tijuana as a binational entry). Related site work:
issue 51 (accessibility facet), the other audience-facing half of the same
upstream issue. Files: `OpportunityFilters.astro`, `OpportunityCard.astro`,
`src/scripts/filters.js`, `src/pages/opportunities/[slug].astro`.

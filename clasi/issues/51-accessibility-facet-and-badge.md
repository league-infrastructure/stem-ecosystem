---
status: pending
split_from: partner-scrape issue 34-audience-gaps-spanish-regional-accessibility.md
---

# Accessibility: a sensory-friendly filter facet and a card badge

## Description

Website half of partner-scrape issue 34's accessibility section, split out
when the site moved to this repo. Sensory-friendly and accessibility
programming is nearly invisible on the site: of three known recurring
offerings — Fleet Accessibility Mornings (3rd Saturday), the Natural History
Museum's ASD Mornings, and CMOD Sensory Friendly Mornings — only one
currently surfaces. Registering the two missing sources and adding the
`accessibility` / sensory-friendly flag to the record are partner-scrape's
work; this issue is what the site does once the flag exists.

A family that needs sensory-friendly programming cannot currently find it by
browsing. The listing has no facet for it and no visual marker, so the
information is only discoverable by reading individual descriptions. For the
audience this matters most to, that is effectively not published at all.

## Proposed fix

- Add an accessibility facet to `src/components/OpportunityFilters.astro`,
  driven by the record flag, wired through `src/scripts/filters.js` the same
  way the existing facets are. It should participate in the facet counts and
  the per-section and global clear behavior already implemented.
- Add a badge to `src/components/OpportunityCard.astro` and a row on the
  opportunity detail page so the marker is visible without opening a card.
- Decide the badge's wording from the source programs rather than inventing
  a label: the three known offerings describe themselves as
  sensory-friendly, ASD-friendly, and accessibility mornings, which are not
  synonyms. A single flag rendered with a generic label may overstate what a
  given program actually offers.

## Open questions

- One flag or several? A single "accessibility" facet is simpler to filter
  but flattens meaningful distinctions between sensory-friendly hours,
  ASD-specific programming, and physical accessibility. The answer likely
  depends on how partner-scrape models the flag, so this should be settled
  jointly rather than decided here.

## References

partner-scrape issue 34 (the data half: registering the two missing sources,
adding the accessibility flag to the record). Related site work:
issue 52 (Spanish-language listings), which is the other audience-facing
half of the same upstream issue. Files: `OpportunityFilters.astro`,
`OpportunityCard.astro`, `src/scripts/filters.js`,
`src/pages/opportunities/[slug].astro`.

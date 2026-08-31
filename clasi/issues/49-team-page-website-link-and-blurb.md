---
status: pending
split_from: partner-scrape issue 44-team-website-links-and-descriptions.md
---

# Team pages: always show the team's website link, and render an "about this team" blurb

## Description

Website half of partner-scrape issue 44 (stakeholder request, Eric,
2026-08-31), split out when the site moved to this repo. The data half —
importing sprint 013's 31 agent-discovered team websites and running the
extraction pass that produces the blurb text — stays in partner-scrape.
This issue covers only what the site does with that data.

**When a team has a website, its detail page must link to it.** Today the
link's visibility is inconsistent. Sprint 013 added three things: the card
badge, the "Has a Website" facet, and a dead-link guard on the detail page
that hides the link unless `website_status == "confirmed"`. Either that
guard or the data path is suppressing links that should show. The site-side
audit is: given a team record that has a `website` value, trace exactly
which condition in `src/pages/teams/[slug].astro` decides whether the anchor
renders, and confirm the guard is not hiding confirmed-good links. If the
suppression turns out to be upstream — teams arriving with an empty or
non-`confirmed` `website_status` — that finding belongs on partner-scrape's
half of 44 rather than here.

**Render the blurb once the pipeline produces it.** The extraction pass
stores a short "about this team" paragraph with provenance and a fetch date.
The site displays it on the team detail page with attribution ("from the
team's website"). A team whose site yields no usable text gets no blurb —
never a generated one, and never a placeholder. The empty state is simply
the absence of the block.

## Proposed fix

- Audit the `website_status` guard in `src/pages/teams/[slug].astro` and
  make the link render whenever a usable URL exists. Keep a guard against
  known-dead links, but do not let an unset status suppress a good link.
- Check the badge in `src/components/TeamCard.astro` and the "Has a Website"
  facet in `src/components/TeamFilters.astro` agree with whatever condition
  the detail page settles on — three different answers to "does this team
  have a website" is the underlying defect.
- Add the blurb block to the detail page: the paragraph, an attribution
  line, and the fetch date. Render nothing when the field is absent.

## Open questions

- Should the blurb's fetch date be shown to visitors, or only carried in the
  data? A visible "as of" date is honest about staleness on a dataset that
  refreshes roughly yearly, but it adds clutter to a short page.

## References

partner-scrape issue 44 (the data half: website import, extraction pass,
`teams/model.py`'s no-email-ever invariant); sprint 013 (website surfacing +
sponsor extraction); `src/pages/teams/[slug].astro`,
`src/components/TeamCard.astro`, `src/components/TeamFilters.astro`.

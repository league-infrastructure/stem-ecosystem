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

**Converge the three surfaces on one signal.** Once partner-scrape's
extraction pass lands, `teams.json` carries provenance and a fetch date —
evidence the pipeline actually reached the team's site. That is a better
basis for all three surfaces than each deriving its own answer, and adopting
it is the actual fix for the inconsistency rather than patching three
conditions to agree.

"We fetched this site" and "this link is worth showing a visitor" are not
the same claim, though — a parked or expired domain can return 200 and yield
no usable text, which is the case sprint 013's dead-link guard was added
for. partner-scrape's sprint 021 is emitting these as two distinct,
independently inspectable fields rather than collapsing them into a
blurb-present check, which makes the split clean:

- The badge, the "Has a Website" facet, and the detail-page link all key off
  the **usable-content** signal. One condition, three surfaces, no
  independent derivations.
- The **fetch-success** signal stays with the dead-link guard, which is the
  question that guard was actually asking.

So what goes away is the third independent derivation, not the guard. Wait
for the real field names before implementing; see References.

**Show the fetch date, quietly.** Resolved rather than left open: render it
alongside the attribution, in the register of the existing staleness cues
("from the team's website, as of Aug 2026"). Teams data refreshes roughly
yearly, so a visitor has no other way to judge whether a blurb still
describes the team. This is transparency about provenance, which is the same
reason the extraction pass refuses to generate a blurb it cannot source —
displaying a summary with silent authority would undercut that. A stale
blurb is also lower-stakes than a wrong date, so surfacing the date is
enough here; it does not need issue 56's don't-trust-the-data-layer
treatment.

## References

partner-scrape issue 44, rescoped to its data half (website import,
extraction pass, `teams/model.py`'s no-email-ever invariant) after sprint
019 removed the site from that repo; its sprint 021 carries that work.
Sprint 013 (website surfacing + sponsor extraction, and the dead-link guard
this issue audits). Site files: `src/pages/teams/[slug].astro`,
`src/components/TeamCard.astro`, `src/components/TeamFilters.astro`.

Before starting the audit, check partner-scrape's import ticket findings:
it reports the `website_status` distribution across current teams data, so
if links are missing because status was never set to `confirmed` rather than
because the guard is wrong, that is fixed upstream and this issue shrinks to
the blurb rendering.

The fetch-success and usable-content field names come from sprint 021's
extraction tickets and are not settled as of this writing — confirm them
against a real `teams.json` before wiring the three surfaces, rather than
guessing from this issue.

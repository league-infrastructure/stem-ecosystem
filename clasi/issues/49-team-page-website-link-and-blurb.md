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
- Add the blurb block to the detail page: `description`, the attribution
  line, and `description_fetched_at`. Render nothing unless
  `description_status == "generated"` — do not test `description` for
  non-emptiness, since the status field is the explicit signal and the
  string is `""` in both the `unavailable` and `none` cases.

**Converge the three surfaces on `website_status`.** The badge, the facet,
and the detail-page link all answer one question — does this team have a
website worth linking — so they should read one field, and `website_status`
is that field. The inconsistency is three independent derivations of the
same answer; the fix is deleting two of them, not adding a condition.

**Do not gate the link on the blurb.** Sprint 021 adds `description_status`
(`generated` / `unavailable` / `none`), and it is tempting to treat it as
the link's condition since a blurb proves the site had real content. That
would be wrong, and would recreate the exact defect this issue exists to fix.
`unavailable` means "nothing publishable came of it" — which covers a parked
domain, but equally covers a legitimate site that is image-heavy,
JS-rendered, or just terse. Those teams have a perfectly good website a
visitor wants.

The current numbers make the cost concrete: 52 of 278 teams are
`website_status == "confirmed"` and 80 carry a URL, while partner-scrape's
run generated descriptions for 24. Gating the link on a generated blurb
would hide a working website link from roughly 28 teams. A rare parked
domain slipping through is a much smaller harm than that, and it is
`website_status`'s job to catch anyway — if `confirmed` is admitting parked
domains, fix it there rather than proxying link-worthiness through an
unrelated signal.

So the mapping is:

- Badge, "Has a Website" facet, detail-page link → `website_status`.
- The blurb block → `description_status == "generated"`.
- The "as of" line → `description_fetched_at`.

Those are two independent questions and should stay two independent
conditions.

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

Field shape from sprint 021, confirmed 2026-08-31: `description`,
`description_status` (`generated` / `unavailable` / `none`),
`description_provenance` (`team_website` or `""`), and
`description_fetched_at` (ISO-8601 UTC, or `""`). `website_status` is
unchanged and stays independent. Verify against a real `teams.json` once
the pipeline has published these — the counts quoted above come from the
pre-extraction Aug 31 data plus partner-scrape's run report, not from a
published file carrying both fields.

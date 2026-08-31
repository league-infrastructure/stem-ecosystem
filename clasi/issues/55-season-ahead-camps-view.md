---
status: pending
split_from: partner-scrape issue 29-camp-session-extraction.md
---

# A season-ahead camps view

## Description

Website half of partner-scrape issue 29, split out when the site moved to
this repo. That issue calls a season-ahead view "the site-side payoff" of
camp session extraction, in one clause and without detail — this issue is
that clause, written down so it isn't lost when the data lands.

The behavior parents need: in January, when summer registration opens, they
are searching for "Summer 2027 camps." The current listing is organized
around what is happening soon, which is exactly wrong for camps. Camp
demand is seasonal and forward-looking, and the sessions that matter most
are the ones several months out. A listing sorted by imminence buries them.

**Blocked** on two upstream things: the `Camps` value in the opportunity
type taxonomy, and actual camp session records from the extraction work.
There is nothing to build against until those exist. Filed now so the site
side is tracked rather than rediscovered later.

## Open questions

- Is this a view toggle on `/opportunities` (alongside List, Calendar, Map),
  a filter preset, or its own route? A dedicated route is the most
  findable and the most linkable when the League promotes it seasonally.
- What defines "the season"? A fixed summer window, or a rolling
  next-N-months? Fixed windows match how families think but need annual
  maintenance.
- Does the view show sessions whose registration has not opened yet? The
  upstream issue raises the same question for data inclusion — "records for
  closed windows stay out (or display as 'opens ~X')" — and the display
  convention should be decided together with it rather than separately.

## References

partner-scrape issue 29 (camp session extraction, the marketing-page targets
and the three platform adapters), which names the season-ahead view as the
site-side payoff; the schema issue that adds the `Camps` taxonomy value.
Existing view-toggle implementation to extend or follow:
`src/pages/opportunities/index.astro` and `src/components/CalendarView.astro`.

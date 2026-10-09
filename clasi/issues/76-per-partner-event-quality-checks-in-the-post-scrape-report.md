---
status: pending
---

# Per-partner event-quality checks in the post-scrape report

## Description

The CMOD review (2026-10-08) found event-data problems a partner would
notice. All are detectable from our own scrape output, with no web calls
and no LLM:

- **Non-events listed as opportunities:** "Member's Only Hours", "Holiday
  Hours", "Museum Early Closure".
- **Duplicates:** the same event listed twice on the partner page, e.g. a
  generic and a specific title in the same slot ("Jimbo's Garden
  Workshop" and "Jimbo's Garden Workshop: Strawberry Banana Snake").
- **Date and link mismatch:** a "Member's Only Hours" dated Oct 13 links to
  the Oct 27 occurrence.
- **Past events in the "current" list:** `partners/<slug>/events.json`
  still lists events from Aug 30 onward (see issue 67).
- **Implausible age tags:** "Grades 6–8"/"Grades 9–12" on toddler events at
  a museum serving ages 0–10, and no K–5 tags.
- **Missing or wrong cost:** events included with $17 admission show
  blank or "Free". Space Night is ticketed ($20/$17/$13/$7).
- **Recurring sessions collapsed to one time:** Garden Workshop runs at
  11:00 and 2:00, and we keep one.

## Proposal

- Add a report step (part of the `updates` job, issue 75, or right after
  `scrape`) that computes these checks per partner and writes them to the
  same report/log.
- Report-only first. Fixes to extraction (a non-event filter, dedup, age
  plausibility, cost) become separate issues once the report shows how
  widespread each problem is.

## References

- `public/data/partners/<slug>/events.json`, `data/opportunities.json`
- Issues 67, 72, 75

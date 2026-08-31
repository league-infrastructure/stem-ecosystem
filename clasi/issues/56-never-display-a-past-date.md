---
status: pending
supersedes: docs/issues/005-no-past-dates-shown.md
---

# Never display a date earlier than today

## Description

Website half of this repo's original issue 005 (stakeholder report, Eric,
2026-07-20), reopened here after the data-side fix landed upstream.

The original complaint was that recurring and ongoing programs displayed
their first-ever occurrence, so an active weekly class that started in 2025
looked like a past event. That is fixed in the pipeline:
`partner_scrape/normalize/collapse.py`'s `_span()` now sets a collapsed
record's `date_start` to the next upcoming occurrence, and clamps to today
when a program is ongoing. Live data is down from 14 bad records to 1.

The residual is a gap the upstream clamp does not cover. `_span()` only
clamps to today when a last date reaches today, so a record with **no
`date_end` at all** keeps whatever start it has. Currently that is 1 of 350:
"2nd Innovation in Women's Health Pitch Competition", `date_start`
2024-12-01, no end date. It renders on the live site as a 2024 event.

The upstream question — why an undated-end 2024 record survives the export
filter — is partner-scrape's, and is filed there. This issue is the site's
own guarantee: the original report's closing line was "nothing on the site
should display a date earlier than today," and that should hold regardless
of what the data does. A display that faithfully renders whatever it is
handed will keep producing this bug every time a new upstream edge case
appears, and each one will be reported as a site defect, because to a
visitor it is one.

## Proposed fix

- A single date-formatting helper in `src/lib/helpers.ts` that every card,
  detail page, and calendar view uses, which never emits a date before
  today. An ongoing program with a past start reads as "available now"; the
  card does not silently invent a date.
- Audit the current call sites — the opportunity card, the detail page, and
  `CalendarView.astro` each format dates, and the fix is only a guarantee if
  it is not bypassed by one of them.
- Do not filter the record out. It is a real opportunity and the defect is
  in how its date reads, not in whether it belongs on the site.

## Open questions

- What does a record with no usable future date show instead? "Available
  now" is right for an ongoing program but wrong for a genuinely stale
  record that should have aged out upstream. There may be no honest display
  for the second case, which would argue for surfacing it as a data problem
  rather than papering over it.

## References

Original report: `docs/issues/005-no-past-dates-shown.md` (this issue
supersedes its website half). Upstream fix:
`partner_scrape/normalize/collapse.py` `_span()`, sprint-era next-occurrence
logic. The undated-end export gap is filed on partner-scrape as issue 61.
Site files: `src/lib/helpers.ts`, `src/components/OpportunityCard.astro`,
`src/pages/opportunities/[slug].astro`, `src/components/CalendarView.astro`.

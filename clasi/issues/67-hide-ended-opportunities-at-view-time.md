---
status: pending
related: clasi/issues/56-never-display-a-past-date.md
---

# Hide opportunities that have already ended, even when the build is stale

## Description

Stakeholder request (Eric, 2026-10-06): "can we not show items that are in
the past as coming up in the future? ... If we didn't scrape for a while,
it'd be nice to be able to turn that off."

The site is a static Astro build. `src/pages/opportunities/index.astro`
renders every record in `src/data/opportunities.json` and sorts it by
`date_start`, with no date filter at all. `deploy.yml` rebuilds only on a
push to `master`. The weekly scrape (`scheduled-run.yml`) writes to the
bucket and does not trigger a site build. So whatever the last build
contained stays on the live site indefinitely, and every event in it
eventually becomes a past event displayed as current.

Measured against today (2026-10-06), the checked-in snapshot
(`scrape-meta.json` `last_updated` 2026-09-02) breaks down as:

| Bucket | Count |
| --- | --- |
| `date_end` in the past (event is over) | 114 |
| `date_start` past, no `date_end`, start == scrape day 2026-09-02 | 18 |
| `date_start` past, no `date_end`, other | 6 |
| current or future | 222 |

So about a third of the opportunities listing is events that have already
happened.

The 18 "start == scrape day" records are **not** stale. They are ongoing
programs that the pipeline's `collapse._span()` clamped to "today" on the
day it ran. Hiding them would remove live programs. Issue 56 owns how those
read ("available now"). This issue covers only records that have a known
end that has passed.

## Proposed fix

Do the filtering when the page is viewed, not only when it is built, so a
stale build cannot show ended events.

1. **One "is this over?" predicate** in `src/lib/helpers.ts`:
   `isEnded(opp, now)` is true when `date_end` is set and before the start
   of `now`'s day (America/Los_Angeles). Records with no `date_end` are
   never "ended" by this rule (see issue 56). The build and the browser
   share this predicate, so they cannot disagree.
2. **Build-time drop.** `opportunities/index.astro`, `CalendarView.astro`,
   and the map data skip `isEnded(opp, buildTime)` records. Most stale
   records go away on every build.
3. **View-time hide (the actual guarantee).** Each card and calendar entry
   carries `data-date-end`. A small script in `src/scripts/filters.js`
   hides entries whose end date has passed when the page loads, and that
   hiding happens before the filter logic, so the "Showing N of M" count,
   the facet counts, and the map markers all reflect only visible items.
   This covers the "we didn't scrape for a while" case without anyone
   having to remember to rebuild.
4. **Detail pages** (`opportunities/[slug].astro`) stay, because links to
   them exist, but they show an "This event has ended" notice (also checked
   at view time) in place of the date block and are marked `noindex`.
5. **Scheduled rebuild.** Add a daily `schedule:` trigger to `deploy.yml`
   so the static HTML and `llms.txt` / the published JSON don't drift far
   from what the browser shows. This is cheap backup, not the guarantee.
6. **Off switch.** A single site config flag (e.g. `HIDE_ENDED = true` in
   `helpers.ts` or `config/`) turns steps 2-4 on or off, as the request
   asks.

## Open questions

- **Stale-data threshold.** Separately from per-event hiding, should the
  site react when the data itself is old (for example, `scrape-meta.json`
  `last_updated` more than N days ago)? Options: show a "listings last
  updated X days ago" banner, or also hide undated / ongoing records past
  some age. This may be what "turn that off" meant. Needs Eric's call.
- **Single-day events with no `date_end`.** Most of the 6 "other" records
  are probably one-day events where the scraper only captured a start. Do
  we treat `date_start` as the end for those (hide the day after), or
  leave it to the pipeline? Leaning toward: hide when `date_start` is past
  and the record's type is a single-occurrence type (competition, event),
  and leave programs/classes alone.
- **Deadline semantics.** For Work-based Learning records `date_end` is the
  application deadline (`data-access.astro`). Hiding after the deadline is
  probably right, but confirm.
- Does the agent-facing output (`llms.txt`, `/data-access` examples) apply
  the same filter at build time? Probably yes, for consistency.

## References

- Related: `clasi/issues/56-never-display-a-past-date.md`, which covers
  display of dates on records that stay listed. This issue covers hiding
  records that are over. 56's "do not filter the record out" applies to
  ongoing programs, which this issue also leaves listed.
- Related: `clasi/issues/57-consume-published-data-instead-of-being-written-into.md`.
  If the site moves to pulling bucket data at build time, the daily rebuild
  in step 5 also picks up fresh scrapes.
- Site files: `src/pages/opportunities/index.astro`,
  `src/pages/opportunities/[slug].astro`, `src/components/OpportunityCard.astro`,
  `src/components/CalendarView.astro`, `src/scripts/filters.js`,
  `src/lib/helpers.ts`, `.github/workflows/deploy.yml`.

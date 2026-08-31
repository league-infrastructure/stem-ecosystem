---
status: done
---

# Filters: per-section "Clear" links + a global "Clear all filters"

**Reported by stakeholder (Eric), 2026-07-20, from the live Opportunities page.**

Each filter section (Areas of Interest, Age/Grade, Cost, Opportunity Type,
Time of Day, …) needs a way to reset **just that section** back to default
(nothing selected). It should be a plain text **link** at the bottom of the
section — not a button.

Plus a single **"Clear all filters"** link at the bottom of the whole filter
list that resets every section to default.

- Component: `src/components/OpportunityFilters.astro` (markup) +
  `src/scripts/filters.js` (state reset + re-filter).
- Per-section clear resets only that facet group's checkboxes/inputs and
  re-runs filtering; global clear resets all.

## Resolution

Resolved. `OpportunityFilters.astro` carries `data-clear-section` and
`data-clear-all` hooks and `src/scripts/filters.js` implements the resets.

Verified 2026-08-31 during the repo split, when this repo's issues moved
from `docs/issues/` into `clasi/issues/`. Numbers 001-006 are this site's own
original sequence and are unrelated to the shared partner-scrape numbering
used by issues 49 and up.

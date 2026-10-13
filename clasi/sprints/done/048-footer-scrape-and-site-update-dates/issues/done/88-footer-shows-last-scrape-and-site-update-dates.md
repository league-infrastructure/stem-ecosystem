---
status: done
sprint: 048
tickets:
- 048-001
---

# Footer shows the last scrape date and the site update date

## Description

Stakeholder request (Eric, 2026-10-13): "update the footer of the site to
include the scrape date, the last scrape date, and the last update date.
When was the site updated? When was the site scraped?"

Today the footer shows only "Last updated: <date>", taken from
`scrape-meta.json` `last_updated`, which is really the scrape time. Example
for 2026-10-13:
- the last scrape was 2026-10-12T10:28:58Z (Oct 12, 3:28 am PT);
- the site was built and deployed 2026-10-13T21:28Z.

## Desired result

- The footer shows both dates, clearly labelled. For example: "Events
  scraped Oct 12, 2026 · Site updated Oct 13, 2026".
  - **Scrape date:** `scrape-meta.json` `last_updated` (the fetched data).
  - **Site update date:** the build time, stamped at `astro build` (e.g. a
    build-time constant), not the visitor's clock.
- Format dates in America/Los_Angeles so a 3 am PT scrape isn't shown as
  the next UTC day. Showing the time on hover (a `<time datetime=…>`
  `title`) is a nice-to-have.
- Small, muted footer text, as today, on every page.
- Keep `/data-access`, `/for-agents` and `llms.txt` consistent if they
  mention "last updated".

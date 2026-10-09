---
status: in-progress
sprint: '043'
tickets:
- 043-002
- 043-003
- 043-008
- 043-009
---

# Weekly scrape of partner home, About, and Contact pages

## Description

Stakeholder direction (Eric, 2026-10-08): add partners' About and Contact
pages (and the home page) to the scraper, fetched weekly, so changes to
the information in our hand-curated partner records can be detected
cheaply from our own scrape data.

Today the scraper fetches only event-related pages (calendar APIs, event
pages, sitemaps). The fetch cache had CMOD's event pages but not its home
or About page, and the curated `src/data/partners.json` is never refreshed
from anything.

## Proposal

- A new job, `profiles` (`partner-scrape profiles` / `run-job profiles`),
  scheduled **weekly** in the container crontab.
- It covers every partner in `partners.json` that has a `website`.
  - Fetch the home page and record redirects (issue 73).
  - Find the About and Contact pages from nav links (about, our story, who
    we are, mission, contact, visit) or the sitemap, and fetch them.
  - Respect `robots.txt` and rate limits, and fall back to headless, using
    the existing fetcher and cache.
- Extract structured facts **without an LLM**:
  - `<title>` and `og:site_name`;
  - schema.org JSON-LD `Organization`/`LocalBusiness`/`Museum` (name,
    address, telephone, email, `sameAs` social links, logo);
  - footer social links;
  - `mailto:`/`tel:` links.
- Write a per-partner **profile snapshot** (facts, page URLs, a content
  hash per page, fetch time) to the bucket, e.g. `data/profiles.json` or a
  non-public prefix; see open questions.
- Content hashes let later steps skip partners whose pages did not change.

## Cost

Roughly 3 pages × ~211 partners a week, mostly served from the fetch
cache's conditional requests. No LLM in this job.

## Open questions

- Should the profile snapshot be public (under `data/`) or private?
- Should partners without a website be skipped, or listed in the report?

## References

- `src/data/partners.json` (roster, 211 entries, hand-curated)
- `scraper/partner_scrape/fetch/*`, `scraper/docker/crontab`

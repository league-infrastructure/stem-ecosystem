# Issues

Website issues for the SD STEM Ecosystem site. Open issues sit in this
directory; resolved ones move to `done/`.

Each file is `NN-kebab-slug.md` with YAML frontmatter carrying `status:`
(`pending` or `done`), an H1 title, and `##` sections — typically
`Description`, an optional `Proposed fix` and `Open questions`, and a closing
`References`.

## Scope

This repo owns the website and the data it publishes. The scraping pipeline
lives in [partner-scrape](https://github.com/league-infrastructure/partner-scrape)
and has its own issue set. The dividing line:

- **Here**: pages, components, filters, rendering, site UX, the published
  data contract's presentation (`/data-access`, `/for-agents`, `llms.txt`),
  and the hand-curated roster `src/data/partners.json`.
- **There**: scraping, adapters, extraction, enrichment, source registries,
  taxonomy, and everything that generates the other data files.

Several issues here were split out of partner-scrape issues when the site
moved into this repo; those carry a `split_from:` field naming the original.
An issue whose data half is still upstream says so, and names what it is
waiting on.

## Numbering

Issues 49 and up share a single sequence with partner-scrape, so a number
means the same issue in both repos and cross-references are unambiguous.
This repo mints from 49; partner-scrape mints from 60.

Issues 001-006 in `done/` predate that arrangement — they are this site's own
original sequence from `docs/issues/`, and their numbers do **not**
correspond to partner-scrape issues 1-6.

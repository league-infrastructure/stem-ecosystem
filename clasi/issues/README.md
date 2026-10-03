# Issues

Issues for the SD STEM Ecosystem project: both the website (repo root) and
the scraper (`scraper/`). Open issues sit in this directory; resolved ones
move to `done/`. Issues claimed by a sprint live in that sprint's
`issues/` directory under `clasi/sprints/`.

Each file is `NN-kebab-slug.md` with YAML frontmatter carrying `status:`
(`pending` or `done`), an H1 title, and `##` sections — typically
`Description`, an optional `Proposed fix` and `Open questions`, and a closing
`References`.

## Scope

One repo, two halves. Issues can touch either or both:

- **Site** (repo root): pages, components, filters, rendering, site UX, the
  published data contract's presentation (`/data-access`, `/for-agents`,
  `llms.txt`), and the hand-curated roster `src/data/partners.json`.
- **Scraper** (`scraper/`): scraping, adapters, extraction, enrichment,
  source registries, taxonomy, and everything that generates the published
  data in the `jtl-stem-ecosystem-scrape` bucket.

The scraper lived in the separate
[partner-scrape](https://github.com/league-infrastructure/partner-scrape)
repo until 2026-10-02, when it moved into `scraper/` here. That repo is now
archived. Its issues and sprint history (sprints 001-038) came with it.
Some site issues carry a `split_from:` field naming a partner-scrape issue
they were split out of; those numbers refer to the same issue here.

## Numbering

There is one issue sequence. **The next new issue is 67.**

- **001-006** (in `done/`): the site's original sequence from
  `docs/issues/`, older than the shared numbering. Not the same issues as the
  scraper's early 01-06.
- **01-48**: scraper issues from partner-scrape.
- **49-58**: site issues, numbered when the two repos shared one sequence.
- **60-62**: scraper issues (sprint-scoped, under `clasi/sprints/`).
- **63-65**: scraper issues from sprint 038. They were created in
  partner-scrape as 49, 50 and 51, colliding with site issues 49-51, and
  were renumbered when the repos merged:

  | Old (partner-scrape) | New |
  |---|---|
  | 49 move scrape cache to DigitalOcean Spaces | 63 |
  | 50 move cache and data to DigitalOcean Spaces | 64 |
  | 51 make partner-scrape a pip-installable package | 65 |

  partner-scrape commit messages still use the old numbers.
- **66**: the repo consolidation itself.

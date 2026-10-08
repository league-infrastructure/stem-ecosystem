---
status: in-progress
related: clasi/issues/67-hide-ended-opportunities-at-view-time.md
sprint: 039
tickets:
- 039-001
- 039-002
- 039-003
- 039-004
- 039-005
- 039-006
- 039-007
---

# Build the site from the bucket and stop committing scraped data

## Description

Stakeholder direction (Eric, 2026-10-07): the site is static, so the
scraped data does not belong in Git. "Make it so that your site builder
just goes to the bucket, immediately gets those JSON files, and just uses
them." Snapshots and backups of the data are out of scope; they will be
handled separately.

Today the scraper publishes to `s3://jtl-stem-ecosystem-scrape/data/`, and
`scripts/fetch-data.sh` copies that output into tracked repo files, which
someone must then commit. The last data commit was 2026-09-02. A single
refresh touches about 570 files, and 354 of the 422 per-partner files
differ only in `generated_at`. `deploy.yml` builds whatever is committed and
never fetches anything.

### Generated files now tracked in Git, which must leave the repo

- `src/data/opportunities.json`, `scrape-meta.json`, `ads.json`,
  `yield-history.json`, `teams.json`, `places.json`, `clubs.json`
- `public/data/` (`partners.json` envelope, `partners/<slug>/*.json`,
  `teams.json`, `places.json`, `clubs.json`)
- `public/images/opportunities/`

`src/data/partners.json` is the hand-curated roster. It stays in Git and is
never overwritten.

### How the site consumes them

- Astro pages and components statically `import` `src/data/*.json`
  (`index.astro`, `opportunities/*`, `partners/*`, `teams/*`, `places/*`,
  `clubs/*`, `Footer.astro`, the `*Filters.astro` components).
- `public/data/**` is served at `/data/...`. This is a documented public
  contract on `/data-access`, `/for-agents` and `llms.txt`.
- Opportunity images are served at `/images/opportunities/<file>`
  (`src/lib/helpers.ts`).

## Decisions (stakeholder, 2026-10-07)

1. **Make the bucket's `data/` prefix publicly readable**, so the build
   fetches it over plain HTTPS with no credentials. `cache/` stays private.
   The scraper's key is scoped and gets AccessDenied on bucket ACL and
   policy operations, so the scraper should publish `data/` objects with a
   `public-read` ACL. If the scoped key cannot set object ACLs, the
   fallback is a bucket policy on `data/*` set by the stakeholder in the DO
   console. The planner should verify which one works.
2. **Keep serving `/data/...` and `/images/opportunities/...` from the
   site.** The build downloads them into the built output, so the public
   URLs and the agent docs stay unchanged. Nothing is committed.

## Desired outcome

- The build (local `npm run dev` / `npm run build` and CI `deploy.yml`)
  fetches the published data from the bucket over HTTPS before Astro reads
  it, with no secrets and no `aws` CLI. It fails loudly if the fetch fails
  or a referenced image is missing; today's integrity check is kept.
- The generated files above are removed from Git and ignored. A fresh
  clone builds with only network access.
- `scripts/fetch-data.sh`, the README and the `/data-access` wording are
  updated to match. The `--local <dir>` mode for running against a local
  scraper output dir is worth keeping.
- The scraper's bucket writes for `data/` are publicly readable, and the
  existing objects are made readable once.
- Consider (or split out): having `scheduled-run.yml` trigger a site deploy
  after a successful scrape, so the live site picks up new data without a
  commit. This also helps issue 67.

## References

- `scripts/fetch-data.sh`
- `.github/workflows/deploy.yml`, `.github/workflows/scheduled-run.yml`
- `scraper/partner_scrape/storage.py` (bucket Store)
- `src/pages/data-access.astro`, `src/pages/for-agents.astro`,
  `src/pages/llms.txt.ts`, `src/lib/helpers.ts`

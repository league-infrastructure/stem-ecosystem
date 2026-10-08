# SD STEM Ecosystem

The production website for [sdstemecosystem.org](https://www.sdstemecosystem.org) — a
directory of San Diego STEM learning opportunities, partner organizations, robotics teams,
places and clubs. Built with Astro, deployed as a static site to GitHub Pages.

The site also **publishes** a public, no-auth data contract at `/data/...` (and event images at
`/images/opportunities/...`) consumed by other tools and by LLM agents (see `/data-access` and
`/for-agents` on the live site). Those files are not committed here: they are fetched from the
scraper's bucket at build time (see below). The public URLs are unchanged.

## Development

```bash
npm install
npm run dev        # http://localhost:4322
npm run build      # static output to dist/
npm run preview    # serve the built output
npm test           # fetch-data script tests
```

`dev`, `start` and `build` first fetch the scraped data **only if it is missing**, so local
development reuses files you already have. Run `npm run fetch-data` to refresh them.

## The scraper

The data comes from the scraper in [`scraper/`](scraper/), a Python package (`partner_scrape`)
that visits partner organizations' sites and APIs, extracts and enriches their events, programs
and internships, and publishes the result to the DigitalOcean Spaces bucket
`s3://jtl-stem-ecosystem-scrape/` (`cache/` and `data/`). It lived in the separate
[partner-scrape](https://github.com/league-infrastructure/partner-scrape) repo until
2026-10-02; that repo is archived. See [`scraper/README.md`](scraper/README.md).

```bash
dotconfig load prod                 # assemble .env at the repo root (config/ is SOPS-encrypted)
cd scraper
uv sync
set -a; source ../.env; set +a      # DO_SPACES_*, ANTHROPIC_API_KEY, ...
uv run partner-scrape --site-dir ..   # full run; --source <id> for one source, --dry-run to preview
uv run pytest                       # offline test suite
```

Scraping is not run by GitHub Actions (the scheduled workflow is retired); it runs on a schedule from a container with built-in cron; see [`scraper/docker/README.md`](scraper/docker/README.md).

## Where the data comes from

Site content is **not** edited here, and the scraped data is **not committed to git**. The
bucket's `data/` prefix (`s3://jtl-stem-ecosystem-scrape/data/`) is the source of truth, and it
is **public**: anonymous HTTPS reads work with no credentials (the scraper sets public-read ACLs
on that prefix; `cache/` stays private). `scripts/fetch-data.mjs` downloads it into the
gitignored build inputs:

```bash
npm run fetch-data                           # always refresh from the bucket over HTTPS
node scripts/fetch-data.mjs --local scraper/data   # or copy from a local scraper data dir
node scripts/fetch-data.mjs --if-missing     # no-op when data is already present (used by dev/build)
SITE_DATA_BASE_URL=https://... npm run fetch-data  # override the source URL
```

- Local `npm run dev` / `npm run build` fetch only if the data is missing; use
  `npm run fetch-data` to pick up a newer scrape.
- CI (`deploy.yml`, `build.yml`) **always** runs `npm run fetch-data` before building, so every
  deploy ships the latest published data. Re-run the deploy after a scrape to publish it.
- The fetch is staged and validated before anything is replaced, so a failed fetch leaves the
  previous data intact. It never writes the hand-curated `src/data/partners.json`.

| Path | Owner | Notes |
|---|---|---|
| `src/data/partners.json` | **Humans — edit here** | Hand-curated partner roster. A pipeline *input*, not an output. |
| `src/data/opportunities.json`, `teams.json`, `places.json`, `clubs.json`, `ads.json`, `scrape-meta.json` | Pipeline | Fetched from the bucket; gitignored; do not hand-edit. |
| `src/data/yield-history.json` | Pipeline | Fetched, gitignored. Per-run state used to detect source yield regressions. |
| `public/data/**` | Pipeline | Fetched, gitignored. The published data contract (partner roster + per-partner event files). |
| `public/images/opportunities/` | Pipeline | Fetched, gitignored. Self-hosted event images, content-hash named. |
| `public/images/logos/` | Pipeline | Partner logos. |

The curated roster lives here because the scraper reads it from its `--site-dir`, which is
this repo's root. Keeping a second copy elsewhere is what caused runs to join against a stale
roster and silently drop partner geocodes and logos.

## Deployment

**Production** — `.github/workflows/deploy.yml` builds and deploys to GitHub Pages **manually only** (Actions -> Deploy -> Run workflow, or `gh workflow run deploy.yml`); there is no push or scheduled trigger. It fetches the data first (`npm run fetch-data`). It passes `--site` and `--base` from `actions/configure-pages`, so absolute
URLs in `llms.txt` and `/for-agents` derive from whatever origin actually serves the build
(see `src/pages/llms.txt.ts`). Nothing hardcodes a domain.

**Beta preview** — a Docker container serving a production build, for reviewing a change at a
real URL before it ships:

```bash
cp docker/.env.example docker/.env    # set SITE_HOSTNAME and SITE_URL
docker compose -f docker/docker-compose.yml up -d --build
```

`SITE_URL` is baked in at build time; if it does not match how the beta is actually reached,
the beta will advertise data URLs that do not resolve.

## Fonts and assets

Fonts live in `src/fonts/`, not `public/fonts/`, so Vite emits base-aware hashed assets.
Absolute `/fonts/...` paths break under a non-root base path — don't reintroduce them.

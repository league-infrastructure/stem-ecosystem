# SD STEM Ecosystem

The production website for [sdstemecosystem.org](https://www.sdstemecosystem.org) — a
directory of San Diego STEM learning opportunities, partner organizations, robotics teams,
places and clubs. Built with Astro, deployed as a static site to GitHub Pages.

This repo is also the **data publication** point: the JSON under `public/data/` is a public,
no-auth data contract consumed by other tools and by LLM agents (see `/data-access` and
`/for-agents` on the live site).

## Development

```bash
npm install
npm run dev        # http://localhost:4322
npm run build      # static output to dist/
npm run preview    # serve the built output
```

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

`.github/workflows/scheduled-run.yml` runs the scraper weekly (Mondays 13:00 UTC).

## Where the data comes from

Site content is **not** edited here: the scraper's output in the bucket is the source. Pulling
it into the site is currently a manual step:

```bash
set -a; source .env; set +a         # DO_SPACES_ACCESS_KEY / DO_SPACES_SECRET_KEY
scripts/fetch-data.sh               # sync from the bucket (default; needs the aws CLI)
scripts/fetch-data.sh --local scraper/data   # or copy from a local scraper data dir
```

Review and commit the result. The GitHub workflows do not fetch yet (build-time fetch is a
planned follow-up). The script never overwrites the hand-curated `src/data/partners.json`.

| Path | Owner | Notes |
|---|---|---|
| `src/data/partners.json` | **Humans — edit here** | Hand-curated partner roster. A pipeline *input*, not an output. |
| `src/data/opportunities.json`, `teams.json`, `places.json`, `clubs.json`, `ads.json`, `scrape-meta.json` | Pipeline | Regenerated each run; do not hand-edit. |
| `src/data/yield-history.json` | Pipeline | Per-run state used to detect source yield regressions. |
| `public/data/**` | Pipeline | The published data contract (partner roster + per-partner event files). |
| `public/images/opportunities/` | Pipeline | Self-hosted event images, content-hash named. |
| `public/images/logos/` | Pipeline | Partner logos. |

The curated roster lives here because the scraper reads it from its `--site-dir`, which is
this repo's root. Keeping a second copy elsewhere is what caused runs to join against a stale
roster and silently drop partner geocodes and logos.

## Deployment

**Production** — `.github/workflows/deploy.yml` builds and deploys to GitHub Pages on every
push to `master`. It passes `--site` and `--base` from `actions/configure-pages`, so absolute
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

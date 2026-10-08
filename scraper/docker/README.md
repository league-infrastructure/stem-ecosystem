# partner-scrape Docker image

A one-shot container that runs a full scrape (scrape -> enrich ->
normalize -> export) and exits. Cache and output go to the DigitalOcean
Spaces bucket `jtl-stem-ecosystem-scrape` (`cache/` and `data/`), so the
container needs no volumes and can run anywhere: locally, on a droplet,
or as a DO App Platform job.

The image is based on Microsoft's Playwright Python image, so headless
Chromium is included for the sources with
`fetch_strategy = "headless"`.

## Build

From the **repo root** (the build copies `src/data/partners.json` as
well as `scraper/`):

```bash
docker build -f scraper/docker/Dockerfile -t partner-scrape .
```

`Dockerfile.dockerignore` keeps the context to just the files the build
needs; `node_modules/`, `dist/` and `.env` are never sent.

The partner roster is baked in at build time, so rebuild after
`src/data/partners.json` changes. When bumping `playwright` in
`scraper/uv.lock`, bump the base image tag in the Dockerfile to match.

## Run

Secrets are passed at run time, never baked into the image. The
assembled `.env` (`dotconfig load prod`) has everything:

```bash
docker run --rm --ipc=host --env-file .env partner-scrape
```

Required variables:

| Variable | Purpose |
|---|---|
| `DO_SPACES_ACCESS_KEY` | Spaces bucket access key |
| `DO_SPACES_SECRET_KEY` | Spaces bucket secret key |
| `ANTHROPIC_API_KEY` | LLM enrichment (not needed with `--no-enrich`) |

`DO_SPACES_ENDPOINT` defaults to `https://sfo3.digitaloceanspaces.com`.
`SCRAPE_CACHE_DIR` and `PARTNER_SCRAPE_DATA_DIR` default to the bucket;
set them to override.

`--ipc=host` (or `--shm-size=1g`) gives Chromium enough shared memory;
Docker's 64MB default can crash it on heavy pages.

Arguments after the image name go to the `partner-scrape` CLI:

```bash
# Smoke-test one source without writing anything or calling the LLM
docker run --rm --ipc=host --env-file .env partner-scrape \
  --source sandiego-cv-aopsacademy --dry-run --no-enrich

# Other subcommands
docker run --rm --env-file .env partner-scrape teams
docker run --rm --env-file .env partner-scrape directory
```

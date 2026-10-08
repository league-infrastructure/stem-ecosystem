# partner-scrape Docker image

A long-running container that runs the scraper on a schedule using
[supercronic](https://github.com/aptible/supercronic). Cache and output go
to the DigitalOcean Spaces bucket `jtl-stem-ecosystem-scrape` (`cache/` and
`data/`), so the container needs no volumes and can run anywhere: locally,
on a droplet, or any Docker host. Headless Chromium is included (Microsoft
Playwright Python base image) for `fetch_strategy = "headless"` sources.

## Build

From the **repo root** (the build copies `src/data/partners.json` as well as
`scraper/`):

```bash
docker build -f scraper/docker/Dockerfile -t partner-scrape .
```

The partner roster (`src/data/partners.json`) is **baked in at build time**:
rebuild and redeploy after the roster changes. When bumping `playwright` in
`scraper/uv.lock`, bump the base image tag in the Dockerfile to match.

## Secrets

Secrets are passed at run time as one base64 bundle, `SCRAPER_SECRETS_B64`,
never baked into the image. Build it from the assembled `.env`
(`dotconfig load prod`):

```bash
SCRAPER_SECRETS_B64=$(scraper/docker/make-secrets.sh)   # optional arg: path to a .env
```

**Never echo or log the bundle**; it contains every key. `make-secrets.sh`
warns (key names only) about missing required keys. Variables set directly
in the container environment (`-e NAME=value`) override bundle values.

Required per job:

| Job | Required variables |
|---|---|
| scrape | `DO_SPACES_ACCESS_KEY`, `DO_SPACES_SECRET_KEY`, `ANTHROPIC_API_KEY` (waived with `--no-enrich` or `--dry-run`), `LEAGUESYNC_API_KEY` |
| teams | `DO_SPACES_ACCESS_KEY`, `DO_SPACES_SECRET_KEY`, `ANTHROPIC_API_KEY` (waived with `--no-sponsors --no-descriptions`), `TBA_KEY` |
| directory | `DO_SPACES_ACCESS_KEY`, `DO_SPACES_SECRET_KEY` |

`ROBOTEVENTS_KEY` is optional. A job with missing variables logs
`FAILURE job=X missing=NAMES` (names only) and does not run.

## Run (long-lived)

```bash
docker run -d --name partner-scrape --restart unless-stopped --ipc=host \
  -e SCRAPER_SECRETS_B64="$SCRAPER_SECRETS_B64" partner-scrape
```

With no arguments the container starts supercronic, which prints the
schedule at startup. `--ipc=host` (or `--shm-size=1g`) gives Chromium enough
shared memory; Docker's 64MB default can crash it.

## Schedule

Times are America/Los_Angeles (see `scraper/docker/crontab`). Jobs are
spaced days apart so a long scrape cannot overlap the next job.

| Job | When |
|---|---|
| `scrape` | Monday and Thursday 03:00 |
| `teams` | Wednesday 03:00 |
| `directory` | Saturday 03:00 |

## Manual runs

```bash
# In the running container
docker exec partner-scrape run-job scrape
docker exec partner-scrape run-job teams
docker exec partner-scrape run-job directory

# One-shot container (extra args go to partner-scrape)
docker run --rm --ipc=host -e SCRAPER_SECRETS_B64="$SCRAPER_SECRETS_B64" \
  partner-scrape run-job scrape --source fleet-science-center --dry-run --no-enrich
```

Legacy one-shot usage still works: any other arguments go straight to the
`partner-scrape` CLI, e.g. `docker run --rm --ipc=host -e ... partner-scrape
--source <id> --dry-run --no-enrich` (secrets are not preflight-checked in
that form).

## Logs

```bash
docker logs -f partner-scrape
```

Each job logs UTC-timestamped lines: `START job=X`, then
`SUCCESS job=X exit=0 duration=Ns` or `FAILURE job=X exit=N duration=Ns`.
Values of secrets are never logged.

## Updating

Rebuild the image, then stop and remove the old container and start a new
one with the `docker run -d` command above:

```bash
docker build -f scraper/docker/Dockerfile -t partner-scrape .
docker rm -f partner-scrape
```

## Site rebuild

The container only refreshes the bucket. Publishing the site is separate and
manual: Actions -> Deploy -> Run workflow, or
`gh workflow run deploy.yml --repo league-infrastructure/stem-ecosystem`.

# partner-scrape Docker image

A long-running container that runs the scraper on a schedule using
[supercronic](https://github.com/aptible/supercronic). Cache and output go
to the DigitalOcean Spaces bucket `jtl-stem-ecosystem-scrape` (`cache/` and
`data/`), so the container needs no volumes and can run anywhere: locally,
on a droplet, or any Docker host. Headless Chromium is included (Microsoft
Playwright Python base image) for `fetch_strategy = "headless"` sources.

## Build

From the **repo root** (only `scraper/` is copied into the image):

```bash
docker build -f scraper/docker/Dockerfile -t partner-scrape .
```

The partner roster is **not** baked into the image: each run reads the
per-partner records (`data/partners/<slug>/partner.json`) from the bucket, so
roster edits (`partner-scrape partners put|add`) take effect on the next run
without a rebuild. When bumping `playwright` in
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
| profiles | `DO_SPACES_ACCESS_KEY`, `DO_SPACES_SECRET_KEY` |
| updates | `DO_SPACES_ACCESS_KEY`, `DO_SPACES_SECRET_KEY`, `ANTHROPIC_API_KEY` (waived **only** with `--no-llm`; `--dry-run` still calls Haiku) |

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
| `profiles` | Sunday 03:00 |
| `updates` | Sunday 05:00 (after `profiles`) |

## Manual runs

```bash
# In the running container
docker exec partner-scrape run-job scrape
docker exec partner-scrape run-job teams
docker exec partner-scrape run-job directory
docker exec partner-scrape run-job profiles
docker exec partner-scrape run-job updates --dry-run

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

### Run logs in the bucket (`logs/`)

Every `run-job` run (scheduled or manual, including failed and
preflight-failed runs) also tees its full stdout+stderr to a temp file and,
on exit, uploads it to `logs/<type>/<UTC ts>-<job>.log` in the bucket
(`type` is `scrape`, `teams`, `directory`, `profiles` or `updates`). One JSON line is appended to `logs/index.jsonl` with `job`,
`start`, `end`, `exit_code`, `duration_s`, `log` (path) and, when parseable
from the output, `events_written`, `sources` and `errors`.

- `logs/` is written **private** (no public-read ACL), unlike `data/`.
  Location override: `PARTNER_SCRAPE_LOGS_DIR` (local dir or `s3://...`).
- Values of secret-looking environment variables (names containing KEY,
  SECRET, TOKEN, PASSWORD) are redacted from the uploaded log.
- An upload failure prints a `WARNING ... log upload failed` line on stdout
  and never changes the job's exit code.
- The index append is read-modify-write (not atomic); that is fine because
  jobs are serial and days apart.

## Profiles and updates jobs

**`profiles`** (no LLM) fetches each partner's home, About and Contact pages
politely and writes a private snapshot per partner to
`history/profiles/<slug>/profile.json`. Flags: `--slug S`, `--limit N`.

**`updates`** compares each partner record with its latest snapshot, asks
Claude Haiku for corrections, and applies only policy-approved changes
through the partner writer (actor `haiku`), then re-consolidates
`data/partners.json`. Flags:

| Flag | Effect |
|---|---|
| `--dry-run` | Report only: still calls Haiku to show real proposals, but writes no records, no consolidate, no state. |
| `--no-llm` | Flags only; never calls Haiku (no `ANTHROPIC_API_KEY` needed). |
| `--max-changes N` | Safeguard: at most N records changed per run; the rest are reported as deferred. |
| `--slug S` | Only this partner. |
| `--all` | Examine every partner, not just those whose snapshot changed. |

Safeguards: only an allowlist of fields can change automatically (name,
website, phone, email, location, social links, description); logos,
coordinates, organization type, id and slug never do. Run `updates --dry-run`
first when trying something new.

### Where things land (all private, under the bucket)

| What | Where |
|---|---|
| Updates report (flags, applied/deferred changes, redirects, event-quality checks) | `history/updates/<ts>.json`, and printed in the run log |
| Run logs | `logs/profiles/` and `logs/updates/`, indexed in `logs/index.jsonl` |
| Profile snapshots | `history/profiles/<slug>/profile.json` |
| Change log of every record write | `history/partners/changes.jsonl` |
| Prior record versions | `history/partners/<slug>/<UTC stamp>-partner.json` |

### Inspecting and undoing a Haiku change

1. Find it: lines in `history/partners/changes.jsonl` with
   `"actor": "haiku"` give `slug`, `ts`, `changed` fields and `archived`
   (the key of the record as it was just before the change).
2. Compare `archived` (the old record) with the current one
   (`partner-scrape partners get <slug>`).
3. Restore: save the archived JSON to a file and run
   `partner-scrape partners put <slug> restored.json` (this validates, writes
   the record and archives the current one again). Then run
   `partner-scrape partners consolidate` to refresh `data/partners.json`.

## Updating

Rebuild the image, then stop and remove the old container and start a new
one with the `docker run -d` command above:

```bash
docker build -f scraper/docker/Dockerfile -t partner-scrape .
docker rm -f partner-scrape
```

## Swarm deployment

Production runs as the `stem-ecosystem` stack on the League Docker swarm,
defined by `docker-compose.yml` at the repo root. Run everything below from
the repo root. The swarm nodes are x86_64 and the `swarm1`/`swarm2` Docker
contexts point at them. Throughout, `<ver>` is the repo tag without the
leading `v` (tag `v0.20261008.3` -> `0.20261008.3`).

1. **Build and push** the image for `linux/amd64` (an Apple-silicon Mac is
   arm64, so a plain `docker build` would produce an image the swarm cannot
   run):

   ```bash
   docker buildx build --platform linux/amd64 \
     -f scraper/docker/Dockerfile \
     -t ghcr.io/league-infrastructure/stem-ecosystem-scraper:<ver> \
     --push .
   ```

   The ghcr package is public and linked to the repo, so the swarm needs no
   pull token (no `--with-registry-auth`). The first time a new package is
   pushed, set it to public and link it to the repo in the ghcr package
   settings.

2. **Create the secret** (once). The bundle is piped straight into the swarm
   and never written to disk or shown:

   ```bash
   scraper/docker/make-secrets.sh | \
     docker --context swarm1 secret create stem-ecosystem_scraper_secrets -
   ```

   The container reads it from `/run/secrets/stem-ecosystem_scraper_secrets`
   (`SCRAPER_SECRETS_FILE`). Swarm secrets are **immutable**: to change one,
   create a new secret under a new name, e.g.
   `stem-ecosystem_scraper_secrets_v2`, update the secret name (in both the
   service's `secrets:` list, the `SCRAPER_SECRETS_FILE` path, and the
   top-level `secrets:` block) in `docker-compose.yml`, redeploy (step 4),
   then remove the old secret with `docker --context swarm1 secret rm`.

3. **Check the release** against the live swarm:

   ```bash
   ~/proj/league/infrastructure/league-network/scripts/check-release . --tag v<ver> --live
   ```

   Its warning about the `/dev/shm` tmpfs volume is a known false positive
   (Chromium needs the 1 GiB tmpfs; see comments in `docker-compose.yml`).

4. **Deploy**:

   ```bash
   TAG=<ver> docker --context swarm1 stack deploy -c docker-compose.yml stem-ecosystem
   ```

5. **Verify**:

   ```bash
   docker --context swarm1 service ps stem-ecosystem_scraper
   docker --context swarm1 service logs stem-ecosystem_scraper
   ```

   The task should be `Running`; the logs show the supercronic schedule.

6. **Run a job by hand.** `service ps` shows which node runs the task. Find
   the container on that node (its context is named after the node, e.g.
   `swarm1` or `swarm2`) and exec into it:

   ```bash
   docker --context <node> ps --filter name=stem-ecosystem_scraper --format '{{.Names}}'
   docker --context <node> exec <container> \
     run-job scrape --source fleet-science-center --dry-run --no-enrich
   ```

7. **Update**: repeat steps 1, 3, 4 and 5 with the new version. **Rotate
   secrets**: see step 2. **Remove** the stack with
   `docker --context swarm1 stack rm stem-ecosystem`.

## Site rebuild

The container only refreshes the bucket. Publishing the site is separate and
manual: Actions -> Deploy -> Run workflow, or
`gh workflow run deploy.yml --repo league-infrastructure/stem-ecosystem`.

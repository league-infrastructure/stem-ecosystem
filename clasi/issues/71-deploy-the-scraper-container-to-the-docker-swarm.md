---
status: pending
---

# Deploy the scraper container to the League docker swarm

## Description

Stakeholder direction (Eric, 2026-10-08): run the sprint-040 scraper
container (supercronic schedule, `run-job`) on the League docker swarm,
following `~/proj/league/infrastructure/league-network/services/docker-swarm/releasing.md`.
The image is to be **public** on ghcr.io.

Facts as of 2026-10-08:

- `league-network/scripts/check-release <repo> -v` reports one error for
  this repo: no compose file at the repo root.
- Swarm: `swarm1` (manager) and `swarm2`, both
  `s-4vcpu-8gb` and x86_64. The docker context `swarm1` works from Eric's
  Mac, which is arm64.
- The planned automation in league-network (`deploying.md`,
  `scripts/swarm-deploy`, `templates/release.yml`, `GHCR_READ_TOKEN`) is
  not built. Deploy by hand per releasing.md:
  `TAG=<version> docker --context swarm1 stack deploy --with-registry-auth -c docker-compose.yml <stack>`,
  after `check-release` passes.
- Eric's gh token (env `GITHUB_TOKEN`) has `write:packages`.

## Scope

1. **Root `docker-compose.yml`, the swarm stack file.**
   - Stack `stem-ecosystem` (`x-league: stack:`).
   - One service, `scraper`, with
     `image: ghcr.io/league-infrastructure/stem-ecosystem-scraper:${TAG:-latest}`
     and `build:` pointing at `scraper/docker/Dockerfile` (context `.`).
   - No ports, no Caddy label, no caddy network (it is a cron worker).
   - `deploy.restart_policy`; no `restart`/`container_name`.
   - A healthcheck confirming supercronic is alive.
   - Chromium shared memory: a tmpfs mount at `/dev/shm` (about 1 GB),
     because `--ipc=host` is not available in swarm.
   - A sensible memory limit or reservation.
   - It must pass `check-release <repo> -v`, and with `--live` once the
     secret exists.
2. **Secrets as a swarm secret.** Create an external secret named
   `stem-ecosystem_scraper_secrets` (the `<stack>_` prefix rule) holding
   the same base64 bundle `make-secrets.sh` produces. It is mounted at
   `/run/secrets/...`.
   - `load-secrets` gains file support (e.g. `SCRAPER_SECRETS_FILE`, set in
     compose), keeping env-var support for plain `docker run`.
   - Tests use fake values only.
3. **Image.**
   - Build for `linux/amd64` (the swarm nodes) and push
     `ghcr.io/league-infrastructure/stem-ecosystem-scraper:<version>`,
     where the version comes from the repo's `v<major>.<YYYYMMDD>.<n>` tag.
   - Make the package public and link it to the repo.
   - A GitHub build-on-release workflow is out of scope until
     league-network ships `templates/release.yml`.
4. **Deploy and verify.**
   - Create the secret by piping `make-secrets.sh` into
     `docker --context swarm1 secret create stem-ecosystem_scraper_secrets -`.
     It is never written to disk or printed.
   - `stack deploy` the stack.
   - Verify the task is running, the logs show the schedule, and a manual
     job works, for example
     `docker exec <task> run-job scrape --source <one> --dry-run --no-enrich`.
5. **Records.**
   - Update `scraper/docker/README.md` with the swarm deploy steps.
   - Add a record in league-network for the service (`services/` or
     `sites/` per its AGENTS.md conventions), committed in that repo.

## Constraints

- Agents never read or print real secret values. The real secret is
  created by the team lead with a pipe only.
- Site deploy (`deploy.yml`) stays manual. No rebuild trigger.

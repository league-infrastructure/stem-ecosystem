# Activating the scheduled scrape workflow

This runbook covers the operator steps that put
`.github/workflows/scheduled-run.yml` into production. The workflow runs
the scraper in `scraper/` every Monday at 13:00 UTC and on manual dispatch.
It's for a human operator to perform once, then again whenever a
credential rotates.

## How the job works

- **Storage:** cache and data live in the DigitalOcean Spaces bucket
  `jtl-stem-ecosystem-scrape`, under the `cache/` and `data/` prefixes,
  which are the scraper's built-in defaults.
- **Nothing goes back to git.** The job commits nothing (`permissions:
  contents: read`) and uses no `actions/cache`.
- **Partner roster:** it is this repo's own `src/data/partners.json`, passed
  with `--site-dir ${{ github.workspace }}`. The cross-repo checkout and
  `SITE_REPO_TOKEN` it needed when the scraper lived in the separate
  partner-scrape repo are gone. That repo was merged into this one on
  2026-10-02.

The job needs three Actions secrets, referenced by name only:

| Secret | Used for |
|---|---|
| `ANTHROPIC_API_KEY` | LLM enrichment |
| `DO_SPACES_ACCESS_KEY` | Spaces bucket access key (cache + data) |
| `DO_SPACES_SECRET_KEY` | Spaces bucket secret key |

The endpoint (`https://sfo3.digitaloceanspaces.com`, the region endpoint,
not bucket-qualified) is set in the workflow itself.

All three secrets live SOPS-encrypted in `config/prod/secrets.env`. No
secret value is written anywhere in this repo, this document or the
workflow file.

## 1. Push the secrets to GitHub Actions

From the repo root:

```bash
# Dry-run first: confirms which keys and repo would be affected
dotconfig gh-push -d prod --actions --repo league-infrastructure/stem-ecosystem --dry-run

# Then for real
dotconfig gh-push -d prod --actions --repo league-infrastructure/stem-ecosystem
```

`dotconfig gh-push` is the only step that transmits the values. They go
straight to GitHub's Actions secrets store.

## 2. Verify the secrets are present

```bash
gh api repos/league-infrastructure/stem-ecosystem/actions/secrets --jq '.secrets[].name'
```

The output should include all three names.

## 3. Trigger one manual run before trusting the cron

```bash
gh workflow run scheduled-run.yml --repo league-infrastructure/stem-ecosystem
```

Confirm, for that run:

- The job summary shows a per-source yield report.
- The run wrote fresh objects under `s3://jtl-stem-ecosystem-scrape/data/`
  and `cache/` (check the bucket listing or last-modified times).
- Nothing is committed to git.

Only after a real end-to-end run like this succeeds should the weekly
cron be trusted to run unattended.

## Getting the data onto the site

The scrape job updates the bucket, not the site. The site's deploy
workflow runs `npm run fetch-data` at the repo root before every build
(anonymous HTTPS from the bucket's public `data/` prefix; no credentials,
nothing committed).

**Auto-deploy.** When the `scrape` job succeeds, a second job in
`scheduled-run.yml` (`deploy`, `needs: scrape`) runs
`gh workflow run deploy.yml --ref <default branch>`, so the live site
rebuilds from the fresh data. If the scrape fails or is cancelled, the
deploy job is skipped and the site keeps its last build. Only that job has
`actions: write`; the scrape job stays `contents: read`. A dispatch (unlike
a push made with `GITHUB_TOKEN`) does trigger workflows, and deploy.yml's
`paths-ignore` applies to pushes only, so it does not affect it.

To verify end to end, run `gh workflow run scheduled-run.yml --repo
league-infrastructure/stem-ecosystem`, then confirm that a Deploy run
appears (`gh run list --workflow deploy.yml`, event `workflow_dispatch`)
after the scrape job finishes. To publish without a scrape, run
`gh workflow run deploy.yml` or push to `master`.

## Known risk: job timeout

The scrape job has `timeout-minutes: 30`, but a full local Docker scrape
took about 80 minutes (mostly LLM enrichment, ~4.7k calls with a partially
warm cache). A cold or large run may be killed by the timeout, which fails
the job and skips the deploy. Raise the timeout (GitHub allows up to 360
minutes on hosted runners) if runs are cut off.

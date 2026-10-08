# Scheduled scrape (GitHub workflow retired)

**Status: retired (sprint 039, ticket 007).** `.github/workflows/scheduled-run.yml`
has been deleted, including its auto-deploy job. Scraping now runs from a
container with built-in cron; see `scraper/docker/README.md` for build,
secrets, schedule and operation.
The old 30-minute job-timeout risk is moot.

Site deploys are **manual only**: Actions -> Deploy -> Run workflow, or
`gh workflow run deploy.yml --repo league-infrastructure/stem-ecosystem`.
`deploy.yml` runs `npm run fetch-data` (anonymous HTTPS from the bucket's
public `data/` prefix) before building. A separate site-rebuild cron may be
added later.

The sections below are kept as background on how the scraper job was
configured (storage, secrets) and are useful when setting up the container
cron. The GitHub-specific steps no longer apply.

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

## 1. (Historical) Push the secrets to GitHub Actions

From the repo root:

```bash
# Dry-run first: confirms which keys and repo would be affected
dotconfig gh-push -d prod --actions --repo league-infrastructure/stem-ecosystem --dry-run

# Then for real
dotconfig gh-push -d prod --actions --repo league-infrastructure/stem-ecosystem
```

`dotconfig gh-push` is the only step that transmits the values. They go
straight to GitHub's Actions secrets store.

## 2. (Historical) Verify the secrets are present

```bash
gh api repos/league-infrastructure/stem-ecosystem/actions/secrets --jq '.secrets[].name'
```

The output should include all three names.

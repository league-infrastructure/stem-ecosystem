---
status: pending
---

# Move partner-scrape into stem-ecosystem and archive partner-scrape

## Context

partner-scrape (the Python scraper) and stem-ecosystem (the Astro site) are being merged into one repo. Sprint 038 made this possible:
- The scraper is now a self-contained package.
- All cache and data live in the `jtl-stem-ecosystem-scrape` bucket.
- Nothing in either repo needs to write into the other.

**Goal:** stem-ecosystem holds both the site and the scraper. It becomes the CLASI-managed project, and partner-scrape is archived on GitHub.

Decisions you made:
- **History:** a fresh copy with no git history. History stays readable in the archived repo, and the import commit names the source commit.
- **Layout:** the scraper goes in a `scraper/` subfolder.
- **CLASI:** stem-ecosystem becomes the CLASI project, with partner-scrape's sprint and issue history brought over.

State today:
- partner-scrape `master` is at `580448e` (sprint 038 closed, tag `v0.20261002.12`). It is **47 commits ahead of origin**.
- stem-ecosystem `master` matches origin. Its sprint 038 work is on the unmerged branch `partner-scrape-038-bucket-fetch` (`c05d50c`).
- Both repos use the same SOPS age recipients, so their encrypted config files can be merged as-is.

Execution is **out of process**, as a one-time repo migration. The CLASI project itself is what's moving, so it can't run as a sprint inside either repo. Approving this plan is your explicit out-of-process authorization. Each phase is a separate commit, so it can be reviewed and reverted.

## Phase 0: Bring both repos up to date

1. **partner-scrape:** `git push origin master`, so the archived repo has all of sprint 038 and the import commit can point at a published SHA.
2. **stem-ecosystem:** merge `partner-scrape-038-bucket-fetch` into `master` (no fast-forward), then delete the branch.

## Phase 1: Copy the scraper into `scraper/` (stem-ecosystem)

1. **Copy the tracked files.** Use `git archive` of partner-scrape `master` into `stem-ecosystem/scraper/`, so only tracked files come across. Local `data/`, `.env`, `.venv` and `__pycache__` stay behind.
   - **Into `scraper/`:** `partner_scrape/`, `tests/`, `dev/`, `pyproject.toml`, `uv.lock`, `README.md`, and `docs/`. That includes `data-schema.md`, which the wheel force-includes as `docs/data-schema.md` relative to `pyproject.toml`, so keeping it under `scraper/docs/` leaves that path working. It also includes `docs/deploy/scheduled-run.md` and `docs/design/design.md`.
   - **Not into `scraper/`:** `config/`, `.github/`, the CLASI files and the root-level agent files. Phases 2 to 4 handle those.
2. **Merge the ignore rules.** Add `scraper/.gitignore`, built from partner-scrape's Python rules: `.venv/`, `__pycache__/`, `/data/`, `.pytest_cache/`, `dist/`.
3. **Verify** with `cd scraper && uv sync && uv run pytest`. It should match partner-scrape: 2,617 passed, 2 skipped. Also run `uv run python dev/wheel_smoke_test.py`.
   - The package resolves paths relative to itself (`_PACKAGE_DIR`). `dev/wheel_smoke_test.py` and `dev/refresh_school_directories.py` use `Path(__file__).parent.parent`, which becomes `scraper/`, and that is still correct.
4. **Commit:** "Import partner-scrape at <sha> into scraper/".

## Phase 2: Config and CI

1. **dotconfig.** Merge partner-scrape's config into stem-ecosystem's `config/`:
   - Copy the scraper keys into `config/prod/public.env`: `SCRAPE_CACHE_DIR`, `PARTNER_SCRAPE_DATA_DIR`, `DO_SPACES_ENDPOINT`. stem-ecosystem's copy is empty today.
   - Bring partner-scrape's encrypted `config/prod/secrets.env` across. stem-ecosystem's is empty, and the age recipients are identical. It holds `ANTHROPIC_API_KEY`, `DO_SPACES_*`, `LEAGUESYNC_*` and `TBA_KEY`.
   - Merge `config/local/eric/*` key by key. Never print values; compare key names only.
   - Set `config/dotconfig.yaml` `version` to partner-scrape's `0.20261002.12`, so CLASI's version tags keep increasing.
   - Run `dotconfig load prod` and `dotconfig audit`, and confirm the Spaces keys are present by counting them with `grep -c`.
2. **Move `scheduled-run.yml` into stem-ecosystem's `.github/workflows/`:**
   - Set `working-directory: scraper`.
   - The partners list (`partners.json`) is now in the same repo. Pass `--site-dir ${{ github.workspace }}`, and **delete the `SITE_REPO_TOKEN` verify and cross-repo checkout steps**. That fixes the weekly job's failure at its first step.
   - It still needs the `ANTHROPIC_API_KEY` and `DO_SPACES_*` secrets on the stem-ecosystem repo.
3. **Move `wheel-smoke.yml`.** Set `working-directory: scraper` and trigger it only on `scraper/**` changes.
4. **Site workflows.** Add `paths-ignore: ['scraper/**']` to stem-ecosystem's `build.yml` and `deploy.yml`, so scraper-only commits don't redeploy the site.
5. **Leave `pages.yml` behind.** That was partner-scrape's old beta publisher, and it's already disabled.
6. **Fix scheduled-run.md.** Move `scraper/docs/deploy/scheduled-run.md` to the right place and update its paths and secrets. `SITE_REPO_TOKEN` is gone.
7. **Commit.**

## Phase 3: CLASI becomes stem-ecosystem's process

1. **Copy the CLASI setup:** `.claude/`, `.agents/`, `.mcp.json`, `CLAUDE.md` and `AGENTS.md` to the stem-ecosystem root. `.clasi/` goes too: the tracked `clasi-version`, `config.yaml` and `log/.gitignore`, plus a copy of the untracked `.clasi.db` (CLASI state, sprint 038 closed).
   - Fix the broken skill symlinks first. `.claude/skills/*/SKILL.md` point at `/Volumes/Proj/...`, which doesn't exist on this machine.
   - Re-run CLASI's own install (`clasi init` or the equivalent in `clasi --help`) in stem-ecosystem so the links are regenerated, rather than copying dead links.
2. **Move the history:** `clasi/sprints/` (001–038, all done), `clasi/issues/` (open: 18, 37–41, 43, 45; done ones in `done/`) and `clasi/reflections/` into stem-ecosystem's `clasi/`.
3. **Renumber the website issues** so they don't collide with partner-scrape's numbers, which run up to 62. stem-ecosystem's 16 issues (001–006, 49–58, open and done) become **063–078**, in their current order.
   - Update cross-references inside those files, e.g. "Issue 57" becomes the new number.
   - Add an old→new mapping table to `clasi/issues/README.md`.
   - Rewrite its "Scope" section, which says the pipeline lives in a separate repo.
4. **Point the docs at the new layout.** Update root `CLAUDE.md` / `AGENTS.md` and the project-level design doc (`scraper/docs/design/design.md`) to say the repo contains both the site (root) and the scraper (`scraper/`). Run Python commands from `scraper/`.
5. **Verify:** in a Claude session in stem-ecosystem, `get_version()` and `list_sprints()` show 001–038 closed, and `list_issues()` shows the open scraper and website issues together.
6. **Commit.**

## Phase 4: Update docs and fetch-data.sh in stem-ecosystem

- **Root `README.md`:** one repo with two parts. It covers:
  - the site: `npm run dev/build`;
  - the scraper: `cd scraper && uv run partner-scrape`;
  - data flow: scraper → bucket → `scripts/fetch-data.sh --bucket` → site;
  - config: `dotconfig load prod` at the root, then `set -a; source ../.env` before scraper runs.
- **`scripts/fetch-data.sh`:**
  - Bucket mode becomes the default.
  - The local-checkout mode takes an explicit data directory, e.g. `scraper/data` when `PARTNER_SCRAPE_DATA_DIR` points at a local folder. It no longer defaults to `../partner-scrape`.
- **`scraper/README.md`:** drop the "separate repo / sibling stem-ecosystem checkout" wording. `get_site_dir()` defaults to the current directory, so from `scraper/` it needs `SITE_DIR=..` or `--site-dir ..`. Document that. Optionally, make the default work out of the box when run inside `scraper/`. Flag it rather than change behavior silently.
- **Commit, then push stem-ecosystem `master`.** This deploys the site. It's a no-op for the site itself, since `scraper/**` is excluded but the README and scripts changed.

## Phase 5: Archive partner-scrape

1. **Point to the new home.** In partner-scrape, replace `README.md` with a short notice: "Moved to league-infrastructure/stem-ecosystem under `scraper/`. Archived <date>." Commit and push.
2. **Archive:** `gh repo archive league-infrastructure/partner-scrape --yes`. The repo becomes read-only and its scheduled workflow stops.
3. **Local checkout:** leave `/Users/eric/proj/league/infrastructure/partner-scrape` in place, since its local `data/mirrors/` and `.env` aren't in git. Tell you it can be deleted once you're satisfied.
4. **My memory:** copy my memory notes for this project into the stem-ecosystem project's memory folder, so future sessions there keep them.

## Operator steps for you

- **GitHub secrets:** add `ANTHROPIC_API_KEY`, `DO_SPACES_ACCESS_KEY` and `DO_SPACES_SECRET_KEY` to the **stem-ecosystem** repo with `dotconfig gh-push -d prod --actions --repo league-infrastructure/stem-ecosystem` (try `--dry-run` first). If you'd rather, I can run it after showing you the dry run.

## Verification

- `cd stem-ecosystem/scraper && uv run pytest`: 2,617 passed, 2 skipped. The wheel smoke test passes.
- `npm run build` at the stem-ecosystem root succeeds. `scripts/fetch-data.sh --bucket` passes its image check.
- `dotconfig audit` is clean, and no secret values appear in any commit (grep the new commits for the real key values).
- CLASI in stem-ecosystem: `list_sprints()` shows 001–038, and `list_issues()` shows the merged open issues with no number collisions.
- **GitHub:**
  - The partner-scrape repo shows as archived, with the moved notice and the sprint 038 commits.
  - stem-ecosystem `master` contains `scraper/`, and its deploy workflow ran green.
  - After you add the secrets, a manual `workflow_dispatch` of the scheduled scrape in stem-ecosystem gets past its first step.

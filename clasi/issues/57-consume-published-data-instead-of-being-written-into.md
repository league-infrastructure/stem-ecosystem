---
status: pending
---

# Pull data from partner-scrape instead of having it written into this checkout

## Description

Eric has directed that partner-scrape stop writing into this repo:
"I want the stem ecosystem to get data from you, so you're not writing the
stem ecosystem anymore." partner-scrape is removing every write path into
`{site_dir}/...` — `opportunities.json`, `scrape-meta.json`, `teams.json`,
`places.json`, `clubs.json`, `yield-history.json`, and the per-partner
publish under `public/data/`. Its own `data/` directory (added sprint 020,
same payload and timestamp) becomes the single place it writes.

So this repo needs to consume that output. Today it does not consume
anything — the files simply appear in the working tree because another
program reached into the directory and wrote them.

**Why this is worth doing properly rather than minimally.** The current
arrangement is what caused the stale-roster bug: the pipeline resolved this
repo by a filesystem guess (`config.py`'s `DEFAULT_SITE_DIR` is literally
`_REPO_ROOT.parent / "stem-ecosystem"`), then both read from and wrote to it,
so a stale `partners.json` sitting here silently corrupted a whole run. No
component verified that the directory it found was the site repo, or that
what it read there was current. Replacing a push with a pull is the chance
to make the data flow explicit and one-directional.

## The images

Settled: the images move to partner-scrape's `data/images/opportunities/`
alongside everything else, so the fetch this issue builds has to cover them,
not just the JSON.

Two corrections to what this issue originally assumed, both established by
measurement (see issue 58). The images do **not** churn every scrape — the
filenames are content-addressed, so git stores each one exactly once and
history shows 631 additions with zero modifications or deletions. Growth is
additive only. And the 405 MB is mostly oversized originals rather than an
irreducible quantity; partner-scrape is adding resize-on-fetch, so newly
downloaded images arrive web-sized and the set stops growing at anything
like the current rate.

Fetching at build time takes the working tree and all future growth off this
repo. It does not shrink history, so the 405 MB already committed stays
unless the history is rewritten — a separate decision, and not one to make
casually on a repo with a live deploy.

## Proposed approach

Fetch partner-scrape's `data/` at build time, mirroring the pattern that
already works in the other direction: partner-scrape's beta preview builds
this site by checking this repo out at build time (sprint 019). Both repos
are public, so a read-only `actions/checkout` with `repository:` needs no
credential.

Sketch, in `.github/workflows/deploy.yml` before the Astro build:

- `actions/checkout` partner-scrape into a temp path.
- Copy its `data/` into the places the site reads: `src/data/` for the build
  inputs, `public/data/` and `public/images/opportunities/` for the
  published artifacts.
- Build.

Then stop tracking the generated files here, keeping only what this repo
actually authors.

Points to settle while implementing:

- **Local development.** The site must still build offline. A script that
  populates from a sibling `../partner-scrape` checkout, or a committed
  sample, or simply documenting that a fetch is required first.
- **Pinning.** Checking out partner-scrape's `master` means a site rebuild
  can pick up data nobody reviewed. Pinning a tag or SHA makes data updates
  deliberate but adds a bump step. Given the whole point is that data flows
  automatically, `master` is probably right, but it is a real choice.
- **Failure mode.** If the fetch fails, the build should fail loudly rather
  than deploy a site with missing or stale data. A silent partial deploy is
  the failure this whole change exists to eliminate.
- **What stays authored here.** `src/data/partners.json` is hand-curated in
  this repo and must not be clobbered by the fetch — see below.

## The remaining coupling: partners.json

partner-scrape's write removal does **not** cover reads. It still reads
`src/data/partners.json` from this checkout via `--site-dir`, for roster
validation and source-registry join checks. Eric was asked whether reads
should stop too and has not ruled, so partner-scrape is proceeding on the
conservative reading that reads stay.

Worth being clear that this leaves the exact mechanism that caused the
stale-roster bug intact: the pipeline still locates this repo by filesystem
guess and still trusts whatever `partners.json` it finds there. Stopping the
writes removes the confusing part — data appearing in a repo that did not
produce it — without removing the failure mode.

Two clean resolutions, if Eric wants reads separated too:

1. The curated roster moves to partner-scrape as a pipeline input. Simplest
   dependency graph: the pipeline owns everything it reads. Costs the
   convenience of editing the roster in the repo where site work happens.
2. The roster stays here and partner-scrape fetches it over HTTP from the
   published site, the same way any other consumer would. Keeps editing
   where it is, and the pipeline reads a published artifact rather than a
   working tree it guessed at.

Not this issue's call, but this issue should not be considered finished
while a second program is reaching into this working tree by path.

## References

partner-scrape's sprint 020 (`data/` as its own publish target,
`config.get_own_data_dir()`); its sprint 019 (the build-time checkout of
this repo, the pattern to mirror); `partner_scrape/config.py`
`DEFAULT_SITE_DIR` / `get_site_dir()` for the current resolution order
(`--site-dir` flag, then `SITE_DIR` env, then the sibling-path guess).
This repo: `.github/workflows/deploy.yml`, `src/data/`, `public/data/`,
`public/images/opportunities/`.

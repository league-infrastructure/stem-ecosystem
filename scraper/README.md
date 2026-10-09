# Scraper (`partner_scrape`)

The San Diego STEM Ecosystem event aggregator engine: fetches and
normalizes opportunities from partner organizations' websites and
publishes them for the site at this repo's root.

This directory was the separate `league-infrastructure/partner-scrape`
repo until 2026-10-02, when it moved here; that repo is archived and keeps
the full git history. Run every command below from `scraper/`.

---

## Running the engine

`partner_scrape/` is the aggregator engine (sprint 001 onward). It reads
a data-driven Source Registry, politely fetches and caches each source,
ingests events via a per-source adapter (The Events Calendar REST,
WordPress REST, or iCal/RSS), normalizes and deduplicates them into the
site's opportunity schema, and exports current+upcoming opportunities
into the data bucket that the site reads.

### Install

Python 3.11+. From a checkout:

```bash
uv sync
uv run partner-scrape --help

# Optional: headless-browser fetching (Playwright) needs the extra AND a browser:
uv sync --extra headless
uv run playwright install chromium
```

Or build a wheel and install it elsewhere (this package is not published to
any package index):

```bash
uv build
pipx install dist/partner_scrape-*.whl      # or: pip install dist/partner_scrape-*.whl
partner-scrape --help
```

The wheel bundles the seed source registry, the in-package data files and
`data-schema.md`. A real run still needs the bucket credentials below;
without them, point `SCRAPE_CACHE_DIR` and `PARTNER_SCRAPE_DATA_DIR` at local
directories. A run also reads the curated roster from the per-partner records in the data
location (`partners/<slug>/partner.json` under `PARTNER_SCRAPE_DATA_DIR`), not
from the site checkout; see "Running locally" below.

### Scheduled runs (container)

Scheduled scraping runs from a Docker image with built-in cron; build, secrets,
schedule, manual runs and logs are in [`docker/README.md`](docker/README.md).

Besides the scrape, teams and directory jobs, two weekly jobs keep partner
records fresh: `profiles` (Sunday 03:00; snapshots each partner's home/About/
Contact pages to `history/profiles/`) and `updates` (Sunday 05:00; asks Haiku
for corrections to records, applies policy-approved changes with actor
`haiku`, and writes a report to `history/updates/<ts>.json` that also holds
redirect and per-partner event-quality checks). Locally:

```bash
uv run partner-scrape profiles --limit 5
uv run partner-scrape updates --dry-run          # report only, no writes
uv run partner-scrape updates --no-llm           # flags only, no Haiku
```

Logs go to `logs/profiles/` and `logs/updates/`. To inspect or undo a Haiku
change (`history/partners/changes.jsonl`, the archived record, `partners put`)
see "Profiles and updates jobs" in `docker/README.md`.

### Configure

Cache and published data live in the DigitalOcean Spaces bucket
`jtl-stem-ecosystem-scrape` (`cache/` and `data/` prefixes) -- **not in
git**. For a real run set `DO_SPACES_ENDPOINT`, `DO_SPACES_ACCESS_KEY` and
`DO_SPACES_SECRET_KEY` (assembled into `.env` by `dotconfig load prod`;
`set -a; source ../.env; set +a` from `scraper/`). To work locally instead, point
`SCRAPE_CACHE_DIR` and `PARTNER_SCRAPE_DATA_DIR` at local directories (a
path or an `s3://bucket/prefix` URL; see `partner_scrape/config.py`).
`--site-dir` / `SITE_DIR` no longer locate the roster (kept for compatibility;
nothing is written there). The seed registry ships inside the package
(`partner_scrape/registry_data/`); set `PARTNER_SCRAPE_REGISTRY_DIR` to a
local directory (with `sources/`, `hubs/`, `candidates/`, `ads/`) to
override it.

```bash
export SCRAPE_CACHE_DIR=/path/to/a/cache/dir
export PARTNER_SCRAPE_DATA_DIR=/path/to/a/data/dir
export PARTNER_SCRAPE_HISTORY_DIR=/path/to/a/history/dir
```

#### Running locally

The curated roster is the set of `partners/<slug>/partner.json` records in the
data location, so a local run needs a local data dir that contains them. Also
set `PARTNER_SCRAPE_HISTORY_DIR` locally: the per-partner event log
(`partner_log/`) and the record archive now live under `history/`, which
otherwise defaults to the real bucket. Seed the local data dir either by
copying `data/partners/` out of the bucket (read-only, with your S3 tool of
choice) or by creating records with the CLI:

```bash
export PARTNER_SCRAPE_DATA_DIR=/tmp/ps/data PARTNER_SCRAPE_HISTORY_DIR=/tmp/ps/history
export SCRAPE_CACHE_DIR=/tmp/ps/cache
uv run partner-scrape partners add --name "Example Org" --file example.json
uv run partner-scrape --source xplorstem        # reads the local roster
```

An empty roster fails loudly ("No partner records found"). Library callers and
tests can bypass the store entirely by passing `partners_path=` (a roster JSON
file or a list of partner dicts) to `pipeline.run()`.

### Run

```bash
# Full run against the bundled seed registry and the site at the repo root
uv run partner-scrape --site-dir ..

# See the payload that would be written, without touching disk
uv run partner-scrape --dry-run

# Point at a different registry dir / site checkout
uv run partner-scrape --registry-dir path/to/sources --site-dir path/to/site

# Smoke-test a single source, or just the first few
uv run partner-scrape --source coastalrootsfarm
uv run partner-scrape --limit 3

# -m works too, without the console script
uv run python -m partner_scrape.cli --dry-run
```

The CLI is `partner-scrape [flags]` -- there is no `run` subcommand;
`--source X` scopes the main run to one source. Other pipelines are the
`teams`, `directory` and `discover-candidates` subcommands.

Output schema: `docs/data-schema.md` (bundled in the wheel and published
to `data/SCHEMA.md` in the data bucket at the end of every non-dry-run).
`data/` is gitignored; a local `data/` is only a scratch copy.
The bucket's `data/` prefix is published with public-read ACLs (`cache/` stays
private); the site downloads it over anonymous HTTPS at build time with
`npm run fetch-data` at the repo root (`--local <data-dir>` copies from a local
scraper data dir instead). Existing objects can be backfilled with
`scripts/backfill_public_read.py`.

One source's adapter failing (network error, malformed response, ...) is
logged and skipped -- it never aborts the rest of the run.

### Test

```bash
uv run pytest
```

The built wheel is smoke-tested end to end (fresh venv outside the repo,
`--help` with no credentials, one dry run with local temp cache/data dirs):

```bash
python dev/wheel_smoke_test.py
```

Every test runs against recorded fixtures under `tests/fixtures/` --
no network access, no `ANTHROPIC_API_KEY` usage, no writes to the real
bucket or the site's files.

---

*A pre-`partner_scrape/` Scrapy-based prototype mirrored partner sites
for offline extraction before this package existed, along with a
standalone entry-point script and its Docker/Compose tooling. It has
been retired and removed; see the archived partner-scrape repo's git
history for reference. `dev/refresh_school_directories.py` is unrelated and
remains -- it is a live, standalone maintenance script for the
`teams/` subsystem's offline geocoding data, documented in
`partner_scrape/teams/DESIGN.md`.*

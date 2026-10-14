---
status: done
sprint: '051'
tickets:
- 051-001
---

# Wheel smoke test has failed since the roster moved to the bucket

## Description

Eric got GitHub failure emails for "Scraper wheel smoke test"
(`.github/workflows/wheel-smoke.yml`). Every push to master since
2026-10-09T19:03Z has failed, on both Python 3.11 and 3.13. The last
success was 2026-10-08. The timing matches sprint 042, which moved the
curated roster to `data/partners/<slug>/partner.json` in the bucket and
added the private `history/` store; later sprints also added hints and
logs stores.

The smoke test installs the wheel in a fresh venv and runs:

```
partner-scrape --dry-run --site-dir <tmp>/site --registry-dir <tmp>/empty-registry
```

with only `SCRAPE_CACHE_DIR` and `PARTNER_SCRAPE_DATA_DIR` pointed at local
directories. It now fails with:

```
RuntimeError: DO_SPACES_ENDPOINT, DO_SPACES_ACCESS_KEY, DO_SPACES_SECRET_KEY not set,
but an s3:// location is in effect ... or point SCRAPE_CACHE_DIR/PARTNER_SCRAPE_DATA_DIR/
PARTNER_SCRAPE_HISTORY_DIR at a local directory to run without the bucket.
```

Two causes:

1. `PARTNER_SCRAPE_HISTORY_DIR` (and the hints and logs store locations)
   still default to the bucket.
2. The roster is no longer read from `--site-dir`. The smoke test should
   seed a minimal local roster in the local data store, e.g. via
   `partner-scrape partners add`, or by writing one
   `partners/<slug>/partner.json`.

The production scraper on the swarm is unaffected (its runs succeed).

## Fix

- Update the smoke-test script and workflow:
  - point every store env var at local temp dirs
    (`PARTNER_SCRAPE_HISTORY_DIR`, `PARTNER_SCRAPE_HINTS_DIR`,
    `PARTNER_SCRAPE_LOGS_DIR`, plus any others in `config.py`);
  - seed a one-partner local roster;
  - keep the "no credentials, no network" guarantee.
- The smoke test must also prove the wheel works without any bucket access.
- Verify locally by running the same script, then confirm the workflow
  passes on push.

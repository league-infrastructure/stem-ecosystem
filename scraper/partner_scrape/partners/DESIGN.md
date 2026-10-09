# Partner Record Store

Per-partner records and logos in the bucket are the source of truth for the
curated roster (issue 77).

## Layout (bucket `jtl-stem-ecosystem-scrape`)

| Key | Access | Content |
|-----|--------|---------|
| `data/partners/<slug>/partner.json` | public-read | the record; carries its own `slug` |
| `data/partners/<slug>/logo.<ext>` | public-read | the logo |
| `history/partners/<slug>/<UTC ts>-partner.json` | private | archived previous record |
| `history/partners/<slug>/<UTC ts>-logo.<ext>` | private | archived previous logo |
| `history/partners/changes.jsonl` | private | one line per change |

The slug is stored in the record and is the directory name. It is never
re-derived from the name (`model.slugify` is for migration and `partners add`).

## Modules

- `records.py` -- key helpers, `read_record`, `list_slugs`, `Roster`,
  `load_roster(data_store)` (checks stored slug == directory, then runs
  `validate_roster` on the record list; fails loudly with every offender).
- `writer.py` -- `PartnerWriter(data, history)`; `put_record(slug, record, actor)`
  and `put_logo(slug, ext, bytes, actor)`. The only code that writes
  `data/partners/`. Per write: no-op if unchanged; archive current object
  (skipped on first write); write new; append a change line
  `{slug, ts, actor, kind, changed, archived}`. `default_writer()` builds it
  from config.

## Why two stores

`S3Store.public_read` is per-store. The data store is public-read; the
history store (`config.get_history_store()`, env `PARTNER_SCRAPE_HISTORY_DIR`,
default `s3://jtl-stem-ecosystem-scrape/history`) is always private. Tests
assert the ACLs with a fake S3 client.

## Notes

- Same-second archives get a `-2`, `-3` suffix instead of overwriting.
- Changing a logo's extension archives the old logo and deletes it from `data/`.
- `changes.jsonl` is appended by read-modify-write; writers are serial.

## consolidate.py and the `partners` CLI (ticket 042-003)

`consolidate(store)` loads and validates every record (`validate_records`
names offending slugs) and only then writes `partners.json`; a bad record
raises before any write. `published_entry` / `build_envelope` are shared
with `export/publish.project` so both produce one envelope shape.
CLI: `partners get|put|add|consolidate`; `put`/`add` validate then go
through `PartnerWriter` with `--by` (default `person:$USER`).

## Scraper readers (ticket 042-004)

The scraper no longer reads `$SITE_DIR/src/data/partners.json`. Every reader
goes through `source.resolve_partners(source=None)`: `None` = the records in
the configured data store (`PARTNER_SCRAPE_DATA_DIR`, local dir or `s3://`);
also accepts a `Store`, a list, or a roster/envelope JSON file (offline
override, tests). An empty roster fails loudly. Switched: `pipeline.run`
(resolves once, hands the list to `validate_roster`, `normalize.run`,
`partner_log.record`), `normalize.partners.load_partners`, `normalize.run`,
`export/partner_log`, `export/publish.project` (default roster = records in
`own_data_dir`), `directory.pipeline._check_related_partner_references`,
`cli` scrape. `publish.project` no longer writes `partners.json`; the `scrape`
CLI calls `consolidate(get_data_store())` right after it (failure logged,
exit 1, like `project`). `--site-dir`/`SITE_DIR` are accepted but unused.
`export/partner_log` moved from `cache/partner_log` to the history store
prefix `partner_log/` (`history/partner_log` in the bucket); copying old
objects is ticket 005. Published event files use the record's stored slug;
the accumulated log is still keyed by `slugify(name)`.
The image does not bake the roster. Local runs: README "Running locally".

## Migration (ticket 042-005)

`migrate.py` is the one-time import: `partner-scrape partners migrate
[--site-dir ..] [--dry-run]` splits `src/data/partners.json` into records
(slug = `slugify(name)`, stored), uploads logos to `partners/<slug>/logo.<ext>`
(`logo_src` = that bucket-relative path, or `""`), through the archiving writer
with actor `migration`, and **copies** `cache/partner_log/**` to
`history/partner_log/**` (never moves/deletes; idempotent; a differing
destination `opportunities.jsonl` gets only the missing source lines appended).
Slug collisions, unusable names, a `logo_src` that is missing/not a bare
filename, or a failing validation abort before any write.
`partner-scrape partners verify-migration --baseline <file|->` consolidates in
memory and exits 1 on any difference except `logo_src` values (partner order is
a note only). The partner_log history directory is keyed by the record's stored
slug (`partner_log.log_slug_for`), so a rename keeps its history.

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

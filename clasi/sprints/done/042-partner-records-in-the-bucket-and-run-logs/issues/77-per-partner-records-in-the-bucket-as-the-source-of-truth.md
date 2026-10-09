---
status: in-progress
related: clasi/issues/75-post-scrape-partner-record-update-check-with-haiku.md
sprint: '042'
tickets:
- 042-002
- 042-003
- 042-004
- 042-005
- 042-006
- 042-007
---

# Per-partner records in the bucket as the source of truth

## Description

Stakeholder decision (Eric, 2026-10-08): move the curated partner roster
out of Git and into the bucket, one record per partner.

- Each partner gets its own `partner.json` under `data/partners/`. That
  record is the original source.
- The single `data/partners.json` is **recomposed** at the end of every
  scrape and every update, by listing and consolidating the individual
  records.
- Updates (by a person, an agent, or the issue-75 Haiku process) edit the
  partner's record in the bucket.
- Old versions are kept: bucket object versioning, plus an explicit
  archive/change log of old versions.
- Logos get the same treatment: when one is overwritten, the old one is
  saved with a date.

This supersedes issue 75's "where does the update land" question: option
C, the bucket is the source of truth.

## Today

- The curated roster is `src/data/partners.json` in Git: 211 entries,
  hand-edited. It is baked into the scraper image at
  `/site/src/data/partners.json`.
  - The site imports it in 7 pages (`index`, `partners/*`,
    `opportunities/[slug]`, `data-access`, `for-agents`, `llms.txt`).
  - About 10 scraper modules read it via `$SITE_DIR` (`normalize/partners.py`,
    `directory/*`, `registry/validate_roster.py`, `export/partner_log.py`, ...).
- Logos are `public/images/logos/*` in Git (204 files), referenced by
  `logo_src`.
- The bucket already has `data/partners/<slug>/events.json` and
  `past-events.json`, plus the generated envelope `data/partners.json`
  (`generated_at`, `partner_count`, `partners[]` with curated fields plus
  `events_url`/`past_events_url`).
- `cache/partner_log/<slug>/` is the **permanent, never-pruned event
  history** that `past-events.json` is built from (`export/partner_log.py`).
  It also holds a refreshed copy of each curated record. It must be kept.
- The slug is derived from the partner name (`model.slugify`), so a rename
  (CMOD) would move the partner's directory.

## Target layout

```
data/partners/<slug>/partner.json      # curated record: SOURCE OF TRUTH
data/partners/<slug>/logo.<ext>        # current logo (public)
data/partners/<slug>/events.json       # generated (unchanged)
data/partners/<slug>/past-events.json  # generated (unchanged)
data/partners.json                     # consolidated: built from all
                                       #   partner.json + events urls
history/partners/<slug>/<UTC ts>-partner.json   # old versions (private)
history/partners/<slug>/<UTC ts>-logo.<ext>     # old logos (private)
history/partners/changes.jsonl         # one line per change: slug, ts,
                                       #   who/what (person, haiku, migration),
                                       #   changed fields, archived path
history/partner_log/...                # moved from cache/partner_log
```

- **Stable slug.** `slug` is stored in `partner.json` and never re-derived
  from the name. A rename changes `name` only.
- **One writer function.** Every update to a record or logo goes through a
  single code path. It does three things:
  1. archives the current object to `history/...`;
  2. writes the new one;
  3. appends to `changes.jsonl`.

  Bucket versioning is the backstop, not the only record.
- **Consolidation** (`partner-scrape partners consolidate`, also run at the
  end of `scrape` and `updates`):
  - list `data/partners/*/partner.json` (the scraper has credentials, so
    listing is fine);
  - validate each record (the existing roster validation);
  - write `data/partners.json`.

  A bad record fails loudly and does not drop the partner silently.
- **Consumers switch to the bucket.**
  - The scraper reads the roster from the bucket instead of `$SITE_DIR`,
    so the image no longer bakes it in.
  - The site gets curated fields from the consolidated `data/partners.json`
    (fetched by `scripts/fetch-data.mjs`; it already carries the curated
    fields) instead of importing `src/data/partners.json`.
  - Logos are fetched to `public/images/logos/` (or served from the
    record's logo URL).
- **Editing by hand.** A small CLI:
  - `partner-scrape partners get <slug>` prints a record;
  - `partner-scrape partners put <slug> <file>` goes through the archiving
    writer;
  - `partner-scrape partners add` creates a new record and assigns the
    slug and id.

  This replaces editing `src/data/partners.json` in the IDE.

## Migration

1. Split `src/data/partners.json` into per-partner records. Assign
   `slug` = the current derived slug so existing `data/partners/<slug>/`
   paths stay. Upload them through the writer, recorded as "migration".
2. Upload the 204 logos to `data/partners/<slug>/logo.<ext>` and update
   `logo_src` to match.
3. Move `cache/partner_log/` to `history/partner_log/` and update
   `export/partner_log.py`.
4. Switch the scraper and site readers. Verify the consolidated output
   equals the pre-migration envelope, apart from logo paths.
5. Remove `src/data/partners.json` and `public/images/logos/*` from Git,
   and gitignore the fetched copies. The Git history keeps the last
   versions.

## Bucket versioning

**Already enabled** on `jtl-stem-ecosystem-scrape`. The DO console shows
"Object Versioning: Enabled", managed via the API only.

Verified 2026-10-08 with the scraper's own key:
- `get_bucket_versioning` returns `Enabled`;
- `list_object_versions` works (`data/scrape-meta.json` has 2 versions).

So the scraper can list and restore old versions itself. Versioning stays
the backstop; the explicit `history/` archive plus `changes.jsonl` is the
readable record. Note for league-network `services/spaces/`: record that
this bucket is versioned. Old versions are never deleted by default, so
consider a lifecycle rule for noncurrent versions later, especially for
`cache/`.

## Open questions

- `history/` private (proposed) or public?
- Should `changes.jsonl` live in `history/` (private) or in
  `data/partners/` as Eric suggested (public)? Old records hold only
  already-published info, so public is acceptable.
- Should logos be served from the bucket URL directly, or copied into the
  site build as today?

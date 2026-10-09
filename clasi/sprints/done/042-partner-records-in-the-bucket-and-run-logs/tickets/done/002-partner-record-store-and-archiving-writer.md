---
id: '002'
title: Partner record store and archiving writer
status: done
use-cases:
- SUC-001
depends-on: []
github-issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Partner record store and archiving writer

## Description

Create `partner_scrape/partners/` with `records.py` (key layout, read/list records, `Roster` loader returning validated records) and `writer.py`: the single archiving writer for records and logos. Write(slug, new object, actor): copy current object to `history/partners/<slug>/<UTC ts>-partner.json` (or `-logo.<ext>`), write the new one, append a line to `history/partners/changes.jsonl` (slug, ts, actor, changed fields, archived path). Slug lives in the record and is never re-derived from name.

## Acceptance Criteria

- [x] Writer archives, writes, and appends change line in one code path; first write has nothing to archive
- [x] Logo writes use the same path (`data/partners/<slug>/logo.<ext>` public, archive `-logo.<ext>` private)
- [x] Records and logos are public-read; everything under history/ is private (test asserts ACL behavior with a fake S3 client)
- [x] Changed-fields diff recorded; no-op put writes nothing and logs nothing
- [x] Roster loader returns records keyed by stored slug

## Implementation Plan

READ FIRST: `storage.py` (S3Store public_read is per-store, so the writer needs a public store view for data/ and a private one for history/; design the writer to take two Store instances) and `config.py` (how data/cache stores are built; add a `get_history_store()`/bucket-root helper). Tests with LocalStore plus fake S3 client. Document in `partners/DESIGN.md`.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest` (and `npm test`/node tests for ticket 006)
- **New tests to write**: as listed in the plan
- **Verification command**: `cd scraper && uv run pytest`

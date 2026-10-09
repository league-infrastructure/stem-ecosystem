---
status: draft
---
# Sprint 042 Use Cases

## SUC-001: Maintainer edits a partner record
Parent: UC-XXX
- **Actor**: Maintainer or agent
- **Preconditions**: Scraper credentials available
- **Main Flow**: `partners get <slug>` -> edit -> `partners put <slug> <file>`; `partners add` creates a new record with slug and id.
- **Postconditions**: Old record archived under `history/partners/<slug>/`, change line appended, consolidated roster refreshed on consolidate.
- **Acceptance Criteria**:
  - [ ] put archives, writes, and logs in one code path; invalid record rejected loudly

## SUC-002: Scraper uses bucket roster
Parent: UC-XXX
- **Actor**: Scheduled scraper
- **Main Flow**: Reads and validates records from the bucket, scrapes, then recomposes `data/partners.json`.
- **Postconditions**: Consolidated file includes events urls; image contains no roster.
- **Acceptance Criteria**:
  - [ ] No code path reads `$SITE_DIR/src/data/partners.json`; bad record fails the consolidation loudly

## SUC-003: Site build gets roster and logos from the bucket
Parent: UC-XXX
- **Actor**: Site build
- **Main Flow**: `fetch-data.mjs` fetches consolidated roster and logos, writes gitignored copies.
- **Acceptance Criteria**:
  - [ ] Pages unchanged in output; `/images/logos/` URLs work

## SUC-004: One-time migration
Parent: UC-XXX
- **Actor**: Team lead
- **Main Flow**: Split roster, upload records and logos via the writer, copy `cache/partner_log` to `history/partner_log`, verify equality.
- **Acceptance Criteria**:
  - [ ] Idempotent; never deletes; verification reports differences other than logo paths

## SUC-005: Run logs
Parent: UC-XXX
- **Actor**: Team lead reading logs
- **Main Flow**: Each `run-job` uploads its full output to `logs/<type>/<ts>-<job>.log` and appends `logs/index.jsonl`.
- **Acceptance Criteria**:
  - [ ] Failed jobs upload too; upload failure keeps job exit code; no secrets in logs; logs/ not public

---
status: pending
---

# Delete cache/partner_log after the history cutover is verified

## Description

Sprint 042 (2026-10-08):
- copied `cache/partner_log/` into `history/partner_log/` (208 objects,
  source untouched);
- deployed image 0.20261008.10, which reads and writes only
  `history/partner_log/`. Its history key is the record's stored slug.

The old prefix is left in place as a fallback.

## To do

Once a few scheduled scrapes on the new image have run cleanly (check
`logs/index.jsonl`, and that `past-events.json` files still contain past
events):

1. Confirm nothing references `cache/partner_log`:
   `grep -r "partner_log" scraper/partner_scrape` shows only the
   `history` store.
2. Optionally compare the object counts of `cache/partner_log/` and
   `history/partner_log/` (history should be a superset).
3. Delete `cache/partner_log/` with the scraper's key. Bucket versioning
   keeps the deleted objects as noncurrent versions, so this is reversible.
4. Optionally add a lifecycle rule that expires noncurrent versions under
   `cache/` after N days. Versioning is on and `cache/` churns every
   scrape.

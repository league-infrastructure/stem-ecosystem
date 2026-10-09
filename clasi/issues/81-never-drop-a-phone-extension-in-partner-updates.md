---
status: pending
related: clasi/issues/80-review-queue-for-partner-update-proposals.md
---

# Never drop a phone extension in partner-record updates

## Description

Stakeholder rule (Eric, 2026-10-09): "if a phone number has an extension, you
need to keep the extension." An extension usually reaches the specific
contact; the site's main line is not a better value.

The first real updates run (2026-10-09) proposed dropping the extension for
four partners. All four were routed to needs-review, not applied:

| Partner | Record | Proposal |
|---|---|---|
| electrical_training_institute | `%28858%29569-6633ext.462` | (858) 569-6633 |
| san_diego_air_space_museum | 619-234-8291x132 | 619-234-8291 |
| san_diego_model_railroad_museum | 6196960199extn.1608 | 6196960199 |
| san_diego_children_s_discovery_museum | 760-233-7755x1012 | 760-233-7755 |

## Rule (updates policy and checks)

- **Same line without the extension.** If the record phone has an extension
  (`x`, `ext`, `ext.`, `extn`, `#`, case-insensitive) and the proposed number
  has the same base digits without it, it is **not a change**. It is not
  flagged as `phone_mismatch`, not applied and not listed as needs-review.
- **Different base number.** A proposal to a different base number goes to
  needs-review as today. If a person accepts it, the extension is not carried
  over automatically; they decide.
- **Normalization.** Decoding `%28`/`%29` and tidying formatting is allowed,
  but must keep the extension. For example `%28858%29569-6633ext.462` becomes
  `(858) 569-6633 ext. 462`.
- **Tests.** The four partners above, plus extension variants (`x132`,
  `ext.462`, `extn.1608`).

## Data cleanup

Two records store URL-encoded phones: electrical_training_institute and
strategic_energy_innovations (`%28858%29500-4161`). Normalize them with the
extension kept, as person edits through `partners put`, pending Eric's OK.

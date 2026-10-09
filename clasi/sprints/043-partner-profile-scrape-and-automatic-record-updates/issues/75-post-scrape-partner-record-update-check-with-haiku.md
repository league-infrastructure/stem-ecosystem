---
status: in-progress
sprint: '043'
tickets:
- 043-004
- 043-005
- 043-006
- 043-008
- 043-009
- 043-010
- 043-011
---

# Post-scrape partner-record update check, with Haiku for changed partners

## Description

Stakeholder direction (Eric, 2026-10-08):
- After the scrape, an extra process checks whether important partner
  information needs updating.
- If important things changed, run a Haiku process to update the partner
  record.
- Keep the old record (it may be enough that it is versioned).
- Write the results to an `updates` log.

Motivating case: CMOD (2026-10-08). The checks below would have caught
the rename, the new domain, the dead Twitter/X link, the moved Facebook and
Instagram accounts, the old-domain email, and the stale "Since 1999"
description.

## Proposal

The job is `partner-scrape updates` / `run-job updates`, run after
`profiles` (issue 74).

1. **Change check (no LLM).** For each partner whose profile snapshot
   changed (content hash) or has a notable redirect, compare against the
   curated record:
   - website host vs final URL;
   - name vs title/site_name/JSON-LD name;
   - phone, email domain vs website domain, address;
   - social links (also checking liveness);
   - logo URL.

   Each difference is a **flag** with a severity.
2. **Haiku step (only for flagged partners).** Model
   `claude-haiku-4-5-20251001`. It reads the cached home/About/Contact pages
   and the current record. It returns a proposed updated record:
   - corrected fields;
   - a fresh description written in our own words, not copied;
   - a confidence and a short reason per change.

   Results are cached by page-content hash, so an unchanged site costs
   nothing on the next run.
3. **Output:**
   - The proposed changes and flags go to `logs/updates/<ts>.log` (issue 72)
     and to a machine-readable `updates/<ts>.json` (proposed record, old
     record, diff).
   - The old record is preserved in that file even if the curated file
     is later changed.

## Key design question: where does "update the record" land?

`src/data/partners.json` is **hand-curated, tracked in Git, and baked into
the scraper image at build time**. The swarm container cannot commit to
Git. Options:

- **A. Propose only.** The job writes proposed records. A person (or the
  agent, on request) reviews them and applies them to `partners.json` in
  Git. Git keeps history. This is the simplest and safest choice.
- **B. Container opens a pull request** with the changes. That needs a
  GitHub token on the swarm (as a swarm secret), scoped to this repo.
  Review happens in the PR, and Git keeps history.
- **C. Move the curated roster to the bucket** (the bucket becomes the
  source of truth; the site and image read it from there). Auto-apply
  then becomes possible, with dated backups under a private prefix.
  This is the biggest change, and loses Git review.

## Cost

Typical week: a handful of flagged partners × ~3 pages × Haiku is a few
cents. Unflagged partners cost nothing.

## Related

- One-off variant: a Claude Code skill, "audit a partner", that runs
  steps 1 and 2 for one named partner on demand. Use it for inbound emails
  like CMOD's, and to draft the reply. Could be its own small issue.
- Event-quality checks (issue 76) feed the same report.

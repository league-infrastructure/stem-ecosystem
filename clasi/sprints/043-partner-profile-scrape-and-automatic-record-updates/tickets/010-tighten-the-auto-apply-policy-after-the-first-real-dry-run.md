---
id: '010'
title: Tighten the auto-apply policy after the first real dry run
status: open
use-cases:
- SUC-003
- SUC-004
depends-on:
- "008"
github-issue: ''
issue: 75-post-scrape-partner-record-update-check-with-haiku.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Tighten the auto-apply policy after the first real dry run

## Description

The team-lead's real `updates --dry-run` on 2026-10-09 against all 211 partners found 106 partners with approvable changes (20 within cap, 86 deferred). CMOD proposals were correct, but many others would damage curated data:

- Replacing named contact emails/phones with generic ones (Samantha@theABF.org -> info@theabf.org; bradford@bsd.education -> info@bsd.education; lschmelz@csusm.edu -> cstem@csusm.edu; anza_borrego phone 8189150336 -> 7607670446). The roster's email/phone are often the curated partner contact, not the public address.
- Wrong or lossy name changes without rebrand evidence ("Discover U at San Diego Public Library" -> "San Diego Public Library"; "EAA Chapter 14" -> "Chapter 14"; "Coronado Public Library" -> "Coronado Library").
- Website set to a site-builder staging host (batiquitos_lagoon_foundation -> https://batiquitos-lagoon-foundation-142729.multiscreensite.com/).

Replace the allowlist-only apply rule with a field-aware policy. Keep: confidence >= 0.8, never-blank, protected fields, shape checks, validator gate. Cap stays 20.

**AUTO-APPLY**
- Fill an EMPTY phone/email/social field.
- Replace a social link with the site's own current link for that network (same-network domain), including dead-link replacement.
- website: only when the proposed value's host equals the snapshot's observed home-page `final_url` host from a notable redirect (`website_moved` flag), and the host is not a site-builder/staging host. Deny list (suffix match): multiscreensite.com, wixsite.com, squarespace.com, godaddysites.com, weebly.com, webflow.io, wordpress.com, netlify.app, vercel.app, github.io.
- name, description, location: only when the partner has a HIGH-severity `website_moved` flag (rebrand evidence) in this run.

**REPORT-ONLY** ("needs review", not applied): changing an existing non-empty email or phone; name/description/location without `website_moved`; logo; anything else.

Needs-review items must appear in both the stdout report and the JSON report so the stakeholder can act on them.

## Acceptance Criteria

- [ ] Apply policy implements the auto-apply and report-only rules above; the old allowlist-only rule is removed.
- [ ] Filling an empty phone/email/social field applies.
- [ ] Social replacement applies only for the same-network domain (including dead-link replacement); cross-network values are report-only.
- [ ] Website applies only on a `website_moved` flag with proposed host == snapshot home `final_url` host and not on the deny list (suffix match); the batiquitos multiscreensite.com case is rejected.
- [ ] name/description/location apply only with a HIGH-severity `website_moved` flag in the run.
- [ ] Changing an existing non-empty email/phone is report-only (Samantha@theABF.org, bradford@bsd.education, lschmelz@csusm.edu, anza_borrego phone cases).
- [ ] The lossy name cases (Discover U, EAA Chapter 14, Coronado Public Library) are report-only absent rebrand evidence.
- [ ] CMOD fixture still applies name, website, facebook, description; its phone change is report-only (acceptable).
- [ ] Logo changes are report-only.
- [ ] Needs-review items appear in stdout and JSON reports (partner, field, current, proposed, reason).
- [ ] Cap remains 20; confidence >= 0.8, never-blank, protected fields, shape checks, validator gate unchanged.
- [ ] DESIGN.md documents the new policy and why (the 2026-10-09 dry-run evidence).

## Implementation Plan

- Approach: rework the apply-policy module from ticket 005 into per-field rules taking the partner's snapshot and flags as context; the `updates` job (ticket 006) passes flags/snapshot in and collects rejected-for-policy items as `needs_review`; extend the report writers.
- Files to modify: apply policy module and `updates` job/report code under `scraper/partner_scrape/`, `scraper/tests/` policy and updates tests, `scraper/docs/design/DESIGN.md` (and README if it describes the policy).
- Add a staging-host deny list constant in the policy module.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: table-driven policy tests for each evidence case above (report-only), staging-host rejection, fill-empty applies, social same-network replacement, website_moved gating, HIGH-severity gating for name/description/location, CMOD fixture end-to-end, and needs-review presence in stdout and JSON reports.
- **Verification command**: `cd scraper && uv run pytest`

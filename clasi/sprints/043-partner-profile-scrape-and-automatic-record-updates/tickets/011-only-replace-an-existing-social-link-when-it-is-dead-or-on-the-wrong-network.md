---
id: '011'
title: Only replace an existing social link when it is dead or on the wrong network
status: done
use-cases:
- SUC-003
- SUC-004
depends-on:
- '010'
github-issue: ''
issue: 75-post-scrape-partner-record-update-check-with-haiku.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Only replace an existing social link when it is dead or on the wrong network

## Description

The second real dry run (policy from ticket 010) showed that existing, working local-chapter social links would be replaced by national/parent accounts, because the partner's page footer links the parent org:

- challenge_island_san_diego_coastal: local FB/IG/LinkedIn -> ChallengeIslandHQ / challengeisland / challenge-island-llc
- brain_balance_of_san_diego: brainbalancesandiego -> brainbalancecenters
- aops: local campus FB -> national
- citizen_schools: linkedin slug -> numeric id
- encorps: facebook

Narrow ticket 010's "replace a social link with the site's own current link" rule. Replacing a NON-EMPTY social link auto-applies only if:

(a) the current value is on the wrong network's domain (e.g. a twitter URL in the linkedin field); the agua_hedionda and aquillius cases must still apply; or
(b) the link checker reports the current link dead (404/410/exception).

Otherwise the change goes to `needs_review` with a reason. Filling an EMPTY social field still auto-applies. In `--no-llm` / no-link-checker mode, (b) cannot fire, so such changes go to `needs_review`.

## Acceptance Criteria

- [x] Non-empty social replacement auto-applies only when the current value is on the wrong network's domain, or the link checker reports it dead (404/410/exception).
- [x] Otherwise it is reported as needs_review with a clear reason, in stdout and JSON reports.
- [x] Filling an empty social field still auto-applies.
- [x] agua_hedionda and aquillius cases (wrong-network current value) still apply.
- [x] challenge_island_san_diego_coastal, brain_balance_of_san_diego, aops, citizen_schools, and encorps cases are needs_review when the current link is live.
- [x] A dead current link (404, 410, or exception) allows replacement with the site's same-network link.
- [x] With no link checker available (`--no-llm` mode), the dead-link condition cannot fire and such changes are needs_review.
- [x] Other 010 rules, cap of 20, and gates are unchanged; DESIGN.md updated with the rationale.

## Implementation Plan

- Approach: in the apply policy's social-field rule, add a "current link status" input (live/dead/unknown) supplied by the `updates` job from the existing link checker, plus a wrong-network check on the current value. Unknown or live with correct network -> needs_review.
- Files to modify: apply policy module and `updates` job under `scraper/partner_scrape/`, policy/updates tests, `scraper/docs/design/DESIGN.md`.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: one test per case listed above (agua_hedionda, aquillius apply; challenge_island, brain_balance, aops, citizen_schools, encorps needs_review), dead-link (404, 410, exception) applies, empty-field fill applies, no-link-checker mode yields needs_review.
- **Verification command**: `cd scraper && uv run pytest`

## Follow-up fix

Real dry run showed `fetcher_link_checker` returned dead on ANY exception, so
robots-disallowed (Instagram/Facebook/LinkedIn) and bot-walled social links
were reported "(record link is dead)" and bypassed this rule (e.g.
challenge_island_san_diego_coastal, brain_balance_of_san_diego, encorps).
Fixed in `scraper/partner_scrape/updates/checks.py`: dead only on an actual
HTTP 404/410 from a non-social host; exceptions, `RobotsDisallowed`, timeouts,
transport errors, 403/429/5xx are unknown (`None`); facebook/fb/instagram/
twitter/x/linkedin hosts are never fetched and always unknown (logged-out
fetches are unreliable even for 404). `None` never sets `Flag.dead` or yields
`social_dead`. Dead-link replacement for social networks therefore goes to
needs_review. Rationale in `updates/DESIGN.md`; tests added.

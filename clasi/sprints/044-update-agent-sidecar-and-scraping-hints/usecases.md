---
status: draft
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 044 Use Cases

## SUC-001: Start an update session for a listing
Parent: issue 83

- **Actor**: Partner or any visitor (via site JavaScript)
- **Preconditions**: Service reachable; daily spend cap not reached; listing slug exists.
- **Main Flow**:
  1. Site calls start-session with `{type, slug}`.
  2. Service resolves the entity (non-partner types resolve to their partner/entity record) and loads current hints.
  3. Service returns session id, entity summary, current hints, limits and the fallback email.
- **Postconditions**: A session exists with a transcript stub; no hints changed.
- **Acceptance Criteria**:
  - [ ] Unknown slug returns 404 with fallback email; non-partner types resolve.
  - [ ] Refused with `spend_cap_reached` when the daily cap is hit.

## SUC-002: Converse and propose hints
Parent: issue 83

- **Actor**: Visitor
- **Preconditions**: Active session.
- **Main Flow**:
  1. Visitor sends a message.
  2. Guard classifies it; legitimate messages go to the agent.
  3. Agent explains the rule, edits the proposed hints only through a structured tool, and replies.
  4. Response carries the reply and the full proposed hints.
- **Postconditions**: Proposed hints updated in session; nothing saved.
- **Acceptance Criteria**:
  - [ ] Agent has no way to change anything except proposed hints.
  - [ ] Off-domain page URLs and unverifiable identity moves are rejected with an explanation and the email fallback.

## SUC-003: Guard ends abusive or off-topic sessions
Parent: issue 83

- **Actor**: Guard model
- **Main Flow**: Non-legitimate message (off-topic, spam, abuse, injection, supplying content) ends the session with a polite message and the email fallback; a short reason is logged.
- **Acceptance Criteria**:
  - [ ] Ended sessions accept no further messages; reason in transcript.
  - [ ] Guard backend can be Anthropic (default) or OpenRouter (config, off by default).

## SUC-004: Confirm hints
Parent: issue 83

- **Actor**: Visitor
- **Main Flow**: Visitor confirms; the service validates and writes `hints/<slug>.json` through `HintWriter`, archiving the prior version and appending to `changes.jsonl` with actor `update-agent:<session>`.
- **Acceptance Criteria**:
  - [ ] Confirm is idempotent; no-op writes leave no archive.
  - [ ] Response states changes take effect at the next scheduled scrape.

## SUC-005: Abuse and cost are bounded
Parent: issue 83

- **Actor**: Operator
- **Main Flow**: CORS limited to configured origins; per-IP and per-listing rate limits; turn and message-length caps; persisted daily spend cap; optional Turnstile; IP stored only as salted hash; transcripts private.
- **Acceptance Criteria**:
  - [ ] Each control has a test with fakes.
  - [ ] Spend counter survives a restart (persisted).

## SUC-006: Scraper uses hints
Parent: issue 83

- **Actor**: Scheduled scraper jobs
- **Main Flow**: `profiles` honors page hints; `updates` passes note/identity as proposer context without bypassing policy; normalize drops events matching exclude hints; updates report lists event-source page hints and which hints were used.
- **Acceptance Criteria**:
  - [ ] Hints never set a record field directly.
  - [ ] Excluded events are counted in the run log.

## SUC-007: Operate the service on the swarm
Parent: issue 83

- **Actor**: Operator
- **Main Flow**: Image built and pushed, stack redeployed, health and a live smoke conversation verified, deployment recorded in league-network.
- **Acceptance Criteria**:
  - [ ] `https://updates.jtlapp.net/healthz` returns 200 and the swarm service is healthy.
  - [ ] Smoke conversation produces a confirmed hint file in the bucket.

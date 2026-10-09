# Updates

**Owner:** Eric Busboom · **Last reviewed:** 2026-10-08 (sprint 043) · **Status:** in progress

Automatic partner record updates (issue 75).

## checks.py (043-004) -- no-LLM change check

`compare_partner(record, snapshot, link_checker=None) -> list[Flag]` is pure.
`run_checks(roster, history_store, cache_store, link_checker=, all_partners=,
slug=) -> CheckReport` selects partners whose snapshot hash (sha256 of the
snapshot fingerprint) differs from `updates/state.json` in the scrape-cache
store, or that have a notable redirect, or all with `all_partners` (`--all`).
It does not write state; the job calls `save_state(cache, report.new_state)`
after downstream work succeeds. Partners without a snapshot are listed in
`no_snapshot`.

Severity is `low < medium < high`; a partner is sent to Haiku when any flag
is >= medium (`needs_llm`, `CheckReport.flagged_for_llm`).

| kind | severity | rule |
|---|---|---|
| website_moved | high | record website host vs home final URL host (ignoring www) |
| name_mismatch | medium | record name matches none of title segments / og:site_name / JSON-LD name |
| phone_mismatch | medium | record phone (last 10 digits) not among tel:/JSON-LD phones, when both exist |
| email_domain_mismatch | medium | record email domain not same/sub of current site host, not a free-mail domain, not listed on site |
| address_mismatch | medium | JSON-LD street/postal not found in record `location` |
| social_changed | medium | record link differs from the site's link for that network |
| social_dead | medium | record link is dead and the site links none |
| social_new | low | site links a network the record lacks |
| logo_changed | low | JSON-LD logo differs from `logo_src` (report-only) |
| site_unreachable | low | home page failed |

Name comparison lower-cases, strips punctuation/apostrophes, drops stop
words (the, of, and...) and suffix words (inc, llc, org, foundation, home...),
then requires token Jaccard >= 0.8.

**Liveness** is an injected `link_checker(url) -> True|False|None`;
`fetcher_link_checker(PoliteFetcher)` is the production one (GET; dead =
exception, 404 or 410; 403/429/999 bot walls are not dead). Only run for a
record link that does not match the site's. Snapshots hold no page bodies;
ticket 005 reads bodies from the fetch cache.


## proposer.py (043-005) -- Haiku proposer

`propose_for_partner(record, flags, snapshot, cache_store, proposer) ->
(Proposal, from_cache)`. Input to the model: current record + flags + trimmed
(6000 chars each) visible text of the home/About/Contact pages, read from the
fetch cache by the snapshot's page URLs (`load_page_texts`). Model
`claude-haiku-4-5-20251001`; `anthropic.Anthropic()` with no api_key;
JSON-schema `output_config`. Output: a list of `{field, value, confidence
0-1, reason}`; `description` is just another field. The prompt forbids empty
values/removals and copying page text (mission phrase quotes only if < 15
words). A similarity check (`drop_copied_description`) drops a description
sharing a verbatim run of >= 15 words with the page text and records a note.

**Cache key**: `updates/<slug>/<sha256(prompt_version, model, record, sha256 of
each page text)>.json` in the scrape-cache store. Unchanged record + pages =
zero API calls. Bump `PROMPT_VERSION` when prompt/schema semantics change.
`FakeProposer` (canned proposals, call log) is the test double.

## policy.py (043-005) -- apply policy (sole gate to PartnerWriter)

`apply_policy(record, proposal, min_confidence=0.8) -> PolicyResult{applied,
applied_fields, rejected}` is pure. Allowlist: name, website, phone, email,
location, twitter, facebook, instagram, linkedin, description. `logo_src` is
report-only; id, slug, latitude, longitude, organization_type never change.
Per field: confidence >= threshold; empty value rejected (so a social link is
never removed, report-only; a dead link can only be replaced by a link on the
same network's domain); URL/email/phone shape check; then
`validate_records([candidate])` must pass, else that field is rejected.
`applied` is the full new record, or None when nothing applies. Ticket 006's
job calls `put_record(actor="haiku")` only with `result.applied`.

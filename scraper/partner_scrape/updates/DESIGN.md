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

## policy.py (043-005, reworked 043-010) -- apply policy (sole gate to PartnerWriter)

`apply_policy(record, proposal, flags=, snapshot=, min_confidence=0.8) ->
PolicyResult{applied, applied_fields, rejected, needs_review}` is pure.
`applied` is the full new record, or None when nothing applies; ticket 006's
job calls `put_record(actor="haiku")` only with it.

**Hard gates** (failure => `rejected`): confidence >= 0.8; never blank (a
social link is never removed); id/slug/latitude/longitude/organization_type
never change; URL/email/phone shape; `validate_records([candidate])`.

**Auto-apply** (field-aware, after the gates):
- fill an EMPTY phone / email / social field;
- replace a social link with one on the same network's domain (covers dead-link
  replacement);
- website: only with a `website_moved` flag, proposed host == the snapshot's
  home `final_url` host (www ignored), and host not in `STAGING_HOSTS`
  (suffix match: multiscreensite.com, wixsite.com, squarespace.com,
  godaddysites.com, weebly.com, webflow.io, wordpress.com, netlify.app,
  vercel.app, github.io);
- name, description, location: only with a HIGH-severity `website_moved` flag
  (rebrand evidence) in this run.

**Needs review** (`needs_review`: `{field, current, proposed, reason}`, never
applied): changing an existing non-empty email/phone; name/description/location
without rebrand evidence; a website not backed by the redirect or on a staging
host; a cross-network social value; `logo_src`; any other field.

Why: the first real `updates --dry-run` (2026-10-09, 211 partners) found 106
partners with approvable changes, and the old allowlist-only rule would have
replaced curated contacts with generic ones (Samantha@theABF.org ->
info@theabf.org, bradford@bsd.education -> info@bsd.education, lschmelz@csusm.edu
-> cstem@csusm.edu, anza_borrego phone), made lossy renames ("Discover U at San
Diego Public Library" -> "San Diego Public Library", "EAA Chapter 14" ->
"Chapter 14", "Coronado Public Library" -> "Coronado Library") and set a
website to a site-builder staging host (batiquitos_lagoon_foundation ->
*.multiscreensite.com). The roster's email/phone are often the curated partner
contact, not the public address. CMOD proposals were all correct and still
apply (name, website, facebook, description; its phone change is review-only).

## job.py (043-006) -- `partner-scrape updates`

`run_updates(roster, data_store=, history_store=, cache_store=, writer=,
proposer=, link_checker=, dry_run=, no_llm=, max_changes=20, slug=,
all_partners=)`. Flow: `run_checks` -> for `needs_llm` partners
`propose_for_partner` (cached) -> `apply_policy` -> `PartnerWriter.put_record(
slug, result.applied, actor="haiku")` (the single writer call; a test pins it)
-> `consolidate` if anything changed -> `save_state`.

- `--dry-run`: proposals are still fetched (and cached); no records, no
  consolidate, no state. `--no-llm`: flags only, no state saved (nothing was
  really handled, so partners stay due). `--max-changes N`: records changed
  per run; further approved changes are `deferred` and their state hash is not
  advanced, so they are re-examined (proposal cache hit) next run.
- A partner that raises (LLM or validation error) is reported as `ERROR`,
  keeps its old state hash, and does not stop the others; the CLI exits 1.
- Report: stdout lines `FLAG`, `REDIRECT`, `PROPOSED old -> new`, `APPLIED` /
  `WOULD APPLY`, `REJECTED field: reason`, `NEEDS REVIEW slug field: current -> proposed: reason`, `DEFERRED`, `ERROR`, and a counts
  line (run-job uploads stdout to `logs/updates/`). Machine-readable JSON per
  run at `updates/<UTC ts>.json` in the private history store: old record,
  flags, proposal, applied diff, rejections, `needs_review` (per partner and as a top-level list; also written on dry runs).
- Partners with a notable redirect are re-examined every run (a `checks.py`
  rule); run-job/crontab wiring is ticket 008.

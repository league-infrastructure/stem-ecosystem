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

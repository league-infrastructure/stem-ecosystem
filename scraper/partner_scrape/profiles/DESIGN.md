# Profiles

**Owner:** Eric Busboom · **Last reviewed:** 2026-10-08 (sprint 043) · **Status:** in progress

Partner profile scrape (issue 74). This ticket (043-002) adds the pure,
network-free, LLM-free pieces; the `profiles` job and snapshots come later.

## discover.py

`discover_profile_pages(home_url, html, sitemap_urls=()) -> DiscoveredPages`
(`about`, `contact`, ranked `candidates`). Anchors whose text matches about /
our story / who we are / mission, or contact / visit, then anchors whose path
matches, then sitemap URLs. Same site only (ignoring `www.`); mailto/tel/
fragment/file links skipped. Rank: source, keyword strength (explicit
"contact" beats "visit"), shallower path, first appearance, URL. At most one
About and one Contact are chosen.

## extract.py

`extract_facts(html) -> ProfileFacts`: `<title>`, `og:site_name`, JSON-LD
Organization/LocalBusiness/Museum (and close subtypes; `@graph` supported:
name, address, telephone, email, sameAs, logo, url), social links by network
(twitter incl. x.com, facebook, instagram, linkedin; footer links preferred;
share/intent links ignored), `mailto:` and `tel:` links. Uses stdlib
`html.parser`; no new dependency. Never raises on malformed HTML or JSON-LD.

## snapshot.py and job.py (043-003)

`partner-scrape profiles [--slug S] [--limit N]` loads the bucket Roster,
and for each partner with a website fetches home, then the discovered About
and Contact pages (sitemap.xml consulted only if one is missing) through
`PoliteFetcher(redirect_log=...)` (robots, throttle, cache, headless
fallback). Partners without a website are listed as `SKIPPED` and not
fetched. A failing page or partner is recorded and never aborts the run.

**Key layout** (history store, private): `profiles/<slug>/profile.json`
(bucket path `history/profiles/<slug>/profile.json`). Schema:
`version, slug, website, status (ok|partial|failed), fetched_at,
pages{home|about|contact: url, final_url, redirect_chain[[status,url]],
status, sha256 (of body; null on error), fetched_at, error},
facts{page: ProfileFacts dict}, redirects[{kind, requested, final}]`.
Overwritten each run, but only written when nothing exists or the
fingerprint (url, final_url, status, sha256, error per page; timestamps
excluded) changed. The job refuses a store with `public_read`.

The report prints `REDIRECT ...` lines from the RedirectLog, `SKIPPED`/
`FAILED` lines, then `profiles: partners= fetched= failed= redirects=
skipped= written= unchanged=`. `profiles` is a run-log type in `logs.py`.

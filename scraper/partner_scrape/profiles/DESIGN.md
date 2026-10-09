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

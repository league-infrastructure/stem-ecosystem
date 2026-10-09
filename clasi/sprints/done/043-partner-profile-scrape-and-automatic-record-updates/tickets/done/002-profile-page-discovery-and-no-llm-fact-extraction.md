---
id: '002'
title: Profile page discovery and no-LLM fact extraction
status: done
use-cases:
- SUC-002
depends-on: []
github-issue: ''
issue: 74-weekly-scrape-of-partner-home-about-and-contact-pages.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Profile page discovery and no-LLM fact extraction

## Description

Pure functions: discover About/Contact pages from a home page's nav links and sitemap, and extract structured facts with no LLM (issue 74).

## Acceptance Criteria

- [x] `profiles/discover.py` returns candidate About/Contact URLs (same-site only) from anchors matching about, our story, who we are, mission, contact, visit, and from sitemap URLs; deterministic order, at most 1 About and 1 Contact chosen
- [x] `profiles/extract.py` extracts: `<title>`, `og:site_name`, JSON-LD Organization/LocalBusiness/Museum (name, address, telephone, email, sameAs, logo), footer/page social links by network (twitter/x, facebook, instagram, linkedin), `mailto:` and `tel:` links
- [x] Malformed HTML/JSON-LD never raises; returns what it found
- [x] Fixture-based unit tests including a CMOD-like page; no network, no LLM

## Implementation Plan

New package partner_scrape/profiles/ with __init__, discover.py, extract.py. Use stdlib html.parser or the HTML library already in pyproject (check; add no new dependency if avoidable). Fixtures under tests/. Add profiles/DESIGN.md.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest`
- **New tests to write**: as listed in the acceptance criteria
- **Verification command**: `cd scraper && uv run pytest`

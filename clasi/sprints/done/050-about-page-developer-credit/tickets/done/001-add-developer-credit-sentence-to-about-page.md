---
id: '001'
title: Add developer credit sentence to About page
status: done
use-cases:
- SUC-001
depends-on: []
github-issue: ''
issue: 90-about-page-credits-the-league-as-site-developer.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Add developer credit sentence to About page

## Description

Add a sentence to the Our Partners section of `src/pages/about.astro`, after the hosting sentence: "This website is developed and maintained by The League of Amazing Programmers." with the name linking to https://www.jointheleague.org/ (site's normal link style). Keep the hosting sentence. Issue 90.

## Acceptance Criteria

- [x] Sentence present and links to https://www.jointheleague.org/
- [x] Hosting sentence unchanged
- [x] `npm test` and `npm run build` pass

## Testing

- **Existing tests to run**: `npm test`
- **New tests to write**: None required unless an existing about-page test exists to extend.
- **Verification command**: `npm test && npm run build`

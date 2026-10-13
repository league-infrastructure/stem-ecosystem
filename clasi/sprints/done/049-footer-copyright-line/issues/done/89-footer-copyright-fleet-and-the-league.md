---
status: done
sprint: 049
tickets:
- 049-001
---

# Footer copyright: Fleet Science Center and The League of Amazing Programmers

## Description

Stakeholder request (Eric, 2026-10-13): "change the copyright to be Fleet
Science Center and The League of Amazing Programmers."

Today `src/components/Footer.astro` reads "Copyright © {year} Fleet Science
Center. All Rights Reserved." Change it to "Copyright © {year} Fleet Science
Center and The League of Amazing Programmers. All Rights Reserved."

Keep the build-time year. Then deploy with the manual Deploy workflow.

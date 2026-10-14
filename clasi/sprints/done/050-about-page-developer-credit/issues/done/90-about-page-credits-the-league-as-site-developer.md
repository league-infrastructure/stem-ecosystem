---
status: done
sprint: '050'
tickets:
- 050-001
---

# About page credits The League of Amazing Programmers as the site developer

## Description

Stakeholder request (Eric, 2026-10-13), following the footer copyright
change (issue 89): the About page "should say that the site's developed by
The League of Amazing Programmers."

`src/pages/about.astro` line 43 reads: "The SD STEM Ecosystem is a collective
impact initiative hosted by the Fleet Science Center. We are supported by a
network of over 150 organizations …"

## Change

Keep the hosting sentence. Add a sentence that the website is developed by
The League of Amazing Programmers, linking to https://www.jointheleague.org/
with the site's normal link style. For example: "This website is developed
and maintained by The League of Amazing Programmers."

Then deploy with the manual Deploy workflow.

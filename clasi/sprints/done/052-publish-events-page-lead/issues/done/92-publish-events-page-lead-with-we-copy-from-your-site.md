---
status: done
sprint: '052'
tickets:
- 052-001
---

# Publish Events page: lead with "publish on your own site; we copy it"

## Description

Stakeholder feedback (Eric, 2026-10-14) on `src/pages/publish-events.astro`:

- **The subtitle has to go:** "Standard, documented ways to make your
  events easy for our scraper to find and ingest…". "Just remove that.
  It's gibberish."
- **Lead with how it works:** "At the very top of the page, the first thing
  you should mention is that you don't come to this site to publish events.
  The only way you publish events is by publishing them on your site, and
  we scrape them. That's first and foremost."
- **"What we need" lacks context:** "The way that you phrase it, 'however
  you publish, we ultimately need…'. They don't have a context for what
  you're talking about. What we're talking about is that this site only
  scrapes in order to get your content on our site. You have to publish it
  on your site, and then we copy it from there."

## Changes

1. Remove the hero subtitle.
2. The first content on the page is a plain-language lead (no jargon):
   - you don't publish events on this site;
   - you publish them on your own website, and we automatically copy
     (scrape) them from there on a regular schedule;
   - if an event isn't on your website, it can't appear here.
3. Rewrite "What we need" from the partner's point of view, with that
   context. Since we copy from your website, each event page should clearly
   show its title, date and time, location, cost, a short description and a
   link we can send people to (an image if you have one).
   - Remove the internal implementation text from this section: "Adapter
     framework", `partner_scrape/adapters/`, `ADAPTERS` table,
     `export.writer.SITE_SCHEMA_FIELDS`.
   - Keep a link to the data reference for those who want field details.
4. Leave the publishing-method sections (iCal, JSON-LD, …) in place for now.

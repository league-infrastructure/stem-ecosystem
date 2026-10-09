---
status: pending
related: clasi/issues/83-update-agent-sidecar-and-scraping-hints.md
---

# Update page and "request an update" links on the site

## Description

Stakeholder design (Eric, 2026-10-09). The website front end for the update
agent (issue 83).

## Links

- Every detail page gets a small block at the bottom (or in the sidebar on
  layouts that have one): "Is something here wrong or out of date? Request
  an update →". It links to `/update?type=<type>&slug=<slug>`. Pages:
  - partner;
  - opportunity, resolved to its partner;
  - team;
  - club;
  - place;
  - the Discovery Lab-style pages.
- The site footer gets a general "Need to update a listing?" link to
  `/update` with no listing, which lets you search for or pick the listing.

## /update page (static Astro page and client JavaScript)

- **Explainer at the top:** we only publish what's on your own website. Tell
  the assistant where to find the information and what's wrong, and the
  next scheduled scrape picks it up. It also gives the email address for
  anything else, using the site's existing contact address.
- **Two panels:** the chat on the left, and on the right a live **scraping
  hints** card. The card is rendered from the sidecar's proposed hints after
  every turn, with each hint readable (for example "Events: visitcmod.org/calendar",
  "Skip: Member's Only Hours"). The user corrects hints by chatting.
- **Confirm button:** saves the hints, shows a summary and "takes effect
  after the next scheduled scrape".
- **Guard-terminated sessions** show the polite stop message and the email
  fallback.
- **Accessibility and layout:** works without JavaScript to the extent of
  showing the explainer and the email fallback. Keyboard and screen-reader
  friendly. On phones the panels stack.
- **Configuration:** the sidecar base URL comes from build-time config
  (Astro env), not hard-coded.
- **No partner data** is entered through the page except the conversation
  itself.

## Out of scope

The sidecar itself (issue 83). Deploying the website: deploy stays manual
(Actions → Deploy → Run workflow).

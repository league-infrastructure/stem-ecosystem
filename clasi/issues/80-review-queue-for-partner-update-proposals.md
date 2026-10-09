---
status: pending
---

# A review queue for partner-record proposals the updates job won't auto-apply

## Description

After sprint 043's policy tightening, the updates job auto-applies only safe
changes:
- filling empty fields;
- replacing a social link on the wrong network;
- a redirect-backed website;
- name, description or location on a rebrand.

Everything else is reported as `NEEDS REVIEW`. The first real run
(2026-10-09) listed **185 needs-review items**. Examples:
- CMOD's email (Marketing@sdcdm.org → FrontDesk@visitcmod.org),
  Facebook (sdcdm → childrensmuseumofdiscovery) and phone (drop x1012);
- contacts changing from named people to generic addresses;
- name changes without a website move;
- chapter/franchise social links where the site footer points at the parent
  organization.

Today these live only in `logs/updates/*.log` and
`history/updates/<ts>.json`, with no way to act on them except hand-editing
with `partners put`.

## Proposal

- `partner-scrape partners review`: list the open needs-review items from the
  latest updates report, grouped by partner, with current and proposed values
  and the reason.
- `partner-scrape partners review --accept <slug> <field> [...]` and
  `--reject ...`:
  - accept applies through PartnerWriter with actor `person:<name>`;
  - reject records a decision so the item isn't re-proposed until the site
    changes again (keyed by page content hash).
- Optionally, a Claude Code skill ("audit a partner") for one-off requests
  like the CMOD email: run profiles plus updates for one slug, show the review
  items, and draft a reply email to the partner.

---
status: pending
related: clasi/issues/80-review-queue-for-partner-update-proposals.md, clasi/issues/81-never-drop-a-phone-extension-in-partner-updates.md
---

# Encode the phone and email review rules in the updates policy

## Description

On 2026-10-09 Eric reviewed the first batch of phone and email needs-review
items. He set rules ("those are good rules"; "take your best guess" on
phones) and had them applied by hand as person edits:
- 22 phone records changed and 15 kept;
- 8 email records changed and 13 kept.

The updates job (sprint 043 policy) still routes every change to an
existing phone or email to needs-review. It will keep re-proposing the kept
items weekly until rejections are remembered (issue 80). Encode the rules so
the job decides these itself.

## Phone rules

1. **Never drop an extension** (issue 81). Same base number without the
   extension is not a change.
2. **Keep** the existing number when it still appears on the partner's own
   pages (snapshot facts or cached page text).
3. **Keep** when the proposed number is toll-free (800/833/844/855/866/877/888)
   or out of area (not 619/858/760/442), i.e. a national or HQ line.
4. **Update** when the existing number is malformed (not 10 digits, or 11
   digits not starting with 1).
5. **Update** when the existing number is not on the site but the proposed
   local number is.
6. Otherwise keep.

## Email rules

1. **Update** when the existing address is broken: its domain redirects or is
   a typo of the site's domain (all_friends_nature_school), or it is on the
   partner's old domain after a move (CMOD sdcdm.org, hands-on-mobile.com).
2. **Update** a free-mail or personal-domain address (gmail, yahoo, a personal
   vanity domain) to an address on the organization's own domain that is
   listed on its site.
3. **Keep** a named person's address on the org's domain (or a parent org's
   domain) rather than a generic `info@`, `hello@`, `support@` or help-desk
   (`*.zendesk.com`) address. The roster's email is usually the curated
   contact.
4. **Keep** a program-specific role address (e.g. `stem@`) over a different
   org's general address unless it is known to bounce.
5. Two role addresses on the same domain: update to the one the site lists
   (agua_hedionda: account@ → sagesadvice@).

## Notes

- The decisions applied on 2026-10-09 are in `history/partners/changes.jsonl`
  with actor `person:eric (phone review, decided by claude)` and `person:eric
  (email review, decided by claude)`. Use them as test fixtures.
- Kept items should be remembered as rejected (issue 80) so they stop
  reappearing.

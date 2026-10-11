---
status: in-progress
sprint: '047'
tickets:
- 047-001
- 047-002
---

# Update page: compact header and a normal chat box

## Description

Stakeholder feedback (Eric, 2026-10-10), on the `/update` page after sprint
046:

- "You've got this enormous banner, this hero with 'Request an update'. It
  doesn't need to be the same template. You don't need all that space, that
  blue space. It can just be a normal-sized bar."
- "When you open the page, I can't see the text message box. It's down off
  the bottom. Just put it at the top. Do a normal chat box. I don't have to
  explain how all of that works."
- "I certainly don't need a whole page's worth of space between 'Chat with
  the update assistant' and then a whole page of empty space, and then make
  it to where the chat box is."

## Desired result

- **Header:** replace the full hero with a compact title bar (normal page
  heading height, at most ~80–100px tall including padding) reading
  "Request an update", plus the listing name when one is selected.
- **Explainer:** cut the "How updates work" section to one short line under
  the title. For example: "Tell us where on your website the right
  information is; we'll pick it up on the next scrape. Prefer email?
  partners@sdstemecosystem.org". Keep the no-JS fallback (that line and the
  email).
- **Chat:** a normal chat box.
  - The **message input is visible on first load without scrolling** on a
    1280×800 desktop and a 390×844 phone.
  - The transcript **sizes to its content**: no fixed full-viewport height
    and no empty reserved space. It grows downward from the panel heading,
    with the input immediately below the last message.
  - Only when the transcript exceeds a max height (e.g. ~60vh on desktop)
    does it scroll internally, with the input staying visible below it.
  - Drop or shrink the "Chat with the update assistant" heading.
- **Hints panel:** stays beside the chat on desktop (sticky, as in 046), and
  below the chat on phones.
- **Keep:** role=log/aria-live, keyboard use, auto-scroll to the newest
  message, and no "messages left".
- **Verification:** headless screenshots at 1280×800 and 390×844, without
  full-page capture, showing the input on first load and after 2–3 turns.

## References

- `src/pages/update.astro`, `src/scripts/update-chat.ts`
- Sprint 046 (`clasi/sprints/done/046-*`)

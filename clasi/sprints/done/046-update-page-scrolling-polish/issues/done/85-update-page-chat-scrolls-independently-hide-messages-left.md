---
status: done
sprint: '046'
tickets:
- 046-001
---

# Update page: the chat scrolls on its own; hide "messages left"

## Description

Stakeholder feedback (Eric, 2026-10-10), from trying `/update` on the dev
server:

1. "Make the left side (chat) scroll independently of the right (hints).
   The hints should stay fixed while the chat scrolls."
2. "Don't display the 'messages left', it's really prickly."

## Desired behavior

- **Desktop:** the chat panel has a bounded height (fits the viewport below
  the sticky site header). Its transcript scrolls inside the panel, and the
  message input stays visible at the bottom of the chat panel. The hints
  panel stays in view (sticky) as you scroll, and does not scroll with the
  chat.
- **New messages:** the transcript auto-scrolls to the newest message
  (respecting the user if they scrolled up to read).
- **Phone:** under the existing stacking breakpoint, keep the current
  stacked layout and normal page scrolling. Nested scroll areas on phones
  are awkward. The hints card may follow the chat as today.
- **Turn count:** remove the "N messages left in this conversation" line
  entirely. The turn cap is still enforced server-side; when it's reached,
  the existing polite end message shows.
- **Accessibility:** keep `role=log` and `aria-live`, and keep the
  scrolling region keyboard-focusable.

## References

- `src/pages/update.astro`, `src/scripts/update-chat.ts`

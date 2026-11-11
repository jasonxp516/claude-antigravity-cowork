# Frontend rules for the implementer (mandatory)
Derived from an Opus review of Gemini-written UIs. Follow all of them; the reviewer checks them.

## Ownership
- `index.html` / `*.css` written by the reviewer are the design. Do NOT edit them (they are protected). Build the UI by
  filling the provided `<template>` elements / classes; do not invent new visual styles inline.

## Rendering & state
- Show/hide only with the `hidden` attribute (never `style.display`). Elements that start hidden have `hidden` in HTML.
- One delegated event listener on the list container (no per-row listeners); build rows in a DocumentFragment.
- After any re-render, restore keyboard focus to the same control of the same `data-id`; after a delete, focus the next
  row (or the add input if none).
- Defaults for missing data are banned everywhere, including sorting and form prefill (no `?? 2`, no `|| 2`);
  if a value is missing, show/leave it empty.
- Labels must reflect state (e.g. toggle label "Mark … done" vs "Mark … open").

## Network
- Abort the previous list request with `AbortController` before starting a new one; ignore aborted results.
- Check `res.ok` BEFORE `res.json()`; parse errors safely (non-JSON bodies happen).
- Show friendly messages: prefix API errors with context (e.g. "Couldn't add task: <api error>"); never show raw
  `e.message` like "Failed to fetch" — say "Network error, please retry".
- Disable the triggering control while its request is in flight (no double submit / double delete).
- If you update UI optimistically, revert it on failure.

## Accessibility
- Status regions (`#counter`, `#error`) get `aria-live="polite"` (error may be `role="alert"`).
- Each interactive element has exactly one accessible name (don't double-label with `<label>` AND `aria-label`).
- Use `textContent`, never `innerHTML` with data.

## Markup contract
- If a `data-testid` or id in the spec must show a value, that value's text must be inside that element.

## Verify before finishing
- Run the acceptance command. Also load the page at 375px width with a long title and make sure nothing overflows.

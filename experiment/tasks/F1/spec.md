# F1 — Web UI for evtrack (`web/index.html`, `web/style.css`, `web/app.js`)
A single-page app, **vanilla HTML/CSS/JS only** (no frameworks, no build step, no external CDN/fonts), served by the
existing `python -m evtrack.web <store.json> <port>` (statics from `web/`, JSON API under `/api` — see `evtrack/api.py`:
`GET /api/tasks?q=`, `POST /api/tasks {"quick": ...}`, `PATCH /api/tasks/<id>`, `DELETE /api/tasks/<id>`; errors return `{"error": ...}`).

## Features
1. **Quick add**: a text input `#quick-add` (placeholder shows syntax hint, e.g. `Buy milk #home !1 due:tomorrow`).
   Enter submits via POST; on success clear the input and refresh the list; on 400 show the API error message in
   `#error` (visible) and keep the input text. Any later success hides `#error`.
2. **Filter**: input `#filter` using the query DSL (`status:open tag:home pri<=2 sort:due` …); list refreshes as the
   user types (debounced ~250 ms). Invalid query → show error in `#error`, keep the previous list.
3. **Task list** `#task-list`: one element per task with `data-testid="task-row"` and `data-id="<id>"`, containing:
   - a checkbox `input[type=checkbox].toggle` (checked = done) → PATCH status open/done, then refresh;
   - the title `.title`; done tasks visibly de-emphasized (e.g. strike-through, muted);
   - priority badge `.priority` showing `P1`/`P2`/`P3` with distinct colors (P1 most prominent);
   - tag chips `.tag` (one per tag, text `#tag`);
   - due date `.due` (text `YYYY-MM-DD`) if any; if the task is open and due < today add class `overdue` to the row
     and make it visually obvious;
   - a delete button `button.delete` with an accessible label (`aria-label="Delete <title>"`) → DELETE, then refresh.
4. **Counter** `#counter` with text exactly `<open> open · <done> done` for the tasks currently listed.
5. **Empty state** `#empty` visible (with a friendly message) when the list has no tasks; hidden otherwise.
6. Initial load lists all tasks (query empty) with default order = open tasks first, then by priority, then due (None last),
   then id — achieved client-side or by sending `sort:` terms.

## Quality bar
Looks like a polished modern product: clear visual hierarchy, consistent spacing scale, good typography, sufficient
contrast, hover/focus states, light **and** dark mode (`prefers-color-scheme`), responsive down to 375 px wide with no
horizontal scroll, all controls keyboard-accessible with visible focus and proper labels.

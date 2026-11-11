# F2 — Multi-view web app for evtrack (`web/` : index.html + CSS + JS, vanilla only)
No frameworks, no build step, no CDN/external fonts. Served by `python -m evtrack.web <store.json> <port>`; JSON API under
`/api` (see `evtrack/api.py`): tasks CRUD, `GET /api/agenda?start=&days=`, `GET /api/stats`,
`POST /api/tasks/<id>/complete`, `GET /api/export.csv|export.ics`, `POST /api/import` (raw body, Content-Type text/csv or text/calendar).
You may split CSS/JS into several files under `web/`.

## Shell & routing (hash router)
- A persistent top navigation `<nav>` with links `a[href="#/tasks"]`, `a[href="#/agenda"]`, `a[href="#/stats"]`, `a[href="#/io"]`
  (visible labels: Tasks, Agenda, Stats, Import/Export). The active link has `aria-current="page"`.
- One `<main id="view">` whose attribute `data-view` is the current view name: `tasks`, `task`, `agenda`, `stats`, `io`.
- Empty/unknown hash → tasks view. Deep links work on page load (e.g. opening `/#/stats`).
- A global error area `#error` (hidden when no error) used by all views; navigating to another view hides it.

## Views
1. **tasks** (`#/tasks`) — everything from the F1 list spec: `#quick-add` (Enter → POST; clear on success; API error → `#error`,
   input kept), `#filter` (query DSL, debounced), `#counter` text `<open> open · <done> done`, `#empty` state, rows
   `[data-testid=task-row][data-id]` with `.toggle` checkbox (PATCH status), `.priority` (`P1`/`P2`/`P3`), `.tag` chips (`#tag`),
   `.due` (`YYYY-MM-DD`), class `overdue` on open rows due before today, `button.delete` with `aria-label="Delete <title>"`.
   The title is a link `a.title` to `#/task/<id>`. Default order: open first, then priority, due (none last), id.
2. **task** (`#/task/<id>`) — edit form `#edit-form` with labeled fields: `[name=title]` text, `[name=priority]` select (1,2,3),
   `[name=tags]` text (comma-separated, shown as `a, b`), `[name=due]` `input[type=date]` (may be empty), `[name=status]`
   select (open, done). Submit → PATCH (tags split on commas, trimmed, empties dropped; empty due → null) → show `#saved`
   (text containing "Saved"). API error → `#error`. Button `#delete-task` → DELETE → go to `#/tasks`. Link `#back` → `#/tasks`.
   Unknown id → `#error` with a message.
3. **agenda** (`#/agenda`) — 7 days starting today (or `#/agenda/YYYY-MM-DD` = start date): one `[data-testid=agenda-day]`
   per day with `data-date="YYYY-MM-DD"`, a visible heading with weekday + date, and items `[data-testid=agenda-item]`
   (title + priority) or a visible "nothing" note. Buttons `#prev-week` / `#next-week` move the window by 7 days (update the hash).
   Each item has `button.complete` (`aria-label="Complete <title>"`) → `POST /api/tasks/<id>/complete` → refresh; if a
   recurring task produced a next occurrence, show a short notice in `#notice`.
4. **stats** (`#/stats`) — tiles `[data-testid=stat-total]`, `[data-testid=stat-open]`, `[data-testid=stat-done]` (each contains
   the number), `[data-testid=stat-rate]` (completion % with one decimal, e.g. `33.3%`); a priority breakdown with one
   `[data-testid=prio-bar]` per priority having `data-p="1|2|3"` and showing the count, bar length proportional to count
   (pure CSS/HTML, no chart library); top tags list `[data-testid=tag-stat]` (`#tag` + count); overdue list
   `[data-testid=overdue-item]` (links to the task).
5. **io** (`#/io`) — export links `a#export-csv` (href `/api/export.csv`) and `a#export-ics` (href `/api/export.ics`), both with
   `download` attribute; import: `input#import-file[type=file]` (accept .csv,.ics) + `button#import-btn` → read file, POST to
   `/api/import` with Content-Type `text/csv` for .csv and `text/calendar` for .ics → `#import-result` text `Imported <n> tasks`;
   error → `#error`.

## Quality bar
Polished, coherent product across all views (shared design language), clear hierarchy, consistent spacing scale, good
typography, contrast in light AND dark (`prefers-color-scheme`), visible focus, responsive to 375px (no horizontal scroll),
keyboard accessible with proper labels; loading/empty/error states designed, not raw.

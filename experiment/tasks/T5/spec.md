# T5 — WSGI JSON API (`evtrack/api.py`)
Implement `make_app(store, today_fn=datetime.date.today)` returning a WSGI callable (stdlib only).
All responses are JSON with header `Content-Type: application/json`.
- `GET /tasks` → 200 `[task.to_dict(), ...]`; optional query string `q=<query>` (URL-encoded) filtered with `filter_tasks`.
- `POST /tasks` body `{"quick": "<text>"}` → parsed with `parse_to_task(text, today_fn())`, stored → 201 with the task dict.
- `GET /tasks/<id>` → 200 task dict.
- `PATCH /tasks/<id>` body JSON object of fields → `store.update` → 200 task dict. `due` given as ISO string or null must be converted to date/None.
- `DELETE /tasks/<id>` → 204 with empty body (no Content-Type requirement).
- Errors: unknown id → 404 `{"error": "..."}`; invalid JSON / ValueError / bad fields → 400 `{"error": ...}`; unknown path → 404; wrong method on a known path → 405.

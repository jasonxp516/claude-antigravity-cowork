# T1 — JSON storage layer (`evtrack/storage.py`)
Implement `class JsonStore` persisting `evtrack.models.Task` objects in one JSON file.
- `JsonStore(path)` — `path` is str or Path. File need not exist (empty store). Parent dir exists.
- `add(task) -> int` — assigns a new id = (max id ever assigned in this file) + 1, starting at 1; ids are never reused even after delete. Sets `task.id`, persists, returns id. If `task.id` is already set, raise `ValueError`.
- `get(id) -> Task` — raise `KeyError` if missing.
- `update(id, **fields) -> Task` — set given fields (must be Task field names except `id`, else `ValueError`), re-validate via Task construction (invalid values raise `ValueError` and leave the store unchanged), persist, return the updated Task.
- `delete(id)` — raise `KeyError` if missing.
- `list() -> list[Task]` — all tasks sorted by id ascending.
- Every mutation is persisted immediately and atomically (write temp file in same dir, then `os.replace`). A new `JsonStore` on the same path sees the data.
- File format: `{"next_id": int, "tasks": [task.to_dict(), ...]}`.

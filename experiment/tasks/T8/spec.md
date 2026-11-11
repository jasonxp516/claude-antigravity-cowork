# T8 — Undo/redo (`evtrack/history.py`)
`class HistoryStore` wraps a `JsonStore` (T1) and exposes the same methods `add, get, update, delete, list`
plus `undo() -> str`, `redo() -> str`, `can_undo() -> bool`, `can_redo() -> bool`.
- Every successful mutating call (`add`, `update`, `delete`) pushes one entry on the undo stack and clears the redo stack.
  Failed calls (exceptions) push nothing.
- `undo()` reverts the latest entry and moves it to the redo stack; returns a description:
  `"undo add <id>"`, `"undo update <id>"`, `"undo delete <id>"`. Nothing to undo → `IndexError`.
- `redo()` re-applies it, returns `"redo add <id>"` etc. Nothing to redo → `IndexError`.
- Undo of `add` deletes the task; redo of that `add` restores it **with the same id**. Undo of `delete` restores the task
  with the same id and all fields. Undo of `update` restores all previous field values.
- `HistoryStore(store, limit=50)`: the undo stack keeps at most `limit` entries (oldest dropped).
- The history is persisted next to the store file as `<store filename>.history.json`, so a new `HistoryStore` over a new
  `JsonStore` on the same path can still undo/redo. Restoring a specific id must not break the store's `next_id`
  rule (ids are never reused for new tasks). You may add small helper methods to `JsonStore` (e.g. to insert a Task
  with a given id) but must not change its existing behavior.

# Gemini 4 評審原文（2026-11-19）

對照表：`blind_map_b6.json`（後端）、`blind_map_f1_g4.json`（前端）。以下已揭盲。

## 稽核能力測試（審 C6 = 3.8 Flash low 的 T1–T6 程式；已知 bug：CLI 遇到 `-` 開頭字詞失敗、`update(due=str)` 丟出非 ValueError）

### AU_hy
```
- `evtrack/parser.py`: `parse_quick` uses `date.fromisoformat(val)` without checking `YYYY-MM-DD` format, so Python 3.14 accepts non-`YYYY-MM-DD` ISO strings like `due:20240110` or `due:2024-W01-1` instead of raising `ValueError`.
- `evtrack/query.py`: `filter_tasks` (`_parse_term`) uses `date.fromisoformat(val_str)` without checking `YYYY-MM-DD` format, so `due` comparisons accept strings like `due=20240110` or `due<2024-W01-1` instead of raising `ValueError`.
- `evtrack/cli.py`: `main` uses `parse_known_args` with `nargs="+"`/`nargs="*"` and rejects `extra`, causing `add TEXT...` and `list [QUERY...]` to fail with `error: unrecognized arguments` on tokens starting with `-` (e.g., `add buy -milk` or `list -milk`).
- `evtrack/recur.py`: `_EVERY_RE` uses `$` instead of `\Z`, so `next_occurrence` accepts rules with a trailing newline like `"every:3d\n"` instead of raising `ValueError`.
- `evtrack/api.py`: `task_id_regex` uses `$` instead of `\Z`, so paths with a trailing newline like `"/tasks/1\n"` match `/tasks/<id>` instead of returning 404.
```
    USAGE {"model": "gemini-4-hydrogen-high", "usage": {"input_tokens": 70139, "output_tokens": 21837, "thinking_tokens": 19787, "cache_read_tokens": 312770, "total_tokens": 91976}, "wall": 135.1}

### AU_ne
```
NO_ISSUES
```
    USAGE {"model": "gemini-4-neon-high", "usage": {"input_tokens": 79954, "output_tokens": 26034, "thinking_tokens": 23527, "cache_read_tokens": 461844, "total_tokens": 105988}, "wall": 260.6}

### AU_ar
```
NO_ISSUES
```
    USAGE {"model": "gemini-4-argon-high", "usage": {"input_tokens": 69925, "output_tokens": 9833, "thinking_tokens": 8592, "cache_read_tokens": 423061, "total_tokens": 79758}, "wall": 210.0}

### AU_fl
```
NO_ISSUES
```
    USAGE {"model": "gemini-3.8-flash-high", "usage": {"input_tokens": 165369, "output_tokens": 60063, "thinking_tokens": 57171, "cache_read_tokens": 2261037, "total_tokens": 225432}, "wall": 550.7}

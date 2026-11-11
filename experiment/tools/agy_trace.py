#!/usr/bin/env python3
"""Summarize what an agy (Antigravity) worker actually did, from its local trajectory DB.
Gemini's hidden reasoning is NOT stored locally, but every tool call is.

  agy_trace.py <conversation_id> [...]      # compact stats per conversation
  agy_trace.py --last N                     # last N conversations
Library: summarize(conv_id) -> dict
"""
import collections, glob, json, os, re, sqlite3, sys
from pathlib import Path

DIRS = [Path.home() / ".gemini/antigravity-cli/conversations", Path.home() / ".gemini/antigravity/conversations"]
ARG = re.compile(rb'\{"([A-Z][A-Za-z]+)":')


def db_path(conv):
    for d in DIRS:
        p = d / f"{conv}.db"
        if p.exists():
            return p
    return None


def classify(p):
    m = ARG.search(p)
    if not m:
        return None, b""
    s = p[m.start():m.start() + 600]
    if s.startswith(b'{"Action":"status"'):
        return "poll", s
    if b'"DurationSeconds"' in s[:40]:
        return "sleep", s
    if s.startswith(b'{"CommandLine"'):
        return ("test" if re.search(rb"pytest|unittest|npm (run )?test|playwright", s[:300]) else "cmd"), s
    if s.startswith(b'{"Content"'):
        return "write", s
    if b'"Replacement"' in s:
        return "edit", s
    if s.startswith(b'{"Path"') or s.startswith(b'{"EndLine"'):
        return "read", s
    return "other", s


def summarize(conv):
    p = db_path(conv)
    if not p:
        return {"conv": conv, "error": "trace not found"}
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    cnt, files_read, cmds = collections.Counter(), collections.Counter(), []
    for (st, payload) in c.execute("select step_type, step_payload from steps order by idx"):
        if st != 132 or not payload:
            continue
        k, s = classify(payload)
        if not k:
            continue
        cnt[k] += 1
        if k == "read":
            m = re.search(rb'"Path":"([^"]+)"', s)
            if m:
                files_read[os.path.basename(m.group(1).decode(errors="ignore"))] += 1
        if k in ("cmd", "test"):
            m = re.search(rb'"CommandLine":"((?:[^"\\]|\\.){0,80})', s)
            if m:
                cmds.append(m.group(1).decode(errors="ignore"))
    tool_calls = sum(cnt.values())
    waste = cnt["poll"] + cnt["sleep"]
    return {"conv": conv, "tool_calls": tool_calls, **dict(cnt),
            "waste_ratio": round(waste / tool_calls, 2) if tool_calls else 0,
            "reread": sum(v - 1 for v in files_read.values() if v > 1),
            "top_cmds": collections.Counter(x.split(" ")[0].split("/")[-1] for x in cmds).most_common(4)}


def one_line(s):
    if "error" in s:
        return f"trace {s['conv'][:8]}: {s['error']}"
    return (f"trace {s['conv'][:8]}: calls={s['tool_calls']} read={s.get('read',0)} write={s.get('write',0)} "
            f"edit={s.get('edit',0)} test={s.get('test',0)} cmd={s.get('cmd',0)} poll={s.get('poll',0)} "
            f"sleep={s.get('sleep',0)} waste={s['waste_ratio']:.0%} reread={s['reread']}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--last":
        n = int(args[1]) if len(args) > 1 else 5
        files = sorted(glob.glob(str(DIRS[0] / "*.db")), key=os.path.getmtime)[-n:]
        args = [Path(f).stem for f in files]
    for conv in args:
        s = summarize(conv)
        print(one_line(s) if "--json" not in sys.argv else json.dumps(s))

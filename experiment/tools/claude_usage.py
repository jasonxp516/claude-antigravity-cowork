#!/usr/bin/env python3
"""Sum Claude token usage from Claude Code transcript JSONL files.

  claude_usage.py FILE_OR_GLOB... [--since EPOCH] [--until EPOCH]
Dedupes assistant messages by message.id. Weighted cost uses price ratios relative to
base input (cache write 1.25x, cache read 0.1x, output 5x) -> "input-equivalent tokens" (IET).
"""
import argparse, glob, json, sys
from datetime import datetime

W = {"input_tokens": 1.0, "cache_creation_input_tokens": 1.25, "cache_read_input_tokens": 0.1, "output_tokens": 5.0}


def usage(paths, since=None, until=None):
    seen, tot, models = set(), {k: 0 for k in W}, {}
    for p in paths:
        for line in open(p):
            try:
                e = json.loads(line)
            except Exception:
                continue
            m = e.get("message") or {}
            u = m.get("usage")
            if e.get("type") != "assistant" or not u:
                continue
            ts = e.get("timestamp")
            if ts and (since or until):
                t = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                if (since and t < since) or (until and t > until):
                    continue
            mid = m.get("id") or e.get("uuid")
            if mid in seen:
                continue
            seen.add(mid)
            for k in W:
                tot[k] += u.get(k, 0) or 0
            models[m.get("model")] = models.get(m.get("model"), 0) + 1
    tot["IET"] = round(sum(tot[k] * w for k, w in W.items()))
    tot["turns"] = len(seen)
    tot["models"] = models
    return tot


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--since", type=float)
    ap.add_argument("--until", type=float)
    a = ap.parse_args()
    files = [f for p in a.paths for f in (glob.glob(p) or [p])]
    print(json.dumps(usage(files, a.since, a.until), indent=1))

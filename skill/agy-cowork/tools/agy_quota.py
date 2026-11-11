#!/usr/bin/env python3
"""Antigravity quota probe (zero-cost: `/usage` slash command does not call a model).

CLI:
  agy_quota.py                 # print table, exit 0=OK 1=LOW 2=EXHAUSTED (for worker model group)
  agy_quota.py --model ID      # status for the group that model belongs to
  agy_quota.py --json          # raw snapshot
Library:
  snapshot() -> dict, remaining_for_model(model_id, snap) -> (fraction, bucket_names)
"""
import argparse, json, os, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "metrics"
POLICY = ROOT / "config" / "model_policy.json"


def load_policy():
    return json.loads(POLICY.read_text())


def snapshot(log=True, tag=None):
    out = subprocess.run(["agy", "-p", "/usage", "--output-format", "json"],
                         capture_output=True, text=True, timeout=90, cwd=str(ROOT))
    data = json.loads(out.stdout)
    groups = data["command"]["data"]["groups"]
    snap = {"ts": time.time(), "tag": tag, "groups": []}
    for g in groups:
        desc = g.get("description", "")
        m = re.search(r"Models within this group:\s*(.*)", desc)
        members = [s.strip().lower() for s in m.group(1).split(",")] if m else []
        snap["groups"].append({
            "name": g["name"], "members": members,
            "buckets": {b["id"]: {"window": b.get("window"),
                                   "remaining": b.get("remaining_fraction", 1.0),
                                   "reset": b.get("reset_time")} for b in g["buckets"]},
        })
    if log:
        METRICS.mkdir(exist_ok=True)
        with open(METRICS / "quota.jsonl", "a") as f:
            f.write(json.dumps(snap) + "\n")
    return snap


def groups_for_model(model_id, snap):
    """Return every quota group that applies to a model id.

    Heuristic (no hard-coded model names): a group whose *name* contains a token of
    the model id (e.g. 'argon') is a dedicated bucket; groups whose member list
    mentions a family token (flash/pro/claude/gpt/...) are shared buckets. Argon is
    described as 'separate' but we conservatively apply both if both match.
    """
    toks = set(re.split(r"[-_.\s]+", model_id.lower()))
    hits = []
    for g in snap["groups"]:
        name_toks = set(re.split(r"[-_.\s]+", g["name"].lower()))
        member_toks = set(t for m in g["members"] for t in m.split())
        if (toks & name_toks) - {"gemini", "models", "and"}:
            hits.append(("dedicated", g))
        elif toks & member_toks - {"gemini"}:
            hits.append(("shared", g))
    dedicated = [g for k, g in hits if k == "dedicated"]
    return dedicated or [g for _, g in hits]


def remaining_for_model(model_id, snap):
    gs = groups_for_model(model_id, snap)
    if not gs:
        return None, []
    vals = [(b["remaining"], f'{g["name"]}/{bid}') for g in gs for bid, b in g["buckets"].items()]
    frac, _ = min(vals)
    return frac, vals


def status(frac, pol):
    if frac is None:
        return "UNKNOWN"
    if frac <= pol["quota"]["exhausted_below"]:
        return "EXHAUSTED"
    if frac <= pol["quota"]["low_below"]:
        return "LOW"
    return "OK"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tag")
    a = ap.parse_args()
    snap = snapshot(tag=a.tag)
    if a.json:
        print(json.dumps(snap, indent=1)); return 0
    for g in snap["groups"]:
        for bid, b in g["buckets"].items():
            print(f'{g["name"]:<24} {bid:<26} {b["remaining"]*100:6.2f}%  reset {b["reset"]}')
    pol = load_policy()
    model = a.model
    if not model:
        sys.path.insert(0, str(Path(__file__).parent))
        from agy_models import pick
        model = pick("worker", snap=snap)["model"]
    frac, _ = remaining_for_model(model, snap)
    st = status(frac, pol)
    print(f"model={model} min_remaining={frac if frac is None else round(frac*100,2)}% status={st}")
    return {"OK": 0, "LOW": 1, "EXHAUSTED": 2}.get(st, 0)


if __name__ == "__main__":
    sys.exit(main())

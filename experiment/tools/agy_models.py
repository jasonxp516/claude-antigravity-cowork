#!/usr/bin/env python3
"""Dynamic model picker for agy. Usage: agy_models.py --role worker|worker_hard|planner [--no-quota]"""
import argparse, json, re, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import agy_quota

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "metrics" / "models_cache.json"


def list_models(max_age=3600):
    if CACHE.exists() and time.time() - CACHE.stat().st_mtime < max_age:
        return json.loads(CACHE.read_text())
    out = subprocess.run(["agy", "models"], capture_output=True, text=True, timeout=90).stdout
    models = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and re.match(r"^[a-z0-9][\w.-]+$", parts[0]):
            models.append({"id": parts[0], "name": parts[1]})
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(models))
    return models


def version_key(mid):
    m = re.search(r"-(\d+(?:\.\d+)?)-", mid)
    return tuple(int(x) for x in m.group(1).split(".")) if m else (0,)


def pick(role, snap=None, use_quota=True, _seen=None):
    pol = agy_quota.load_policy()
    r = pol["roles"][role]
    _seen = (_seen or set()) | {role}
    models = [m["id"] for m in list_models()]
    if use_quota and snap is None:
        snap = agy_quota.snapshot(log=False)
    reasons = []
    if r.get("enabled", True):
        for fam in r["families"]:
            cands = [m for m in models if f"-{fam}-" in m and m.endswith("-" + r["effort"])]
            for mid in sorted(cands, key=version_key, reverse=True):
                frac = agy_quota.remaining_for_model(mid, snap)[0] if use_quota else 1.0
                if frac is None or frac >= r["min_remaining"]:
                    return {"role": role, "model": mid, "remaining": frac, "skipped": reasons}
                reasons.append(f"{mid}: remaining {frac:.1%} < {r['min_remaining']:.0%}")
    else:
        reasons.append(f"role {role} disabled")
    fb = r.get("fallback_role")
    if fb and fb not in _seen:
        res = pick(fb, snap, use_quota, _seen)
        res["skipped"] = reasons + res["skipped"]
        res["fallback_from"] = role
        return res
    return {"role": role, "model": None, "remaining": None, "skipped": reasons}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", default="worker")
    ap.add_argument("--no-quota", action="store_true")
    a = ap.parse_args()
    print(json.dumps(pick(a.role, use_quota=not a.no_quota), indent=1))

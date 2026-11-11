#!/usr/bin/env python3
"""Naive agy call (arm B): agy_raw.py --workdir DIR --tag T "prompt". Prints agy's reply; logs usage."""
import argparse, json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import agy_models, delegate
ap = argparse.ArgumentParser(); ap.add_argument("--workdir", required=True); ap.add_argument("--tag", default="")
ap.add_argument("prompt"); a = ap.parse_args()
m = agy_models.pick("worker")["model"]
r = delegate.run_agy(a.prompt, m, str(Path(a.workdir).resolve()))
with open(delegate.RUNS, "a") as f:
    f.write(json.dumps({"ts": time.time(), "tag": a.tag, "raw": True, "model": m, "agy_usage": r.get("usage"), "wall": r.get("wall")}) + "\n")
print(r.get("response", ""))

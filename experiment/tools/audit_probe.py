"""Audit-capability probe: ask a model to audit a known-buggy implementation (C6, flash-low, T1–T6).
Usage: audit_probe.py <workdir> <model> <base>   -> prints the audit reply + usage json line."""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import delegate
wd, model, base = sys.argv[1:4]
specs = "\n\n".join(Path(f"{wd}/specs/T{i}.md").read_text() for i in range(1, 7))
r = delegate.run_agy(delegate.AUDIT_PROMPT.format(base=base, specs=specs), model, str(Path(wd).resolve()), timeout=1800)
print((r.get("response") or "").strip())
print("USAGE", json.dumps({"model": model, "usage": r.get("usage"), "wall": round(r["wall"], 1)}))

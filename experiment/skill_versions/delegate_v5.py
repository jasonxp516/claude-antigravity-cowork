#!/usr/bin/env python3
"""Delegate an implementation job to Antigravity (agy) with an automatic acceptance gate.

The Claude side only reads the compact report this prints. The retry loop
(acceptance failure -> feed back to agy) costs zero Claude tokens.

  delegate.py --workdir DIR --spec a.md [--spec b.md ...] --accept "pytest -q tests/test_x.py"
              [--role worker] [--retries 2] [--protect 'tests/acceptance/*'] [--tag run-label]
              [--escalate-role worker_hard] [--timeout 900]

Exit codes: 0 accepted, 1 not accepted after retries, 3 quota exhausted (tell the user), 4 agy error.
"""
import argparse, concurrent.futures as cf, shutil, tempfile, fnmatch, glob, json, os, re, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import agy_quota, agy_models, agy_trace

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "metrics" / "runs.jsonl"

WRAPPER = """You are the implementation worker. Another engineer (the reviewer) wrote the spec below and
will only look at whether the acceptance command passes, so be precise and complete.

Rules:
- Work only inside this repository. Do not edit files matching these protected patterns: {protect}
- Implement exactly what the spec says; keep public names/signatures as specified.
- Run the acceptance command yourself and iterate until it passes: `{accept}`
- The given acceptance tests are only a few golden examples. Write your OWN thorough tests for every
  rule in the spec (normal, edge and error cases) under tests/ (not in protected paths) and make them pass.
- NEVER special-case or hard-code specific test inputs; implement the general rule. If a protected
  test contradicts the spec, keep the spec behavior and say so in your final reply.
- Run tests and other commands SYNCHRONOUSLY: when you run a command set WaitMsBeforeAsync to 300000 (5 min) so
  it finishes in the foreground. Never poll a background task's status repeatedly.
- Final reply: at most 6 short lines — files changed, anything you were unsure about. No code in the reply.

{specs}
"""


AUDIT_PROMPT = """You are a strict code auditor. Compare the changes in this repo (run `git diff {base}` and read new
untracked files) against the specs below. Report ONLY real problems: spec rules not implemented or
implemented wrongly, hard-coded special cases for specific inputs, missing error handling the spec
requires, edits outside the spec's scope. Do NOT modify any files.
Final reply: one line per problem as `- <file>: <problem>`; if none, reply exactly `NO_ISSUES`.

{specs}
"""


def sh(cmd, cwd, timeout=600):
    p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr)


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True).stdout


def ensure_clean_commit(cwd, msg):
    if git(cwd, "status", "--porcelain").strip():
        git(cwd, "add", "-A")
        subprocess.run(["git", "-c", "user.name=exp", "-c", "user.email=exp@local", "commit", "-qm", msg], cwd=cwd)
    return git(cwd, "rev-parse", "HEAD").strip()


def group_remaining(model, snap):
    _, vals = agy_quota.remaining_for_model(model, snap)
    return {name: round(v, 5) for v, name in vals}


def run_agy(prompt, model, cwd, conv=None, timeout=900):
    cmd = ["agy", "-p", prompt, "--model", model, "--mode", "accept-edits", "--output-format", "json"]
    if conv:
        cmd += ["--conversation", conv]
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    try:
        j = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return {"status": "ERROR", "response": (p.stdout + p.stderr)[-800:], "usage": {}, "wall": time.time() - t0}
    j["wall"] = time.time() - t0
    return j


def protected_changes(cwd, base, patterns):
    changed = git(cwd, "diff", "--name-only", base).split() + \
        [l[3:] for l in git(cwd, "status", "--porcelain").splitlines() if l.startswith("??")]
    return sorted({f for f in changed for pat in patterns if fnmatch.fnmatch(f, pat)})


def public_symbols(cwd, base):
    diff = git(cwd, "diff", base, "--unified=0", "--", "*.py", ":!tests/*")
    new_files = [l[3:] for l in git(cwd, "status", "--porcelain", "-uall").splitlines()
                 if l.startswith("??") and l.endswith(".py") and not l[3:].startswith("tests/")]
    syms = re.findall(r"^\+(?:class|def) ([A-Za-z]\w*)", diff, re.M)
    for f in new_files:
        try:
            syms += re.findall(r"^(?:class|def) ([A-Za-z]\w*)", Path(cwd, f).read_text(), re.M)
        except Exception:
            pass
    return sorted(x for x in set(syms) if not x.startswith("test"))


PAR_NOTE = """NOTE: you implement ONLY the single spec below. Other engineers implement other specs in
parallel in other copies of this repo — do not create, stub or edit modules that belong to other specs.
Your acceptance check is your own tests for this spec (run them with: {py} -m pytest -q <your test files>).
"""


def commit_all(cwd, msg):
    git(cwd, "add", "-A")
    subprocess.run(["git", "-c", "user.name=exp", "-c", "user.email=exp@local", "commit", "-qm", msg], cwd=cwd)


def parallel_stage(cwd, base, spec_paths, model, a, py):
    """Run each spec in its own git worktree concurrently, then merge branches back. Gemini-only cost."""
    tmp = tempfile.mkdtemp(prefix="agy_par_")
    jobs = []
    for i, sp in enumerate(spec_paths):
        br = f"par-{re.sub(r'[^A-Za-z0-9]', '', a.tag)}-{i}-{int(time.time())}"
        wt = os.path.join(tmp, f"w{i}")
        git(cwd, "worktree", "add", "-q", "-b", br, wt, base)
        prompt = WRAPPER.format(protect=", ".join(a.protect) or "(none)", accept="your own tests for this spec",
                                specs=PAR_NOTE.format(py=py) + f"## SPEC: {Path(sp).name}\n" + Path(sp).read_text())
        jobs.append((br, wt, prompt))
    with cf.ThreadPoolExecutor(len(jobs)) as ex:
        results = list(ex.map(lambda j: run_agy(j[2], model, j[1], timeout=a.timeout), jobs))
    attempts, usage, conflicts = [], {}, []
    for (br, wt, _), r in zip(jobs, results):
        for k, v in (r.get("usage") or {}).items():
            usage[k] = usage.get(k, 0) + v
        for f in protected_changes(wt, base, a.protect):
            git(wt, "checkout", base, "--", f)
        commit_all(wt, f"parallel {br}")
        m = subprocess.run(["git", "-c", "user.name=exp", "-c", "user.email=exp@local", "merge", "--no-edit", "-X", "theirs", br],
                           cwd=cwd, capture_output=True, text=True)
        if m.returncode:
            conflicts.append(br); git(cwd, "merge", "--abort")
        attempts.append({"model": model, "status": "PAR:" + str(r.get("status")), "conv": r.get("conversation_id"), "tokens": (r.get("usage") or {}).get("total_tokens"),
                         "wall": round(r.get("wall", 0), 1), "tampered": []})
    for br, wt, _ in jobs:
        git(cwd, "worktree", "remove", "--force", wt); git(cwd, "branch", "-D", br)
    shutil.rmtree(tmp, ignore_errors=True)
    return attempts, usage, conflicts, max(r.get("wall", 0) for r in results)


def tail(s, n=40, maxc=2500):
    return "\n".join(s.strip().splitlines()[-n:])[-maxc:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--spec", action="append", required=True)
    ap.add_argument("--accept", required=True)
    ap.add_argument("--role", default="worker")
    ap.add_argument("--escalate-role", default=None, help="role for the last retry if earlier attempts failed")
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--protect", action="append", default=[])
    ap.add_argument("--tag", default="")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--audit", action="store_true", help="after acceptance passes, run a fresh agy auditor and feed issues back once")
    ap.add_argument("--audit-role", default="auditor")
    ap.add_argument("--parallel", action="store_true", help="run each --spec concurrently in its own git worktree")
    ap.add_argument("--then-spec", action="append", default=[], help="specs that depend on --spec ones; run after merge")
    a = ap.parse_args()
    cwd = str(Path(a.workdir).resolve())

    t_start = time.time()
    snap0 = agy_quota.snapshot(tag=f"{a.tag}:before")
    pick = agy_models.pick(a.role, snap=snap0)
    model = pick["model"]
    pol = agy_quota.load_policy()
    frac = agy_quota.remaining_for_model(model, snap0)[0] if model else None
    if not model or agy_quota.status(frac, pol) == "EXHAUSTED":
        print(f"QUOTA_EXHAUSTED role={a.role} model={model} skipped={pick['skipped']} -> notify user to switch account")
        return 3

    base = ensure_clean_commit(cwd, f"pre-delegate {a.tag}")
    specs = "\n\n".join(f"## SPEC {i+1}: {Path(s).name}\n" + Path(s).read_text() for i, s in enumerate(a.spec))
    prompt = WRAPPER.format(protect=", ".join(a.protect) or "(none)", accept=a.accept, specs=specs)

    attempts, usage_tot, conv, ok, acc_out, tampered = [], {}, None, False, "", []
    py = sys.executable if "venv" in sys.executable else str(ROOT / ".venv/bin/python")
    if a.parallel and len(a.spec) > 1:
        pa, pu, conflicts, pw = parallel_stage(cwd, base, a.spec, model, a, py)
        attempts += pa
        for k, v in pu.items():
            usage_tot[k] = usage_tot.get(k, 0) + v
        if conflicts:
            print(f"NOTE merge conflicts (resolved by fix loop): {conflicts}")
        if a.then_spec:
            then = "\n\n".join(f"## SPEC: {Path(s).name}\n" + Path(s).read_text() for s in a.then_spec)
            prompt = WRAPPER.format(protect=", ".join(a.protect) or "(none)", accept=a.accept,
                                    specs="(Other specs are already implemented in this repo; build on them.)\n" + then)
        else:
            prompt = None  # go straight to the gate
        specs = specs + "\n\n" + "\n\n".join(Path(s).read_text() for s in a.then_spec)
    elif a.then_spec:
        specs = specs + "\n\n" + "\n\n".join(f"## SPEC: {Path(s).name}\n" + Path(s).read_text() for s in a.then_spec)
        prompt = WRAPPER.format(protect=", ".join(a.protect) or "(none)", accept=a.accept, specs=specs)
    r = {"response": ""}
    for i in range(a.retries + 1):
        if prompt is None:  # parallel stage already produced code: check the gate first
            rc, acc_out = sh(a.accept, cwd); ok = rc == 0
            attempts.append({"model": model, "status": "GATE", "accept_rc": rc, "tokens": 0, "wall": 0, "tampered": []})
            if ok:
                break
            prompt = (f"Several engineers implemented these specs in parallel and their work was merged. The acceptance command "
                      f"`{a.accept}` fails. Output (tail):\n```\n{tail(acc_out)}\n```\nFix the implementation (not protected tests) "
                      f"so it matches the specs and re-run until it passes. Reply in <= 4 lines.\n\n{specs}")
            continue
        if i == a.retries and i > 0 and a.escalate_role:
            esc = agy_models.pick(a.escalate_role, snap=snap0)["model"]
            if esc and esc != model:
                model, conv = esc, None  # fresh conversation on the stronger model
                prompt = prompt + f"\n\nNOTE: a previous attempt failed acceptance with:\n```\n{tail(acc_out, 30)}\n```\n"
        r = run_agy(prompt, model, cwd, conv=conv, timeout=a.timeout)
        for k, v in (r.get("usage") or {}).items():
            usage_tot[k] = usage_tot.get(k, 0) + v
        conv = r.get("conversation_id") or conv
        tampered = protected_changes(cwd, base, a.protect)
        if tampered:  # restore protected files, never trust a gate the worker edited
            git(cwd, "checkout", base, "--", *tampered)
        rc, acc_out = sh(a.accept, cwd)
        ok = rc == 0
        attempts.append({"model": model, "status": r.get("status"), "accept_rc": rc, "conv": r.get("conversation_id"),
                         "tokens": (r.get("usage") or {}).get("total_tokens"), "wall": round(r["wall"], 1),
                         "tampered": tampered})
        if r.get("status") == "ERROR" and i == 0 and not ok:
            print("AGY_ERROR", r.get("response")); return 4
        if ok:
            break
        prompt = (f"The acceptance command `{a.accept}` still fails. Output (tail):\n```\n{tail(acc_out)}\n```\n"
                  "Fix the implementation (not the protected tests) and re-run it until it passes. Reply in <= 4 lines.")

    audit = None
    if ok and a.audit:
        amodel = agy_models.pick(a.audit_role, snap=snap0)["model"] or model
        ar = run_agy(AUDIT_PROMPT.format(base=base, specs=specs), amodel, cwd, timeout=a.timeout)
        for k, v in (ar.get("usage") or {}).items():
            usage_tot[k] = usage_tot.get(k, 0) + v
        audit = (ar.get("response") or "").strip()
        attempts.append({"model": amodel, "status": "AUDIT", "conv": ar.get("conversation_id"), "tokens": (ar.get("usage") or {}).get("total_tokens"),
                         "wall": round(ar["wall"], 1), "tampered": []})
        if "NO_ISSUES" not in audit:
            fr = run_agy("An independent auditor reported these problems:\n" + audit[-3000:] +
                         "\nFix the real ones (ignore false alarms), keep all tests passing, re-run `" + a.accept +
                         "`. Final reply: one line per item: fixed / not-a-problem + reason.", model, cwd, conv=conv, timeout=a.timeout)
            for k, v in (fr.get("usage") or {}).items():
                usage_tot[k] = usage_tot.get(k, 0) + v
            tampered = protected_changes(cwd, base, a.protect)
            if tampered:
                git(cwd, "checkout", base, "--", *tampered)
            rc, acc_out = sh(a.accept, cwd); ok = rc == 0
            attempts.append({"model": model, "status": "AUDIT_FIX", "accept_rc": rc, "conv": fr.get("conversation_id"),
                             "tokens": (fr.get("usage") or {}).get("total_tokens"), "wall": round(fr["wall"], 1), "tampered": tampered})
            r = fr

    traces = [agy_trace.summarize(c) for c in dict.fromkeys(x.get("conv") for x in attempts) if c]
    tr = {k: sum(t.get(k, 0) for t in traces) for k in ("tool_calls", "read", "write", "edit", "test", "cmd", "poll", "sleep")}
    tr["waste_ratio"] = round((tr["poll"] + tr["sleep"]) / tr["tool_calls"], 2) if tr["tool_calls"] else 0

    snap1 = agy_quota.snapshot(tag=f"{a.tag}:after")
    q0, q1 = group_remaining(model, snap0), group_remaining(model, snap1)
    report = {
        "ts": time.time(), "tag": a.tag, "accepted": ok, "attempts": attempts, "role": a.role,
        "agy_usage": usage_tot, "quota_delta": {k: round(q0.get(k, 0) - q1.get(k, 0), 5) for k in q1},
        "quota_after": q1, "diffstat": git(cwd, "diff", "--stat", base).strip().splitlines()[-1:] or ["(no tracked changes)"],
        "files": sorted(f for f in set(git(cwd, "diff", "--name-only", base).split() +
                            [l[3:] for l in git(cwd, "status", "--porcelain").splitlines() if l.startswith("??")])
                        if "__pycache__" not in f),
        "public_symbols": public_symbols(cwd, base), "worker_note": (r.get("response") or "")[-600:],
        "accept_tail": "" if ok else tail(acc_out, 25, 1500), "base": base, "audit": audit, "trace": tr, "wall_total": round(time.time() - t_start, 1),
    }
    RUNS.parent.mkdir(exist_ok=True)
    with open(RUNS, "a") as f:
        f.write(json.dumps(report) + "\n")
    ensure_clean_commit(cwd, f"delegated {a.tag} accepted={ok}")

    # compact human/Claude-facing report
    print(f"[{a.tag}] ACCEPTED={ok} attempts={len(attempts)} models={[x['model'] for x in attempts]}")
    print(f"agy tokens={usage_tot.get('total_tokens')} quota_used={report['quota_delta']} left={q1}")
    print(f"files={report['files']} {report['diffstat'][0]}")
    print(f"public={report['public_symbols']}")
    print(f"worker trace: wall={report['wall_total']:.0f}s calls={tr['tool_calls']} tests={tr['test']} "
          f"polls={tr['poll']} waste={tr['waste_ratio']:.0%}" + ("  <-- high waste" if tr['waste_ratio'] > 0.2 else ""))
    if any(x["tampered"] for x in attempts):
        print(f"WARNING protected files were edited and restored: {[x['tampered'] for x in attempts]}")
    if audit is not None:
        print("audit:", "NO_ISSUES" if "NO_ISSUES" in audit else audit.replace("\n", " | ")[:700])
    print("worker:", report["worker_note"].strip().replace("\n", " | ")[:400])
    if not ok:
        print("--- acceptance tail ---\n" + report["accept_tail"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

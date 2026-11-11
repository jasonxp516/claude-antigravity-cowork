#!/usr/bin/env python3
"""Bounded wait for a background delegate.py run — keeps a subagent's 5-minute prompt cache warm.

Launch:   python3 delegate.py ... > R 2>&1; echo "EXIT=$?" >> R        (Bash, run_in_background)
Then loop: python3 wait_delegate.py R          (Bash with timeout=300000; repeat while it prints RUNNING)

Returns as soon as the run finishes (prints DONE + exit code; then `cat R`), otherwise after --chunk seconds
(default 270 < 300 s cache TTL) prints one RUNNING line. Each return is one cheap cache-hit turn (~0.1x context)
instead of a full cache rewrite (~1.25x context) after a >5 min idle gap.
"""
import os, re, sys, time

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    chunk = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--chunk=")), 270)
    if not args:
        sys.exit(__doc__)
    path, t0 = args[0], time.time()
    while True:
        txt = open(path, errors="ignore").read() if os.path.exists(path) else ""
        m = re.search(r"^EXIT=(\d+)", txt, re.M)
        if m:
            print(f"DONE exit={m.group(1)} — now read the report: cat {path}")
            return
        if time.time() - t0 >= chunk:
            age = int(time.time() - os.path.getmtime(path)) if os.path.exists(path) else -1
            print(f"RUNNING (waited {int(time.time() - t0)}s; report untouched {age}s) — call wait_delegate.py again")
            return
        time.sleep(5)

if __name__ == "__main__":
    main()

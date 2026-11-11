#!/usr/bin/env python3
"""Run F1 hidden tests + take standard screenshots. Usage: shoot_front.py <workspace> <outdir>
Run with the workspace on sys.path (cwd = workspace)."""
import os, subprocess, sys, tempfile, threading
from datetime import date, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
ws, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
NO_TESTS = "--no-tests" in sys.argv
r = None if NO_TESTS else subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider", str(ROOT / "tasks/F1/hidden")],
                   cwd=ws, capture_output=True, text=True)
if r: print("hidden:", (r.stdout.strip().splitlines() or ["?"])[-1])
sys.path.insert(0, str(ws)); os.chdir(ws)
from wsgiref.simple_server import make_server, WSGIRequestHandler
from playwright.sync_api import sync_playwright
from evtrack.models import Task
from evtrack.storage import JsonStore
from evtrack.web import make_web_app
T = date.today()
class Q(WSGIRequestHandler):
    def log_message(self, *a): pass
d = tempfile.mkdtemp(); s = JsonStore(Path(d) / "s.json")
for t in [Task("Prepare quarterly planning deck for the leadership offsite", priority=1, tags=["work", "q4"], due=T + timedelta(days=1)),
          Task("Buy milk", tags=["home", "shop"], due=T - timedelta(days=2)),
          Task("Call the dentist to reschedule", priority=2, tags=["health"]),
          Task("Water plants", priority=3, tags=["home"], due=T + timedelta(days=5)),
          Task("Renew passport", priority=1, due=T - timedelta(days=10)),
          Task("Read chapter 4", status="done", priority=3, tags=["reading"]),
          Task("Pay electricity bill", status="done", priority=2, tags=["home", "bills"], due=T - timedelta(days=1))]:
    s.add(t)
srv = make_server("127.0.0.1", 0, make_web_app(s), handler_class=Q)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_port}/"
with sync_playwright() as p:
    b = p.chromium.launch()
    def page(w, h, scheme="light"):
        pg = b.new_page(viewport={"width": w, "height": h}, color_scheme=scheme); pg.goto(url)
        try: pg.wait_for_selector("[data-testid=task-row]", timeout=5000)
        except Exception: pass
        pg.wait_for_timeout(400); return pg
    page(1280, 800).screenshot(path=str(out / "1_desktop_light.png"), full_page=True)
    page(1280, 800, "dark").screenshot(path=str(out / "2_desktop_dark.png"), full_page=True)
    page(390, 844).screenshot(path=str(out / "3_mobile_light.png"), full_page=True)
    pg = page(1280, 800)
    try:
        pg.fill("#quick-add", "oops !9"); pg.press("#quick-add", "Enter"); pg.wait_for_timeout(500)
        pg.locator("#quick-add").focus()
    except Exception as e: print("error-state failed:", e)
    pg.screenshot(path=str(out / "4_error_focus.png"))
    pg = page(1280, 800)
    try: pg.fill("#filter", "zzznomatch"); pg.wait_for_timeout(800)
    except Exception as e: print("empty-state failed:", e)
    pg.screenshot(path=str(out / "5_empty.png"))
    b.close()
srv.shutdown(); print("shots:", sorted(x.name for x in out.iterdir()))

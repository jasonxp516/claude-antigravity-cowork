#!/usr/bin/env python3
"""F2: run hidden tests (unless --no-tests) + 9 screenshots. Usage: shoot_f2.py <workspace> <outdir> [--no-tests]"""
import os, subprocess, sys, tempfile, threading
from datetime import date, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
ws, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(); out.mkdir(parents=True, exist_ok=True)
if "--no-tests" not in sys.argv:
    r = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "pytest", "-q", "-p", "no:cacheprovider", str(ROOT / "tasks/F2/hidden")],
                       cwd=ws, capture_output=True, text=True)
    print("hidden:", (r.stdout.strip().splitlines() or ["?"])[-1])
sys.path.insert(0, str(ws)); os.chdir(ws)
from wsgiref.simple_server import make_server, WSGIRequestHandler
from playwright.sync_api import sync_playwright
from evtrack.models import Task
from evtrack.storage import JsonStore
from evtrack.web import make_web_app
T = date.today(); D = lambda n: T + timedelta(days=n)
class Q(WSGIRequestHandler):
    def log_message(self, *a): pass
s = JsonStore(Path(tempfile.mkdtemp()) / "s.json")
for t in [Task("Prepare quarterly planning deck for the leadership offsite", priority=1, tags=["work", "q4"], due=D(1)),
          Task("Buy milk", tags=["home", "shop"], due=D(-2)), Task("Call the dentist to reschedule", tags=["health"]),
          Task("Water plants", priority=3, tags=["home", "rec-every:3d"], due=D(0)), Task("Renew passport", priority=1, due=D(-10)),
          Task("Weekly review", priority=2, tags=["work", "rec-weekly"], due=D(3)), Task("Read chapter 4", status="done", priority=3, tags=["reading"]),
          Task("Pay electricity bill", status="done", tags=["home", "bills"], due=D(-1))]:
    s.add(t)
srv = make_server("127.0.0.1", 0, make_web_app(s), handler_class=Q); threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_port}/"
shots = [("1_tasks_light", "#/tasks", 1280, "light"), ("2_tasks_dark", "#/tasks", 1280, "dark"), ("3_task_edit", "#/task/1", 1280, "light"),
         ("4_agenda_light", "#/agenda", 1280, "light"), ("5_agenda_dark", "#/agenda", 1280, "dark"), ("6_stats_light", "#/stats", 1280, "light"),
         ("7_stats_mobile", "#/stats", 390, "light"), ("8_agenda_mobile", "#/agenda", 390, "light"), ("9_io_dark", "#/io", 1280, "dark")]
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, h, w, sch in shots:
        pg = b.new_page(viewport={"width": w, "height": 800}, color_scheme=sch); pg.goto(url + h); pg.wait_for_timeout(700)
        pg.screenshot(path=str(out / f"{name}.png"), full_page=True); pg.close()
    b.close()
srv.shutdown(); print("shots:", len(list(out.glob("*.png"))))

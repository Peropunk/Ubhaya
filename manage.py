"""Project commands. Works the same on Windows, Linux and macOS:

    python manage.py run          start the API and interface on http://127.0.0.1:8000
    python manage.py load-demo    load the synthetic demo case (add --fresh to wipe first)
    python manage.py make-demo    regenerate data/demo_case from data/make_demo_case.py
    python manage.py verify       check every artifact hash and audit chain
    python manage.py test         run the test suite

The Makefile targets (make run, make test, make load-demo) call these.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))


def cmd_run(args) -> int:
    import uvicorn

    print(f"UBHAYA on http://{args.host}:{args.port}/ui/  (API docs at /docs)")
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload,
                app_dir=str(ROOT / "backend"))
    return 0


def cmd_load_demo(args) -> int:
    from app.config import get_settings
    from app.db import connect
    from app.demo import find_demo_case, load_demo

    settings = get_settings()
    if args.fresh:
        if settings.db_path.exists():
            settings.db_path.unlink()
            print(f"removed {settings.db_path}")
    with connect() as conn:
        existing = find_demo_case(conn)
        if existing and not args.fresh:
            print(f"demo case already loaded as {existing['id']}; use --fresh to reload")
            return 0
        result = load_demo(conn)
    case = result["case"]
    print(f"loaded {case['id']} '{case['title']}': {result['artifacts']} artifacts, "
          f"{result['statements']} statements, {result['events']} events")
    return 0


def cmd_make_demo(args) -> int:
    return subprocess.call([sys.executable, str(ROOT / "data" / "make_demo_case.py")])


def cmd_verify(args) -> int:
    from app.db import connect
    from app.intake import audit, service

    failures = 0
    with connect() as conn:
        cases = service.list_cases(conn)
        if not cases:
            print("No cases to verify. Check UBHAYA_DATA_DIR or run python manage.py load-demo.", file=sys.stderr)
            return 1
        for case in cases:
            for art in service.list_artifacts(conn, case["id"]):
                res = service.verify_artifact(conn, art["id"], actor="cli")
                failures += not res["ok"]
                print(f"{case['id']} {art['id']} {'OK  ' if res['ok'] else 'FAIL'} {art['sha256'][:16]}  {art['filename']}")
            chain = audit.verify(conn, case["id"])
            failures += not chain["ok"]
            print(f"{case['id']} audit chain: {'OK' if chain['ok'] else 'BROKEN at ' + str(chain['broken_at'])} ({chain['entries']} entries)")
    return 1 if failures else 0


def cmd_test(args) -> int:
    return subprocess.call([sys.executable, "-m", "pytest", *args.pytest_args], cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="UBHAYA project commands")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("load-demo")
    p.add_argument("--fresh", action="store_true", help="delete the local database first")
    p.set_defaults(func=cmd_load_demo)
    sub.add_parser("make-demo").set_defaults(func=cmd_make_demo)
    sub.add_parser("verify").set_defaults(func=cmd_verify)
    p = sub.add_parser("test")
    p.add_argument("pytest_args", nargs=argparse.REMAINDER)
    p.set_defaults(func=cmd_test)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

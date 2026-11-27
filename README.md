# UBHAYA

Offline prototype for the Surakshit Bharat Innovation Challenge 2026: checks every claim in witness, complainant and suspect statements against the digital evidence, and links each finding to its exact source row, line or frame.

**Synthetic data only.** Every person, place, number and image in `data/` is invented.

## Setup (Windows)

```powershell
.\scripts\setup_offline.ps1
```

This creates `.venv`, installs the pinned packages (from `vendor\wheels` if present, so it works with Wi-Fi off), loads the demo case and runs the tests. To prepare an offline copy, run `.\scripts\setup_offline.ps1 -Download` once while online. On Linux or macOS use `scripts/setup_offline.sh`.

## Run

```powershell
.\.venv\Scripts\python.exe manage.py run
```

Then open http://127.0.0.1:8000/ui/ (API docs at http://127.0.0.1:8000/docs).

| Command | What it does |
| --- | --- |
| `python manage.py run` | API and interface on port 8000 |
| `python manage.py load-demo [--fresh]` | Load the PC-14 demo case (`--fresh` wipes the local database first) |
| `python manage.py make-demo` | Regenerate `data/demo_case` from `data/make_demo_case.py` |
| `python manage.py verify` | Re-hash every artifact and check every audit chain |
| `python manage.py test` | Run the tests |

Each has a `make` target (`make run`, `make test`, `make load-demo`, ...); on Windows `make` is `mingw32-make`.

## Layout

```
backend/app/
  main.py          FastAPI routes (contract: docs/SPEC.md)
  models.py, db.py Pydantic models, SQLite storage
  intake/          hashing, read-only store, hash-chained audit log
  parsers/         door log, PC event log (UTC), UPI statement
  demo.py          one-command demo loader
  extract/ timeengine/ rules/ ranking/ report/   later phases
frontend/          screen 1 (case overview), plain HTML + JS, no build step
data/make_demo_case.py   generates data/demo_case/ and its answer key
docs/              SPEC.md (frozen), RULES.md (worked rule examples), PROGRESS.md (chunk tracker)
tests/
var/               local database and evidence store (git-ignored)
```

## Where we are

Phase 0 (except the people and model tasks) and Phase 1 are done. See `docs/PROGRESS.md` for the chunk-by-chunk status and the deviations from the plan text.

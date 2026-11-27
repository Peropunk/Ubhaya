# UBHAYA

Offline prototype for the Surakshit Bharat Innovation Challenge 2026: checks every claim in witness, complainant and suspect statements against the digital evidence, and links each finding to its exact source row, line or frame.

**Synthetic data only.** Every person, place, number and image in `data/` is invented.

## Setup (Windows)

Install Python 3.12 x64. From the repository folder in PowerShell, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_offline.ps1
.\.venv\Scripts\python.exe manage.py run
```

The execution-policy setting applies to that PowerShell process. A fresh Git
clone needs internet access for the first setup. The separate handoff ZIP
contains an earlier snapshot with offline wheels for Windows x64 and Linux
x86-64 with Python 3.12.

If you need to prepare wheels for another Windows configuration, run the same
setup command with `-Download` appended while online, then run it again without
`-Download`. Setup creates `.venv`, installs packages, loads the demo and runs
the tests. GitHub Actions runs setup and the tests on Windows and Linux on
pushes and pull requests.

## Setup (Linux or macOS)

Use Python 3.12.

```bash
bash scripts/setup_offline.sh
.venv/bin/python manage.py run
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
  parsers/         door, PC, UPI, WhatsApp and CCTV evidence
  demo.py          one-command demo loader
  analysis.py      case analysis, findings, reviews and evidence requests
  extract/ timeengine/ rules/ ranking/ report/   analysis and export modules
frontend/          case overview, evidence viewer, timeline, review and export
data/make_demo_case.py   generates data/demo_case/ and its answer key
docs/              SPEC.md (frozen), RULES.md (worked rule examples), PROGRESS.md (chunk tracker)
tests/
var/               local database and evidence store (git-ignored)
```

## Where we are

The cached PC-14 walkthrough covers intake through reviewed JSON and PDF export.
Live-model acceptance and the presenting-laptop rehearsal are still open.
See [the milestone tracker](docs/PROGRESS.md) for the status of each phase.

## Run the complete synthetic walkthrough

Start the server after loading the demo case. In **Overview**, select
**Verify all hashes**, then **Analyze case** to open the findings in **Statements**.

1. Open **The files were copied around 22:15** and select PC-14 row 22 to see the source and its UTC and IST times.
2. Toggle clock calibration in Timeline. The possible camera order conflict clears with calibration enabled.
3. Reject the 42-second V-03 repeat as a possible double tap. The blurry CAM-B still stays open for manual time entry.
4. Inspect **Accounts** and the ranked evidence drafts. Export the reviewed case from **Requests & report**.

The default demo uses bundled claim annotations and template suggestions.
It needs neither Ollama nor a local AI model. Live extraction and live
alternative suggestions use the Ollama service on the same machine as the
UBHAYA server. Extraction can also call Ollama when a statement has no
bundled annotation or saved manual claims. To try live mode, start the server with
`UBHAYA_EXTRACT_MODE=live` and set `UBHAYA_MODEL` to an installed model. Use a
separate `UBHAYA_DATA_DIR` when comparing extraction modes because each case
retains its saved claims. The measured live models exceeded the 30-second
target on this machine.

PDF export uses a local Chromium-based browser. It can discover Chromium
Headless Shell on PATH or in the local Playwright browser cache. On Windows it checks standard
Edge, Chrome and Brave install folders as well as PATH. Chromium Headless Shell
was used for the sample report. If discovery or rendering fails, set
`UBHAYA_BROWSER` to its executable path before starting the server. Report
JSON and the demo UI use the pinned Python environment.

Run `python eval/run_eval.py` from the project environment to evaluate the
cached demo in a temporary database. Use
`python eval/run_eval.py --benchmark qwen2.5:0.5b gemma:2b` with both models
installed to measure live extraction.

See [handoff materials](docs/handoff/README.md) for the pitch and results.

## Verify a rehearsed demo

The handoff ZIP includes a Python 3.12 wheelhouse for Windows x64 and Linux
x86-64 under `vendor/wheels`. Both setup scripts use it with `--no-index`.
On another platform or Python version, prepare a wheelhouse on the target
configuration before going offline.

Load a fresh synthetic case with `UBHAYA_EXTRACT_MODE=cached`, then start the
server with a working Chromium headless executable for PDF export. With
Playwright already installed, run `node scripts/verify_demo.cjs`.
`UBHAYA_DEMO_URL` defaults to the loopback server on port 8000.
`UBHAYA_CHROMIUM` optionally points Playwright to a local browser.
The verifier writes synthetic review decisions and checks the exported PDFs.

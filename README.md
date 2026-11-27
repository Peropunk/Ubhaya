# UBHAYA

UBHAYA is an offline evidence-review prototype for the Surakshit Bharat Innovation
Challenge 2026. It checks statements against the digital evidence in the
fictional PC-14 case and links findings to the exact source row, line, or frame.

**Use synthetic data only.** The demo runs on your laptop using the bundled
evidence, cached claim annotations, and rule engine. Ollama and a local model
are optional.

## Run the project

### 1. Get the code and install Python

Install **Python 3.12**. Use the 64-bit installer on Windows. If you already have
the repository, open a terminal in the folder that contains `manage.py` and
`requirements.txt`. To get a new copy with Git, run:

```text
git clone https://github.com/Peropunk/Ubhaya.git
cd Ubhaya
```

If your teammate shared a feature branch, run `git switch BRANCH_NAME` with the
shared branch name before setup.
Keep internet access available for first-time dependency installation, or
[prepare the offline wheels](#set-up-on-an-offline-laptop) in advance.

### 2. Set up and start the server

#### Windows PowerShell

Run these commands from the repository folder:

```powershell
python --version
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_offline.ps1
.\.venv\Scripts\python.exe manage.py run
```

If `python` points to a different version or you installed Python through the
Windows launcher, run `py -3.12 -m venv .venv` before setup so the script reuses
that environment. The execution-policy setting applies to the setup process.
The commands use the environment's Python directly, so activation is optional.

#### Linux or macOS

Run these commands from the repository folder:

```bash
python3 --version
bash scripts/setup_offline.sh
.venv/bin/python manage.py run
```

If `python3` points to another version and Python 3.12 is installed, run
`python3.12 -m venv .venv` before setup. If venv creation fails on Linux,
install the venv support package for your Python 3.12 installation and retry.

Both setup scripts create or reuse `.venv`, install Python dependencies, load
the PC-14 demo, and run the tests. A fresh demo load reports **12 artifacts,
3 statements, and 276 events**. Once setup has succeeded, use the last command
for subsequent launches. Run setup again if a Git pull changes the dependencies.

### 3. Open the workspace

Leave the server terminal running and open
[http://127.0.0.1:8000/ui/](http://127.0.0.1:8000/ui/) in Brave, Chrome, Edge, or
the VS Code browser preview. Use `Ctrl+C` in the server terminal to stop it.

- [Health check](http://127.0.0.1:8000/health) should return `{"status":"ok"}`.
- [API documentation](http://127.0.0.1:8000/docs) lists the available endpoints.
- The server binds to this laptop by default. Each teammate runs their own copy
  with a local SQLite database and evidence store under `var/`.

## Walk through the PC-14 demo

1. In **Overview**, select **Verify all hashes**. On a fresh case, **12 of 12 hashes match** and the audit chain is **Intact**. Open any filename to inspect the stored evidence and its SHA-256 digest.
2. Select **Analyze case**. The app opens **Statements** with **18 findings**. Open **The files were copied around 22:15**, expand **Why this finding?**, and select **pc14_events.csv row 22** under **Cited evidence**. The viewer highlights the source row and shows its normalized time interval.
3. Open **Timeline** and turn **Apply clock calibration** off. The possible camera-order conflict appears. Turn calibration back on and the conflict clears.
4. On the timeline alert for repeated V-03 badge scans 42 seconds apart, enter a reviewer name, choose **reject**, enter a reason such as “The repeated scan may be a double tap,” and select **Save review**. Leave the blurry CAM-B frame flagged as **Manual time required** to show the unresolved evidence.
5. Open **Accounts** to browse findings by speaker. In **Requests & report**, read the ranked evidence requests and select **Download JSON** or **Download PDF** to export the reviewed case.

## PDF export

JSON export works after the standard Python setup. PDF rendering uses a local
Chromium-family executable. UBHAYA looks for Chromium Headless Shell in the
Playwright browser cache or on PATH. It also checks desktop browser commands
and standard install folders for browsers such as Edge, Chrome, and Brave.

If PDF export fails or times out, stop UBHAYA, set `UBHAYA_BROWSER` to a
working Chromium or Chromium Headless Shell executable, then restart from the
same terminal. Replace the example path with the executable on your laptop.

**Windows PowerShell**

```powershell
$env:UBHAYA_BROWSER = 'C:\path\to\chrome-headless-shell.exe'
.\.venv\Scripts\python.exe manage.py run
```

**Linux or macOS**

```bash
export UBHAYA_BROWSER="/path/to/chrome-headless-shell"
.venv/bin/python manage.py run
```

## Set up on an offline laptop

While online, use the download mode on the target platform, architecture,
and Python version. This fills `vendor/wheels/` with the dependency files.

**Windows PowerShell**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_offline.ps1 -Download
```

**Linux or macOS**

```bash
bash scripts/setup_offline.sh --download
```

Copy the current repository and `vendor/wheels/` to the offline machine,
omitting `.venv/` and `var/`. Run the normal setup script from
[step 2](#2-set-up-and-start-the-server) to create a local virtual environment
and demo database. When `vendor/wheels/` exists, setup installs from that
folder using `--no-index`. If you plan to
export PDFs offline, install and rehearse the local browser renderer before
disconnecting.

The separate handoff ZIP contains an earlier source snapshot and Python 3.12
wheels for Windows x64 and Linux x86-64. Use the current checkout for the latest
interface.

## Optional live extraction with Ollama

The standard demo uses the bundled annotations and can run with Ollama closed.
Live extraction and live alternative suggestions call the Ollama service at
`127.0.0.1:11434` on the laptop running UBHAYA. A statement with neither a
bundled annotation nor saved claims can also need Ollama for automatic
extraction. You can enter manual claims in **Statements**.

To try live mode, start Ollama and make sure `ollama list` shows the model you
want to use. The examples use `gemma:2b`. Substitute the exact installed model
name. Use a new data directory for each model comparison because existing cases
reuse saved claims.

**Windows PowerShell**

```powershell
$env:UBHAYA_EXTRACT_MODE = 'live'
$env:UBHAYA_MODEL = 'gemma:2b'
$env:UBHAYA_DATA_DIR = Join-Path $env:TEMP ('ubhaya-live-' + [guid]::NewGuid())
.\.venv\Scripts\python.exe manage.py load-demo
.\.venv\Scripts\python.exe manage.py run --port 8001
```

**Linux or macOS**

```bash
export UBHAYA_EXTRACT_MODE=live
export UBHAYA_MODEL=gemma:2b
export UBHAYA_DATA_DIR="$(mktemp -d)"
.venv/bin/python manage.py load-demo
.venv/bin/python manage.py run --port 8001
```

Open [http://127.0.0.1:8001/ui/](http://127.0.0.1:8001/ui/) for that run.
The measured live models exceeded the 30-second target on the development
machine. To measure an installed model separately, run
`python eval/run_eval.py --benchmark gemma:2b` with the project's Python.
For the cached demo again, use a new terminal with the default environment and
the standard run command.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| The browser cannot connect | Keep `manage.py run` active, open the URL and port printed in its terminal, and check `/health`. |
| Port 8000 is already in use | Append `--port 8001` to the run command and use [http://127.0.0.1:8001/ui/](http://127.0.0.1:8001/ui/). |
| VS Code and Brave show different layouts | Use the same `/ui/` URL and port in both. Widen the VS Code preview to compare desktop layouts. If one still shows the old sidebar, hard-refresh Brave or close and reopen the preview. |
| No case appears | Run `manage.py load-demo` with the virtual environment's Python and the same `UBHAYA_DATA_DIR` used by the running server, then refresh the browser. |
| Setup cannot find a dependency offline | Prepare `vendor/wheels/` for the target platform and Python version. For an online install, move an incomplete wheelhouse aside and rerun setup. |
| PDF export fails | Set `UBHAYA_BROWSER` and restart as shown in [PDF export](#pdf-export). Use **Download JSON** to export the report without a PDF renderer. |

## Verify the installation

On Windows, use `.\.venv\Scripts\python.exe` for `python` below. On Linux or
macOS, use `.venv/bin/python`.

| Command | What it does |
| --- | --- |
| `python manage.py load-demo` | Loads the synthetic case if it is absent. |
| `python manage.py verify` | Re-hashes stored artifacts and checks each case's audit chain. |
| `python manage.py test` | Runs the Python tests. GitHub Actions runs setup and tests on Windows and Linux. |
| `python eval/run_eval.py` | Scores the cached demo in a temporary database. Expected result is 18 correct verdicts, five planted contradictions, and zero false contradictions. Run from a terminal with the default extraction mode. |
| `python manage.py make-demo` | Regenerates the synthetic fixtures in `data/demo_case/`. |

`load-demo --fresh` deletes the configured SQLite database, including all cases
and reviews in that database. For a clean rehearsal, set `UBHAYA_DATA_DIR` to a
new directory before loading the demo and starting the server.

For an optional automated browser rehearsal, install Node.js, Playwright and
its Chromium browser. With Playwright available to Node, load a clean demo
database and start the server in cached mode with a working PDF renderer. Run
`node scripts/verify_demo.cjs` from another terminal in the repository folder.
The script expects case `C001`, records synthetic reviews, and verifies three
walkthroughs and exports. Set `UBHAYA_DEMO_URL` to the server origin if you
changed the port, `UBHAYA_PLAYWRIGHT` to the Playwright module path if installed
outside the repo, or `UBHAYA_CHROMIUM` to use a specific browser executable
for the test.

## Repository layout

| Path | Contents |
| --- | --- |
| `backend/app/` | FastAPI, SQLite storage, intake, parsers, analysis, review, and reporting |
| `frontend/` | Offline HTML, CSS, JavaScript, and bundled fonts |
| `data/demo_case/` and `cache/` | Synthetic evidence, answer key, and cached claim annotations |
| `scripts/` and `tests/` | Setup scripts, browser walkthrough, and Python tests |
| `var/` | Local database and evidence store, ignored by Git |
| `docs/` | [API spec](docs/SPEC.md), [rules](docs/RULES.md), [milestones](docs/PROGRESS.md), and [handoff materials](docs/handoff/README.md) |

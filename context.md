# UBHAYA agent handoff

## Project and current state

- UBHAYA is an offline prototype for the Surakshit Bharat Innovation Challenge 2026. It checks statements against evidence in the fictional PC-14 case and links findings to source rows, lines and frames in the UI. The JSON and PDF exports record findings and reviewer decisions.
- Use [the development plan](UBHAYA%20Prototype%20Development%20Plan.md) for scope, [the tracker](docs/PROGRESS.md) for milestone status, and [the API spec](docs/SPEC.md) and [rule examples](docs/RULES.md) for contracts. The [README](README.md) explains setup and the demo path.
- The cached demo works end to end. The final event freeze and live-model acceptance are still open.

## Run on Windows and Linux

Use Python 3.12 x64 for the tested Linux setup and the prepared Windows wheel set. A clean Git checkout normally downloads dependencies during first setup. The separate `../UBHAYA-handoff.zip` bundles Windows x64 and Linux x86-64 wheels in `vendor/wheels`. Setup preserves existing case data. The explicit `load-demo --fresh` option deletes the configured database before loading.

Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_offline.ps1
.\.venv\Scripts\python.exe manage.py run
```

Linux:

```bash
bash scripts/setup_offline.sh
.venv/bin/python manage.py run
```

Open <http://127.0.0.1:8000/ui/> and select **Analyze case** in **Overview** to jump to **Statements**. Open the file-copy claim and inspect its supporting USB event at PC-14 row 22 and the copy events at rows 23–31. In **Timeline**, toggle calibration and review the V-03 repeat. Export from **Requests & report**.

- **Ollama is optional for the bundled demo.** Cached mode uses exact-quote annotations and template suggestions. New uncached statements can call Ollama for automatic extraction. Manual claims are also supported.
- For live AI, start Ollama on the same machine as UBHAYA, install a local model, and set `UBHAYA_EXTRACT_MODE=live` and `UBHAYA_MODEL` before launching UBHAYA. The backend uses `127.0.0.1:11434`. Use a fresh `UBHAYA_DATA_DIR` for comparison because stored claims are reused. Your teammate does not need access to your laptop.
- PDF export needs a local Chromium-based browser. The app looks on PATH and in standard Edge, Chrome and Brave install folders on Windows. Set `UBHAYA_BROWSER` to the executable path if discovery or rendering fails. JSON export has no browser dependency.

Claim detail includes **Why this finding?** with the saved verdict, claim window, rule explanations and unresolved question. When a ranked request addresses the claim, its link opens the matching draft. The explanation runs offline.

## Where the code lives

| Area | Files and behavior |
| --- | --- |
| App and storage | `manage.py` runs FastAPI. `backend/app/main.py` serves the API and static UI. `backend/app/db.py` owns SQLite storage. `backend/app/intake/` handles SHA-256, the read-only evidence store, and audit entries. |
| Evidence and time | `backend/app/parsers/` handles door, PC, UPI, WhatsApp, and CCTV. `backend/app/timeengine/` handles ISO bounds in IST and claim time windows. Original times and locators remain available. |
| Extraction | `backend/app/extract/` contains local Ollama calls, quote validation, a versioned prompt, fallback loading, and overlay recognition. `cache/` contains annotations keyed to the statement text hash. |
| Reasoning and workflow | `backend/app/analysis.py` joins extraction, matching, timeline, review, requests and reporting. `backend/app/rules/` and `backend/app/ranking/` implement the synthetic rules and request ranking. `backend/app/report/` produces PDF through a local browser. |
| UI | `frontend/` is plain HTML, CSS and JavaScript. FastAPI serves it at `/ui/`. It has no build step or CDN dependency. |
| Demo and evaluation | `data/demo_case/` contains the synthetic fixtures. `eval/run_eval.py` compares results with the answer key. Keep the answer key out of runtime reasoning. Preserve fixture bytes and quote offsets when moving across operating systems. |
| Handoff and CI | [Handoff guide](docs/handoff/README.md) links the reports, slides, recording, results and organiser draft. `.github/workflows/tests.yml` runs Windows and Linux setup and tests on pushes and pull requests. |

## Verified baseline

- **42 Python tests passed on Linux** in the pre-push check. The integrity CLI reports an empty database as a failure. The Windows wheel set resolved offline. Native Windows execution still needs a CI result after push or a teammate's run.
- Three browser walkthroughs passed with the case-file interface, including exact source locators, calibration, review, JSON and PDF export. PDF export discovered Chromium Headless Shell in the Playwright browser cache. An earlier rehearsal also exercised offline installation with loopback only. See [offline verification](docs/handoff/offline-verification.md).
- Cached evaluation matched **18 of 18 claim spans and verdicts**, found **five planted contradictions**, and recorded zero false claim contradictions. The V-03 double tap is a separate alert, reviewed as a suspected false alarm. See [evaluation results](docs/handoff/evaluation.json).
- The demo has 12 artifacts, 3 statements and 276 events before manual time entry. PC-14 row 22 retains `16:44:05Z` and gets an IST range of `22:13:05–22:15:05`. The possible camera ordering conflict clears after calibration.
- The built-in overlay reader and Tesseract both read the clear frames. The built-in reader requests manual time for the blurry frame. See [overlay results](docs/handoff/overlay-results.md).
- The five-minute narrated backup, six-slide pitch, and sample reviewed JSON and PDF reports are complete. Files live under `docs/handoff/`. The workspace-level ZIP is a separate packaging snapshot. Later source edits require a rebuild before distributing an updated ZIP.

## Integrity boundary

Artifact verification compares stored bytes with the intake digest. Audit verification checks the sequence and hashes of the entries present and flags an empty history. A valid prefix can still pass after deletion of the final entries. Detecting that loss requires an independently trusted record of the expected chain head.

## Remaining work

1. **Live extraction qualification.** The plan requires at least 15 of 18 claims correct and under 30 seconds per statement. Gemma 2B and Qwen2.5 0.5B timed out on the development laptop. Three further short-prompt trials also timed out. Report live results separately from cached evaluation. For evidence, use [the original benchmark](docs/handoff/model-benchmark.json) and [the short-prompt rerun](docs/handoff/model-benchmark-short-prompt.json).
2. **Native Windows verification.** Verify the Windows CI job after push, then check PDF export on the teammate's setup. Keep Python, setup paths, and report generation portable.
3. **Presenting-laptop check.** Time setup and run the full demo three times with Wi-Fi off on the designated machine. The Linux loopback-only run verifies an offline environment on the development machine.
4. **Event sign-off.** Written organiser approval, checkpoint feedback, team sign-offs and two timed presenter rehearsals remain open. The organiser message is a [draft](docs/handoff/organiser-draft.md). Final freeze and submission depend on the remaining gates and organiser instructions.

For regression checks, use `python manage.py test` and `python eval/run_eval.py` from the project virtual environment. With the demo running and Playwright installed, `node scripts/verify_demo.cjs` exercises the browser path and writes synthetic review records. Start those checks from a fresh synthetic case when comparing runs.

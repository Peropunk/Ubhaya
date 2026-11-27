# Chunk tracker

Status of every chunk in the development plan. Update this when a chunk's "done when" passes.

| ID | Chunk | Status | Proof |
| --- | --- | --- | --- |
| P0.1 | Ask organisers what may be prepared in advance | **Open (PM, people task)** | |
| P0.2 | Synthetic case pack + answer key | Done | `data/make_demo_case.py`; `tests/test_demo.py` (18 claims, quotes exact, planted rows) |
| P0.3 | Frozen data schemas and API spec | Done, needs RE + FE review | `docs/SPEC.md` |
| P0.4 | LLM bake-off | **Open**: Ollama not installed on this laptop | |
| P0.5 | OCR bake-off | **Open**: no OCR engine installed yet | |
| P0.6 | Rule specs with worked examples | Done | `docs/RULES.md` |
| P0.7 | Wireframes for 6 screens | Partly: screen 1 built; tabs for 2 to 6 stubbed | `frontend/` |
| P0.8 | Offline setup script | Done for Python packages; models pending P0.4/P0.5 | `scripts/setup_offline.ps1`, `.sh` |
| P1.1 | Repo scaffold | Done | `make run`; `tests/test_api.py` |
| P1.2 | Intake, read-only store, audit chain | Done | `tests/test_intake.py` (re-hash matches; edited entry breaks chain) |
| P1.3 | Fixture loader | Done | `make load-demo` → C001, 12 artifacts, 3 statements, 236 events |
| P1.4 | Parsers: door, PC log (UTC), UPI | Done | `tests/test_parsers.py` |
| P1.5 | Interface shell: case overview | Done | http://127.0.0.1:8000/ui/ |

## Deviations from the plan text (decided in P0.2 / P0.6)

1. **Ravi's "dhaba pahunch gaya" chat is at 22:07, not 22:03.** With ± 60 s ranges, a 22:03 chat sits only 8:53 after the latest possible badge OUT (21:53:07), so R4 (12 min travel) would wrongly flag his real trip as "possible two places at once". At 22:07 the real trip is clean and every planted R4 conflict is still certain. Worked numbers in `docs/RULES.md` §3 R4.
2. **calibration.json has two records**, CAM-A (0 s ± 60 s) and CAM-B (+420 s ± 60 s). With CAM-A uncalibrated (± 10 min) the CAM order conflict would never fully vanish when calibration is switched on.
3. **Without calibration the CAM order conflict fires as R1 *possible*, not *certain*,** because uncalibrated CCTV is ± 10 min. It shows as uncertain and disappears with calibration on.
4. **Strength depends on the claim.** A bank entry is direct evidence of a payment but indirect evidence of where a person was; a login is direct for "the account was used" but indirect for "Ravi sat at the keyboard". This is what makes M4 and Ravi's R3 come out uncertain (the case's open question) while M5 and M6 are contradicted.
5. **Case date is 3 Dec 2025** (one constant in the generator).
6. **Interface is plain HTML + JS served by FastAPI at `/ui`**, no build step and no CDN, so it runs offline with nothing extra to install. The plan's "React or Streamlit" choice is still open; the API contract is the same either way.
7. **`make` on Windows is `mingw32-make`**; every target is a thin wrapper over `python manage.py <command>`, which works everywhere.

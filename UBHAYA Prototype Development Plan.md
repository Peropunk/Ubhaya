# UBHAYA: Prototype Development Plan

Surakshit Bharat Innovation Challenge 2026 · companion to the UBHAYA concept plan

## Goal, scope and definition of done

Build an offline prototype that takes the synthetic PC-14 case, checks every claim in three statements against the evidence, and produces a reviewed report. The build is split into 7 phases and 40 chunks; each chunk has one owner and a test that proves it is done.

**In scope (must ship):**

- Intake with SHA-256 hashes, read-only originals and a hash-chained audit log.
- Parsers for the 6 demo sources: door log, PC event log, UPI records, WhatsApp export, CCTV stills, statements.
- AI claim extraction from Hindi, English and Hinglish statements.
- Time ranges, clock calibration and UTC-to-IST conversion.
- Claim verdicts (supported, contradicted, uncertain, no evidence) with a link to the exact source.
- Account board, next-best-evidence ranking with draft requests, human review, PDF/JSON report.
- An evaluation script that scores the tool against the answer key.

**Stretch (only after code freeze conditions are green):** audio transcription, captured web posts as a source, OpenTimestamps anchoring, IndicTrans2.

**Out of scope:** face recognition, suspect scoring, real case data, cloud AI services, user accounts and permissions.

**The prototype is done when:**

- [ ] The demo case runs end to end on a laptop with Wi-Fi switched off.
- [ ] Every finding opens its source row, line or frame.
- [ ] The evaluation script prints measured results against the answer key.
- [ ] The false alarm and the known failure appear and are explained.
- [ ] A recorded backup demo and setup README exist.

**Team roles used below:** BE = team lead and backend, AI = AI and extraction engineer, RE = reasoning engineer, FE = frontend developer, DT = data and testing lead, PM = product, legal and pitch lead. With five people, PM also covers DT.

## Phases at a glance

Seven phases run in order, with two checkpoints and a code freeze. Phases 3 and 4 overlap on purpose, because frontend, AI and pitch work can start before the rules engine is finished.

1. **Phase 0, Setup:** organiser rules, data pack, model choice, rule specs, offline install.
2. **Phase 1, Foundation:** demo case loads with one command; every file hashed.
3. **Phase 2, First working slice:** one claim from statement to clickable verdict. Ends at **checkpoint 1**.
4. **Phase 3, Core engine:** every source and verdict type, scored against the answer key.
5. **Phase 4, Product and trust:** account board, next evidence, review, report. Ends at **checkpoint 2**.
6. **Phase 5, Hardening:** final measured results, fallback mode, demo-path testing. Ends at **code freeze**.
7. **Phase 6, Demo and handoff:** backup video, final slides, README, rehearsals.

Each phase below lists its chunks: ID, owner, what "done" means and what it depends on. Chunk IDs (P2.3 and so on) are used for branch names and in team chat.

## Phase 0: Setup

Phase 0 settles every decision and download before building starts, so later phases are spent only on building.

**Check the rules first:** the guidelines ask teams to check the organisers' rules before bringing an existing prototype, so confirm that code built before the event is allowed (P0.1).

| ID | Chunk | Owner | Done when | Depends on |
| --- | --- | --- | --- | --- |
| P0.1 | Ask the organisers what may be prepared in advance (code, data, models) | PM | Written answer saved | None |
| P0.2 | Build the synthetic case pack and answer key (see "Demo data pack") | DT | All files exist; 18 claims labelled; planted items listed | None |
| P0.3 | Freeze data schemas and API contracts as a written spec | BE | Spec reviewed by RE and FE | None |
| P0.4 | LLM bake-off: run 2 or 3 small models on the 3 statements on team laptops | AI | Model chosen; at least 15 of 18 claims correct; under 30 seconds per statement | P0.2 |
| P0.5 | OCR bake-off on the CCTV stills and payment screenshots | AI | Engine chosen; error rate noted per image | P0.2 |
| P0.6 | Write rule specs with hand-worked examples for every planted item | RE | Each rule has a worked input, output and expected verdict | P0.2 |
| P0.7 | Wireframes for the 6 screens | FE | Paper or Figma sketches agreed by the team | P0.3 |
| P0.8 | Offline setup: pinned requirements, models pulled, setup script tested with Wi-Fi off | BE | Fresh laptop goes from zero to running in under 20 minutes | P0.4, P0.5 |

**Exit check:** every laptop has the models and packages installed, the data pack is final, and the team has agreed the Phase 1 and 2 task split.

## Phase 1: Foundation

Phase 1 ends when the demo case loads with one command and every file shows its hash. All six people work in parallel from the frozen spec.

| ID | Chunk | Owner | Done when | Depends on |
| --- | --- | --- | --- | --- |
| P1.1 | Repo scaffold: FastAPI app, SQLite models, config, test runner, README stub | BE | `make run` starts the API; one test passes | P0.3 |
| P1.2 | Intake: upload, SHA-256, read-only original store, artifact IDs, hash-chained audit log | BE | Re-hashing a file matches; editing a log entry breaks the chain check | P1.1 |
| P1.3 | Fixture loader: load the whole demo case in one command | DT | `make load-demo` creates the case with all artifacts and statements | P1.2 |
| P1.4 | Parsers for structured sources: door CSV, PC event log (UTC), UPI/bank CSV | RE | Each row becomes an Event with its source row number and original timestamp | P1.1 |
| P1.5 | Interface shell: case overview listing artifacts, types and hashes | FE | Screen shows the loaded case from the API | P1.1 |

Meanwhile, AI wraps the chosen LLM and OCR engines behind two functions, `extract_claims()` and `read_overlay_time()`, ready for Phase 2. PM drafts the checkpoint 1 demo script.

## Phase 2: First working slice

The goal of Phase 2 is one claim going all the way from statement to a clickable verdict before anything is widened. Breadth comes later.

| ID | Chunk | Owner | Done when | Depends on |
| --- | --- | --- | --- | --- |
| P2.1 | Claim extraction: statement in, validated claims out, each with its exact quote and position | AI | Manager's statement yields its claims; every quote is an exact substring | P1.3 |
| P2.2 | Time engine v1: timezone conversion and time ranges for every event | RE | PC log 16:44 UTC shows as 22:14 IST with a range; original kept | P1.4 |
| P2.3 | Claim matcher v1: match time and action claims to events; supported and no-evidence verdicts | RE | "Files copied around 22:15" is supported by the PC-14 USB and copy events | P2.1, P2.2 |
| P2.4 | Statement view and source viewer: claims highlighted in the statement; clicking one opens its evidence row | FE | Click-through works on the slice claim | P1.5, P2.3 |
| P2.5 | Evaluation script v0: compare extracted claims to the answer key and print a score | DT | Prints claims found, missed and extra | P2.1 |

**Checkpoint 1, first working slice:**

- [ ] One claim goes from statement to verdict to source row, live.
- [ ] The UTC-to-IST conversion is visible, original timestamp shown beside it.
- [ ] A first claim-extraction score from the evaluation script.
- [ ] One specific question ready for mentors (suggested: "Which next-evidence requests would you actually send first?").

If checkpoint 1 slips, cut nothing yet; move one person from FE to help RE and push the interface polish later.

## Phase 3: Core engine

Phase 3 widens the slice to every source and every verdict type, so the engine gets the whole demo case right in the terminal before the interface catches up. Never leave a chunk half-merged when handing it over.

| ID | Chunk | Owner | Done when | Depends on |
| --- | --- | --- | --- | --- |
| P3.1 | WhatsApp export parser: Hinglish messages, sender, time, line number | DT | Ravi's 22:03 "reached the dhaba" message is an Event with its line number | P1.4 |
| P3.2 | Overlay OCR for CCTV stills: time read, confidence, manual-entry fallback below a threshold | AI | CAM-A reads 22:06; blurry CAM-B still is flagged for manual entry | P0.5 |
| P3.3 | Clock calibration: apply offsets from the calibration record, widen ranges by their uncertainty | RE | CAM-B 22:05 becomes 22:12 ± 1 min; the impossible ordering disappears | P2.2, P3.2 |
| P3.4 | Contradiction rules R1 to R6 (see "Logic spec") | RE | Each rule passes its worked example from P0.6 | P3.3 |
| P3.5 | Verdict engine: four verdicts plus evidence strength (direct or indirect) | BE | All 18 claims get a verdict; each verdict lists its events and rule | P3.4 |
| P3.6 | Evaluation script v1: verdict accuracy, contradictions found, false contradictions | DT | Prints the measures from the concept plan's testing table | P3.5 |

Meanwhile FE builds the claim detail screen (evidence side by side, verdict colours) against mock API responses, and AI starts P4.2. PM writes the draft request templates for P4.4.

## Phase 4: Product and trust features

Phase 4 turns verdicts into the features the jury will remember: the account board, next-best evidence, human review and the report. It overlaps Phase 3 because FE, AI and PM are free earlier than RE.

| ID | Chunk | Owner | Done when | Depends on |
| --- | --- | --- | --- | --- |
| P4.1 | Account board: each speaker's claims grouped as supported, contradicted, open | FE | Manager's and Ravi's accounts show side by side with counts | P3.5 |
| P4.2 | AI explanations and harmless alternatives for each conflict, labelled as AI | AI | Each conflict gets 1 to 3 alternatives built only from listed events | P3.4 |
| P4.3 | Next-best-evidence ranking from the request catalogue, with score breakdown | RE | V-03 register ranks first, dhaba CCTV second, telecom records third | P3.5 |
| P4.4 | Draft request generator: fills the request template with identifiers, time window, legal section | AI | Each top-3 request has a draft citing the claim it would settle | P4.3 |
| P4.5 | Review workflow: accept, reject or edit any finding, with reason; written to audit log | BE | A rejected finding stays visible as rejected, with reviewer and reason | P3.5 |
| P4.6 | Report export: PDF and JSON with hashes, findings, decisions, limitations, Section 63 checklist | BE | Report opens; hash list matches intake | P4.5 |
| P4.7 | Timeline view: events with ranges, original and corrected times, calibration source | FE | CAM-B shows original 22:05, corrected 22:12 ± 1 min | P3.3 |

**Checkpoint 2, whole case running:**

- [ ] The whole demo case runs from intake to report.
- [ ] Measured results from evaluation script v1, including the false alarm and the failure.
- [ ] The top-3 evidence requests with drafts.
- [ ] A short list of what is still rough, to agree priorities with the mentor.

## Phase 5: Hardening and evaluation

Phase 5 adds no new features unless the demo path is fully green; every late change must fix something that would show in the demo.

| ID | Chunk | Owner | Done when | Depends on |
| --- | --- | --- | --- | --- |
| P5.1 | Apply checkpoint 2 feedback, in the agreed priority order | All | Each agreed item done or consciously dropped | Checkpoint 2 |
| P5.2 | Final evaluation run; save results as the numbers for the slides | DT | Results file saved and copied into the pitch | P3.6 |
| P5.3 | Fallback mode: cached, pre-reviewed AI outputs for the demo case, labelled as cached | AI | Demo runs with the LLM switched off | P4.2, P4.4 |
| P5.4 | Demo-path bug bash: run the pitch flow 3 times on the presenting laptop, Wi-Fi off | BE, FE | 3 clean runs in a row | P4.1 to P4.7 |
| P5.5 | Stretch features, only if P5.4 is clean | AI, RE | Merged without breaking a demo run | P5.4 |

**Code freeze:** tag the repo `final`, copy it to two laptops and a USB drive.

## Phase 6: Demo and handoff

Phase 6 ends with a rehearsed pitch, a backup video and a handoff package that runs from its README alone.

| ID | Chunk | Owner | Done when | Depends on |
| --- | --- | --- | --- | --- |
| P6.1 | Record a 5-minute backup demo video of the frozen build | FE | Video plays offline on the presenting laptop | Freeze |
| P6.2 | Final slides with measured results, the false alarm, the failure and limits | PM | Every number traces to the P5.2 results file | P5.2 |
| P6.3 | Handoff package per the organisers' instructions: code, README setup steps, data pack, report sample | BE | A teammate who did not write it runs it from the README | Freeze |
| P6.4 | Two full rehearsals with timed Q&A from the risks table in the concept plan | PM | Pitch under 5 minutes twice; every Q&A answer has an owner | P6.2 |

## Technical spec: repo, data model, API

One Python backend, one interface, and plain-file data; every module maps to one owner so merges rarely collide.

**Repo layout:**

```
ubhaya/
  backend/app/
    main.py            # FastAPI app and routes (BE)
    models.py          # Pydantic + SQLite models (BE)
    intake/            # hashing, read-only store, audit chain (BE)
    parsers/           # door, pc_log, upi, whatsapp, statements (RE, DT)
    extract/           # LLM claim extraction, OCR wrappers, prompts/ (AI)
    timeengine/        # timezone, ranges, calibration (RE)
    rules/             # R1-R6 contradiction rules, verdicts (RE, BE)
    ranking/           # request catalogue, scoring, draft requests (RE, AI)
    report/            # PDF and JSON export (BE)
  frontend/            # Streamlit or React app (FE)
  data/demo_case/      # artifacts/, statements/, calibration.json, answers.json (DT)
  eval/run_eval.py     # scores the engine against answers.json (DT)
  cache/               # pre-reviewed AI outputs for fallback mode (AI)
  scripts/setup_offline.sh
  tests/
```

**Data model:**

| Entity | Key fields | Notes |
| --- | --- | --- |
| Case | id, title, timezone (Asia/Kolkata), scope | One per demo |
| Artifact | id, sha256, type, source, acquired\_at, path | Original never written to |
| Event | id, artifact\_id, locator, actor, action, place, original\_time, original\_tz, t\_min, t\_max, confidence | `locator` = row, line, page or frame |
| Calibration | source\_id, offset\_s, uncertainty\_s, method, reference\_artifact\_id, valid\_from, valid\_to | Applied only inside its validity window |
| Statement | id, speaker, role, language, artifact\_id | Role: complainant, suspect, witness |
| Claim | id, statement\_id, quote, char\_start, char\_end, type, subject, value, t\_min, t\_max, negated | `quote` must match the statement exactly |
| Finding | id, claim\_id, verdict, strength, event\_ids, rule\_ids, explanation, ai\_generated | Verdict and rule set by code, never by the LLM |
| Alternative | id, finding\_id, text, event\_ids, ai\_generated | Shown as AI-suggested |
| EvidenceRequest | id, claim\_ids, catalogue\_id, score, score\_parts, draft\_text | `score_parts` shown in the interface |
| Review | id, target\_id, reviewer, decision, reason, time | Every review also written to the audit chain |
| AuditEntry | seq, time, actor, action, payload\_hash, prev\_hash, entry\_hash | `entry_hash` = SHA-256(prev\_hash + payload\_hash + action) |

**API:**

| Method and path | Purpose | Chunk |
| --- | --- | --- |
| POST /cases | Create a case | P1.1 |
| POST /cases/{id}/artifacts | Upload, hash and register a file | P1.2 |
| GET /artifacts/{id}/verify | Re-hash and compare | P1.2 |
| POST /cases/{id}/statements/{sid}/extract | Run claim extraction | P2.1 |
| POST /cases/{id}/analyze | Parse, align, check, rank | P3.5 |
| GET /cases/{id}/timeline | Events with ranges | P4.7 |
| GET /cases/{id}/claims | Claims with verdicts | P3.5 |
| GET /claims/{id} | One claim with evidence and source locators | P2.4 |
| GET /cases/{id}/accounts | Account board | P4.1 |
| GET /cases/{id}/requests | Ranked evidence requests with drafts | P4.3 |
| POST /reviews | Accept, reject or edit a finding | P4.5 |
| GET /cases/{id}/audit/verify | Check the hash chain | P1.2 |
| GET /cases/{id}/report.pdf and .json | Export | P4.6 |

## Logic spec: time ranges, rules, verdicts, ranking

All judging is plain Python with unit tests: every time is a range, a contradiction must hold across the whole range, and every score shows its parts.

**1. Every time is a range.** Each event and claim stores `t_min` and `t_max` in IST, plus the original value and timezone. Default widths (assumptions for the demo; RE may tune them in P0.6):

| Source | Default range |
| --- | --- |
| PC event log, door log (clock sync unknown) | ± 60 s |
| Bank and UPI records | ± 60 s |
| Chat export (minute precision) | ± 60 s |
| CCTV overlay, not calibrated | ± 10 min |
| CCTV overlay, calibrated | The calibration's own uncertainty (± 1 min in the demo) |
| Statement with an exact time ("9:50") | ± 5 min |
| Statement with "around" or "about" | ± 15 min |
| Statement with only "night" or "late" | 18:00 to 06:00 |

Calibration shifts a source's range by `offset_s` and widens it by `uncertainty_s`, only inside the calibration's validity window. Without calibration, nothing is shifted.

**2. Contradiction rules.** A rule fires as *certain* only if it holds for every time inside the ranges; if it holds for only part of the ranges, it fires as *possible*.

| Rule | Fires when | Demo example |
| --- | --- | --- |
| R1 Impossible order | A required sequence (from a small site config: entrance before corridor) is reversed | CAM-B before CAM-A, until calibration fixes it |
| R2 Time mismatch | A claim's range and the matching event's range do not overlap | Tested on "left at 9:50" vs badge OUT 21:52 (overlaps, so no fire) |
| R3 Exclusion broken | A negated or exclusive claim ("never", "only") meets an event of the excluded kind in its window | "Only person with access" vs V-03 IN at 22:06 |
| R4 Two places at once | The same actor is placed in two places closer in time than the minimum travel time in the site config | Ravi's login at PC-14 vs his UPI payment at the dhaba |
| R5 Value mismatch | An amount, account or identifier in a claim differs from the record | Screenshot or claimed amount vs bank entry |
| R6 Duplicate guard | Two events from one source with identical fields within 2 s | Counts them once (the planted false alarm is 42 s apart, so it slips past) |

**3. Verdicts.**

| Verdict | Condition |
| --- | --- |
| Contradicted | A rule fires as certain, using direct evidence |
| Uncertain | A rule fires as possible, or evidence points both ways, or a key reading is low confidence |
| Supported | At least one matching event overlaps the claim's range and no rule fires |
| No evidence | Nothing in the case relates to the claim |

Each finding also gets a strength: *direct* when the event names the person or identifier (badge, login), *indirect* when it doesn't (a phone payment, a chat message). The interface shows "supported, not proven" for indirect support.

**4. Next-best-evidence ranking.** Candidate requests come from a fixed catalogue; each is scored only for open claims where the two accounts disagree.

```latex
\text{score} = 2D + F - P + U
```

D = how differently the result would read under each account (0 to 3); F = feasibility (1 to 3); P = privacy cost (1 to 3); U = urgency from retention (2 if overwritten within 7 days, 1 within 30, else 0). Retention periods are demo assumptions, not legal facts.

| Catalogue item | Held by | D | F | P | U | Score |
| --- | --- | --- | --- | --- | --- | --- |
| Visitor card V-03 issue register | Company | 3 | 3 | 1 | 0 | 8 |
| Sharma Dhaba CCTV, 22:00 to 22:40 | Dhaba owner | 2 | 2 | 2 | 2 | 6 |
| Telecom location records, Ravi's number (BNSS Sec. 94 notice) | Telecom provider | 3 | 1 | 3 | 0 | 4 |
| PC-14 account password-change history | Company IT | 1 | 2 | 1 | 0 | 3 |
| Aman's bank statement | Bank | 1 | 1 | 3 | 0 | 0 |

## AI spec: prompts, output schema, validation

The LLM is used for three jobs, always returns JSON, and its output is checked by code before anything reaches the screen. Run it locally through Ollama with temperature 0 and JSON output mode.

| Job | Input | Output | Code check before use |
| --- | --- | --- | --- |
| Claim extraction (P2.1) | One statement's text, speaker, role, case date | Claims list (schema below) | Every `quote` is an exact substring at `char_start`; types from the allowed list; times parse |
| Harmless alternatives (P4.2) | A conflict and its events, as structured data only | 1 to 3 short explanations, each citing event IDs | Every cited event ID exists in that conflict; no new names, places, times or amounts |
| Draft request wording (P4.4) | A catalogue item, the claim IDs, identifiers, time window | Request text filling a fixed template | Identifiers and times in the text match the inputs exactly |

**Claim extraction output schema:**

```json
{
  "claims": [
    {
      "quote": "I left office at 9:50 pm",
      "char_start": 0,
      "char_end": 24,
      "type": "presence | absence | time | action | amount | identity | relationship",
      "subject": "Ravi",
      "action": "left",
      "place": "office",
      "value": null,
      "time_expr": "9:50 pm",
      "negated": false,
      "exclusive": false
    }
  ]
}
```

The model only copies `time_expr` as written ("around 10", "9:50 pm"); converting it to a range is the time engine's job, using the table in the logic spec. `exclusive` marks "only" claims for rule R3.

**Prompt rules:**

- System prompt states the schema, the allowed types, and three worked examples, including one in Hinglish.
- "Copy the claim's words exactly from the statement; do not translate, summarise or add facts."
- "Split compound sentences into one claim per fact; skip opinions and feelings."
- Keep prompts in `extract/prompts/` as versioned files, and record the prompt version on every claim.

**On failure:** if validation fails, retry once with the error message appended; if it fails again, mark the statement "needs manual claims" and let the reviewer add them. In fallback mode (P5.3), the cached reviewed output is loaded and labelled "cached".

## Demo data pack and answer key

The data pack is generated by one script, `data/make_demo_case.py`, with a fixed random seed, so anyone can rebuild it and the answer key never drifts from the data. All people, places, numbers and images are invented; images are plain rendered scenes with overlay text, no faces.

| File | Format | Records | Planted content |
| --- | --- | --- | --- |
| door\_log.csv | time, badge\_id, holder, door, direction | \~180 | Ravi OUT 21:52; V-03 IN 22:06:10 and again 22:06:52 (false alarm); V-03 OUT 22:31 |
| pc14\_events.csv | time\_utc, event\_id, user, detail | \~40 | Logon ravi.k 16:43 UTC; USB 16:44 UTC; file copies to 16:52 UTC |
| upi\_ravi.csv | time, direction, counterparty, amount, note, ref | \~15 | Sharma Dhaba ₹340 at 22:20; Aman ₹15,000 on 4 Dec, "udhaar wapas" |
| whatsapp\_ravi\_aman.txt | Standard WhatsApp export lines | \~40 | 1 Dec loan promise; 3 Dec 22:03 "dhaba pahunch gaya" (Hinglish) |
| cctv/cam\_a\_2206.png, cam\_b\_2205.png, cam\_b\_blurry.png | Image with burned-in time | 3 | CAM-B 7 min slow; blurry still is the known failure |
| calibration.json | Offset record | 1 | CAM-B +420 s ± 60 s, valid 1 to 10 Dec |
| site\_config.json | Places, required orders, travel times | 1 | Entrance before corridor; office to dhaba at least 12 min |
| statements/manager.txt, ravi.txt, guard.txt | Plain text | 3 | English, Hinglish, and Hindi in Devanagari |

**Planted items DT must include (finalise all 18 claims in P0.2):**

- 5 real contradictions, each certain under the default ranges. Candidates: "only person with access" vs V-03 IN; guard's "around 10:30" visitor vs V-03 IN at 22:06; manager's "paid that same night" vs payment on 4 Dec; Ravi's "reached the dhaba at 9:55" vs his 22:03 chat; one more chosen by DT.
- 2 harmless-looking conflicts: CAM-B before CAM-A (fixed by calibration) and the PC log in UTC (fixed by conversion).
- 1 false alarm: V-03 appears to enter twice, 42 s apart; the tool flags it and the reviewer rejects it on screen.
- 1 known failure: the blurry CAM-B still, which OCR misreads and should flag as low confidence.

**answers.json shape:**

```json
{
  "claims": [
    {"id": "M1", "statement": "manager", "quote": "he was the only person with access",
     "expected_verdict": "contradicted", "expected_rule": "R3", "evidence": ["door_log.csv#row142"]}
  ],
  "planted": {
    "harmless_conflicts": ["CAM-B order", "PC log UTC"],
    "false_alarm": "door_log.csv#row143",
    "known_failure": "cctv/cam_b_blurry.png"
  },
  "expected_requests_top3": ["visitor_register", "dhaba_cctv", "telecom_location"]
}
```

## Screens

Six screens cover the whole pitch flow; build them in this order, because each one is usable on its own.

| # | Screen | Shows | Key interactions | Chunk |
| --- | --- | --- | --- | --- |
| 1 | Case overview | Artifacts with type, hash, verify status; synthetic-data badge | Verify hash; open artifact | P1.5 |
| 2 | Statement view | Statement text with each claim highlighted in its verdict colour | Click a claim to open it | P2.4 |
| 3 | Claim detail | Claim quote, verdict, strength, rule; evidence rows beside the original source line, row or frame; AI alternatives labelled | Accept, reject or edit with a reason | P2.4, P4.5 |
| 4 | Timeline | Events as ranges; original and corrected times; calibration source | Toggle calibration on and off to show the conflict appear and vanish | P4.7 |
| 5 | Account board | Each speaker's claims grouped supported, contradicted, open | Click through to claim detail | P4.1 |
| 6 | Next evidence and report | Ranked requests with score parts, draft text; report export | Edit a draft; export PDF and JSON | P4.3, P4.4, P4.6 |

Colours: green supported, red contradicted, grey uncertain or no evidence; anything AI-written carries an "AI" tag. Screen 4's calibration toggle is the best live moment of the demo.

## Priorities, cut order and fallbacks

If time runs short, cut from the bottom of this list up; never cut anything marked Must, because those carry the pitch.

| Priority | Features |
| --- | --- |
| Must | Intake and hashes; claim extraction; time ranges and calibration; verdicts with source links; account board; top-3 requests; review; evaluation script |
| Should | Draft request text; PDF report; timeline screen with calibration toggle; AI alternatives |
| Could | JSON report; audit chain verify screen; WhatsApp media references; polished styling |
| Stretch | Audio transcription; captured web posts; OpenTimestamps; IndicTrans2 |

**Cut order when behind:** stretch features, then polished styling, then the audit verify screen, then the timeline screen (show the calibration effect on claim detail instead), then the PDF (keep JSON plus a printed screen).

**Fallbacks:**

| If this fails | Do this |
| --- | --- |
| LLM too slow or unreliable on the day | Fallback mode with cached, reviewed outputs, labelled "cached" |
| OCR misreads the good stills | Manual time entry, recorded as manual in the audit log |
| React interface not ready by checkpoint 2 | Switch the remaining screens to Streamlit over the same API |
| Presenting laptop fails | Second laptop with the tagged build; then the backup video |
| A rule gives a wrong verdict late | Show it honestly as a measured miss; do not patch the answer key |

## Team working rules

The main branch must always run the demo; everything else follows from that.

- **Branches:** one short-lived branch per chunk, named by its ID (`p3.4-rules`). Merge only when the chunk's "done when" passes and `make test` is green.
- **Tags:** `demo-g1` at checkpoint 1, `demo-g2` at checkpoint 2, `final` at code freeze. Any tag can be demoed if a later build breaks.
- **Syncs:** 10 minutes at every phase boundary: what merged, what is blocked, who moves where.
- **Contracts first:** a change to a schema or API path needs a message to everyone it affects before merging.
- **Shifts:** overnight, at least two people awake, never both from the same chunk; hand over with a 3-line note (done, in progress, next).
- **Tracking:** the chunk tables in this doc are the task list; mark the ID in the team chat when you start and finish a chunk.
- **Data rules:** synthetic data only, no real names or numbers in code, commits or screenshots; no cloud AI services at any point.
- **Credits:** add every library, model and dataset to the references list as it is installed, not at the end.

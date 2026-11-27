# UBHAYA frozen spec (P0.3)

Status: **frozen v1**. Changing anything in this file needs a message to everyone it affects before merging (team rule "contracts first").

## Conventions

- All IDs are strings with a type prefix and a zero-padded counter: `C001` case, `A001` artifact, `E0001` event, `S001` statement, `CL001` claim, `F001` finding, `AL001` alternative, `R001` evidence request, `RV001` review.
- All stored times are ISO 8601 strings with an explicit offset. Ranges (`t_min`, `t_max`) are always IST (`+05:30`).
- The original value of every time is kept as written in the source (`original_time`) with its zone (`original_tz`).
- A **locator** points into an artifact: `row 12` (1-based data row, header excluded), `line 7` (1-based line), `page 2`, `frame 1`, `chars 120-164`. A full source reference is `<artifact filename>#row12`, which is the format used in `answers.json`.
- Hashes are lowercase hex SHA-256.

## Entities

| Entity | Fields | Notes |
| --- | --- | --- |
| Case | `id, title, timezone, scope, created_at, synthetic` | `timezone` is `Asia/Kolkata`; `synthetic` true for the demo |
| Artifact | `id, case_id, filename, sha256, size, type, source, acquired_at, path, meta` | `path` is the read-only stored copy; originals are never written to |
| Event | `id, case_id, artifact_id, locator, actor, action, place, original_time, original_tz, t_min, t_max, confidence, fields, raw` | `fields` keeps typed source columns (amount, badge_id...); `raw` is the source line verbatim |
| Calibration | `source_id, offset_s, uncertainty_s, method, reference_artifact, valid_from, valid_to` | Applied only inside its validity window |
| Statement | `id, case_id, artifact_id, speaker, role, language, text` | `role`: complainant, suspect, witness; `language`: en, hi-Latn (Hinglish), hi |
| Claim | `id, statement_id, quote, char_start, char_end, type, subject, action, place, value, time_expr, t_min, t_max, negated, exclusive, prompt_version, source` | `quote == statement.text[char_start:char_end]` always; `source` = llm, cached, manual |
| Finding | `id, claim_id, verdict, strength, event_ids, rule_ids, certainty, explanation, ai_generated` | Verdict and rule set by code, never by the LLM |
| Alternative | `id, finding_id, text, event_ids, ai_generated` | Shown with an "AI" tag |
| EvidenceRequest | `id, case_id, claim_ids, catalogue_id, score, score_parts, draft_text` | `score_parts` = `{D, F, P, U}` |
| Review | `id, target_id, reviewer, decision, reason, edit, time` | `decision`: accept, reject, edit. Also written to the audit chain |
| AuditEntry | `case_id, seq, time, actor, action, payload, payload_hash, prev_hash, entry_hash` | see below |

**Artifact types:** `door_log`, `pc_event_log`, `bank_upi`, `chat_export`, `cctv_still`, `statement`, `calibration`, `site_config`.

**Event actions** (closed list, extend only via this file): `badge_in`, `badge_out`, `logon`, `logoff`, `usb_connected`, `usb_removed`, `file_copy`, `file_access`, `upi_debit`, `upi_credit`, `chat_message`, `camera_sighting`.

**Claim types** (from the AI spec): `presence`, `absence`, `time`, `action`, `amount`, `identity`, `relationship`.

**Verdicts:** `supported`, `contradicted`, `uncertain`, `no_evidence`. **Strength:** `direct`, `indirect`. **Rule certainty:** `certain`, `possible`.

## Audit hash chain

One chain per case. For entry `seq` (1-based):

```
payload_hash = SHA-256( canonical_json({seq, time, actor, action, payload}) )
entry_hash   = SHA-256( prev_hash + payload_hash + action )
prev_hash    = entry_hash of seq-1, or 64 zeros for seq 1
```

`canonical_json` = `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` encoded as UTF-8. Hashing every field (not only the payload) means editing the time or actor of an entry also breaks the chain. Verification recomputes both hashes for every entry and reports the first broken `seq`.

Audit actions: `case_created`, `artifact_registered`, `artifact_verified`, `statement_registered`, `events_parsed`, `claims_extracted`, `analysis_run`, `review_recorded`, `report_exported`, `manual_time_entry`.

## Evidence store

- Path: `<UBHAYA_DATA_DIR>/store/<sha256[0:2]>/<sha256>` (content-addressed; the same file uploaded twice is stored once).
- Written once, then made read-only (`chmod 0o444`). The original uploaded filename lives only in the database.
- `GET /artifacts/{id}/verify` re-hashes the stored file and compares with the hash taken at intake.

## API (v1)

All bodies JSON unless stated. Errors use FastAPI's `{"detail": ...}`.

| Method and path | Body / params | Returns | Chunk |
| --- | --- | --- | --- |
| GET /health | | `{"status":"ok"}` | P1.1 |
| POST /cases | `{title, scope?, synthetic?}` | Case | P1.1 |
| GET /cases | | Case[] | P1.1 |
| GET /cases/{id} | | Case with `artifact_count`, `statement_count`, `event_count` | P1.5 |
| POST /cases/{id}/artifacts | multipart: `file`, `type`, `source`, `acquired_at?`, `meta?` (JSON string) | Artifact | P1.2 |
| GET /cases/{id}/artifacts | | Artifact[] | P1.5 |
| GET /artifacts/{id} | | Artifact | P1.2 |
| GET /artifacts/{id}/content | | the stored file bytes | P2.4 |
| GET /artifacts/{id}/verify | | `{artifact_id, expected, actual, ok}` | P1.2 |
| GET /cases/{id}/statements | | Statement[] | P1.3 |
| GET /cases/{id}/events | `?artifact_id=` | Event[] | P1.4 |
| GET /cases/{id}/audit | | AuditEntry[] | P1.2 |
| GET /cases/{id}/audit/verify | | `{ok, entries, broken_at}` | P1.2 |
| POST /cases/{id}/statements/{sid}/extract | | Claim[] | P2.1 |
| POST /cases/{id}/analyze | | `{events, claims, findings}` counts | P3.5 |
| GET /cases/{id}/timeline | `?calibrated=true` | Event[] with ranges | P4.7 |
| GET /cases/{id}/claims | | Claim[] with Finding | P3.5 |
| GET /claims/{id} | | Claim with Finding, Events, locators | P2.4 |
| GET /cases/{id}/accounts | | `{speaker: {supported:[], contradicted:[], open:[]}}` | P4.1 |
| GET /cases/{id}/requests | | EvidenceRequest[] ranked | P4.3 |
| POST /reviews | `{target_id, reviewer, decision, reason, edit?}` | Review | P4.5 |
| GET /cases/{id}/report.json, /report.pdf | | report | P4.6 |

## Demo data pack layout

```
data/demo_case/
  artifacts/door_log.csv          type door_log
  artifacts/pc14_events.csv       type pc_event_log
  artifacts/upi_ravi.csv          type bank_upi
  artifacts/whatsapp_ravi_aman.txt type chat_export
  artifacts/cctv/*.png            type cctv_still
  statements/manager.txt, ravi.txt, guard.txt   type statement
  statements/statements.json      speaker, role, language per statement file
  calibration.json                type calibration
  site_config.json                type site_config
  answers.json                    ANSWER KEY - never loaded as evidence
```

`answers.json` is only read by `eval/run_eval.py`.

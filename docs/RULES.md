# Rule specs with worked examples (P0.6)

Every example below uses the real rows of the generated demo pack (`data/make_demo_case.py`, seed 1403). Each one becomes a unit test in P3.4. All times are IST unless marked `Z` (UTC). "OUT", "IN" are door-log directions.

## 1. Time ranges

| Source | Range rule | Worked example |
| --- | --- | --- |
| Door log, PC log (clock sync unknown) | value ± 60 s | Ravi OUT `21:52:07` → [21:51:07, 21:53:07] |
| PC log is UTC | convert first (+05:30), then ± 60 s | `16:43:21Z` → 22:13:21 → [22:12:21, 22:14:21] |
| Bank / UPI | ± 60 s | Sharma Dhaba `22:20:31` → [22:19:31, 22:21:31] |
| Chat export (minute precision) | `HH:MM:00` ± 60 s | `22:07` → [22:06:00, 22:08:00] |
| CCTV overlay, uncalibrated | ± 10 min | CAM-B `22:05:40` → [21:55:40, 22:15:40] |
| CCTV overlay, calibrated | shift by `offset_s`, ± `uncertainty_s` | CAM-B `22:05:40` + 420 s → 22:12:40 → [22:11:40, 22:13:40] |
| Statement, exact time | ± 5 min | "9:50" → [21:45, 21:55] |
| Statement, "around / about / kareeb / करीब" | ± 15 min | "about 10:10 pm" → [21:55, 22:25] |
| Statement, "night / raat / that night" only | 18:00 case date → 06:00 next day | "that same night" → [3 Dec 18:00, 4 Dec 06:00] |
| Statement, "after X" | X → 06:00 next day | "दस बजे के बाद" (after ten) → [22:00, 06:00] |
| Statement, a date only | 00:00 → 23:59:59 that day | "4 December" → [4 Dec 00:00, 4 Dec 23:59:59] |
| Statement, no time | whole case window | "Aman transferred him Rs 20,000" → [1 Dec, 10 Dec] |

**Clock-hour resolution.** A statement time without am/pm ("9:50", "10:30") is resolved to the reading nearest the incident window (evening of the case date), so "9:50" = 21:50.

**Calibration** applies only if the event's original time is inside `valid_from`..`valid_to`. CAM-A: 0 s ± 60 s. CAM-B: +420 s ± 60 s. Both valid 1 to 10 Dec.

## 2. Certain vs possible

For two ranges A = [a0, a1] and B = [b0, b1]:

- "A is before B for sure": `a1 < b0`. "Maybe": `a0 < b1`.
- Overlap: `a0 <= b1 and b0 <= a1`.
- Smallest gap: `max(0, b0 - a1, a0 - b1)`. Largest gap: `max(a1 - b0, b1 - a0)`.

A rule is **certain** when its condition holds for every pair of times inside the ranges, **possible** when it holds for some but not all.

**Same-source exception:** two events from the same artifact share one clock, so their relative order and spacing are taken from the original times, not from the ranges.

## 3. Rules

### R1 Impossible order
Fires when a required order from `site_config.required_orders` is reversed.
- *certain*: `then.t_max < first.t_min`; *possible*: `then.t_min < first.t_max` (and not certain).

| Example | Input | Output |
| --- | --- | --- |
| CAM order, calibration OFF | CAM-A [21:56:20, 22:16:20], CAM-B [21:55:40, 22:15:40] | **R1 possible** → finding "uncertain" |
| CAM order, calibration ON | CAM-A [22:05:20, 22:07:20], CAM-B [22:11:40, 22:13:40] | no fire (CAM-B.t_min > CAM-A.t_max) |
| Badge alternation (false alarm) | V-03 IN row 185 `22:06:10`, V-03 IN row 186 `22:06:52`, no OUT between (same source) | **R1 certain** → flagged; reviewer rejects as a double tap |

### R2 Time mismatch
Fires when a claim's range and the matching event's range do not overlap. Always *certain* when it fires (no overlap at all); *possible* is not used.

| Claim | Claim range | Event | Event range | Output |
| --- | --- | --- | --- | --- |
| R1 "Main 9:50 pe office se nikal gaya tha" | [21:45, 21:55] | OUT row 184 | [21:51:07, 21:53:07] | overlap → no fire → **supported** |
| G2 "करीब 10:30 बजे एक विज़िटर आया" | [22:15, 22:45] | V-03 IN row 185 | [22:05:10, 22:07:10] | **R2 certain** → contradicted |
| M5 "His friend Aman paid him that same night" | [3 Dec 18:00, 4 Dec 06:00] | UPI CR Aman row 12 `4 Dec 11:42:05` | [11:41:05, 11:43:05] 4 Dec | **R2 certain** → contradicted |
| R2 "9:55 tak main Sharma Dhaba pahunch gaya tha" | [21:50, 22:00] | chat line 22 `22:07` "dhaba pahunch gaya" | [22:06, 22:08] | **R2 certain** (supporting rule; chat is indirect) |

### R3 Exclusion broken
A claim with `negated` or `exclusive` meets an event of the excluded kind inside its window.
- *certain*: event range fully inside the claim window; *possible*: partly inside.

| Claim | Excluded kind | Event | Output |
| --- | --- | --- | --- |
| M1 "Ravi was the only person with access to PC-14 that night" (exclusive) | someone other than Ravi entering the office, 18:00 to 06:00 | V-03 IN row 185 [22:05:10, 22:07:10] | **R3 certain** → contradicted |
| R3 "Maine us raat PC-14 pe login nahi kiya" (negated) | logon by one of Ravi's accounts on PC-14 | logon ravi.k row 21 [22:12:21, 22:14:21] | **R3 certain**, but see R4 → uncertain |
| G5 "दस बजे के बाद कोई और कर्मचारी ऑफिस नहीं आया" (negated) | employee badge IN, [22:00, 06:00] | none (only V-03, a visitor card) | no fire; door log covers the window → **supported** |

### R4 Two places at once
The same actor is placed in two places closer in time than `min_travel_s` (office ↔ dhaba ≥ 720 s).
- *certain*: largest gap < travel; *possible*: smallest gap < travel ≤ largest gap.

Place inference: door, PC and camera events → `office`; UPI with merchant "Sharma Dhaba" → `dhaba`; chat text containing "dhaba" → `dhaba`. Actor links come from `site_config.actors` (ravi.k, E-1047, upi_ravi.csv, chat name "Ravi Kumar" are all Ravi).

| Pair | Ranges | Smallest / largest gap | Output |
| --- | --- | --- | --- |
| logon ravi.k (office) vs UPI Sharma Dhaba (dhaba) | [22:12:21, 22:14:21] vs [22:19:31, 22:21:31] | 5:10 / 9:10 | **R4 certain** (the central open question) |
| chat "dhaba pahunch gaya" (dhaba) vs logon ravi.k (office) | [22:06:00, 22:08:00] vs [22:12:21, 22:14:21] | 4:21 / 8:21 | **R4 certain** |
| OUT row 184 (office) vs chat "dhaba pahunch gaya" (dhaba) | [21:51:07, 21:53:07] vs [22:06:00, 22:08:00] | 12:53 / 16:53 | no fire (Ravi's real trip is consistent) |
| Claim R2 "9:55 at the dhaba" vs OUT row 184 (office) | [21:50, 22:00] vs [21:51:07, 21:53:07] | 0 / 8:53 | **R4 certain** with direct badge evidence → contradicted |

### R5 Value mismatch
An amount, account or identifier in a claim differs from the matched record. Always *certain*.

| Claim | Record | Output |
| --- | --- | --- |
| M6 "Aman transferred him Rs 20,000" | UPI row 12 CR Aman Verma 15000 | **R5 certain** → contradicted |
| R5 "Aman ne 4 December ko mere 15,000 rupaye wapas kiye the" | UPI row 12 CR 15000 on 4 Dec | no fire → supported |
| R4 "Dhaba pe maine 340 rupaye UPI se pay kiye" | UPI row 11 DR Sharma Dhaba 340 | no fire → supported |

### R6 Duplicate guard
Two events from one source with identical `actor, action, place` and original times within `duplicate_window_s` (2 s) count as one. Runs before R1 to R5.

| Pair | Gap | Output |
| --- | --- | --- |
| V-03 IN row 185 and row 186 | 42 s | not merged → R1 badge alternation fires (the planted false alarm) |

## 4. Verdicts and strength

Order of evaluation: R6 → match events to the claim → R1 to R5 → verdict.

| Verdict | Condition |
| --- | --- |
| contradicted | a rule fires *certain* on **direct** evidence and no certain conflict points the other way |
| uncertain | a rule fires *possible*; or a certain rule fires only on indirect evidence; or a certain R4 conflict involves the claim's own evidence (evidence points both ways); or a key reading is low confidence |
| supported | at least one matching event overlaps the claim range and no rule fires |
| no_evidence | nothing in the case relates to the claim |

**Strength depends on what the claim is about:**

- *Direct*: the record is itself the thing claimed. A personal badge for a person entering or leaving; a login for an *account* being used; a bank entry for a *payment* (time, amount, counterparty).
- *Indirect*: the record is a proxy. A login as proof of *who sat at the keyboard*; a UPI payment or chat message as proof of *where a person was*.
- Indirect support is shown as **"supported, not proven"**.

Worked verdicts for the two open claims:

- **M4 "Ravi copied the files himself"**: login ravi.k supports it (indirect for a person); UPI at the dhaba 22:20 and chat 22:07 conflict with it via R4 certain (indirect). Evidence both ways → **uncertain**.
- **R3 "Maine us raat PC-14 pe login nahi kiya"**: R3 certain on logon ravi.k, but the logon is indirect for a person and R4 says Ravi's phone was at the dhaba → **uncertain**.

## 5. Expected results for all 18 claims

| ID | Expected verdict | Rule(s) | Strength | Evidence |
| --- | --- | --- | --- | --- |
| M1 | contradicted | R3 | direct | door_log.csv#row185 |
| M2 | supported | | direct | pc14_events.csv#row22, #row23 to #row31 |
| M3 | supported | | direct | pc14_events.csv#row21 |
| M4 | uncertain | R4 | | pc14 #row21, upi #row11, whatsapp #line22 |
| M5 | contradicted | R2 | direct | upi_ravi.csv#row12 |
| M6 | contradicted | R5 | direct | upi_ravi.csv#row12 |
| M7 | no_evidence | | | |
| R1 | supported | | direct | door_log.csv#row184 |
| R2 | contradicted | R4, R2 | direct | door_log.csv#row184, whatsapp #line22 |
| R3 | uncertain | R3, R4 | | pc14 #row21, upi #row11 |
| R4 | supported | | indirect | upi_ravi.csv#row11 |
| R5 | supported | | direct | upi_ravi.csv#row12, whatsapp #line30 |
| R6 | no_evidence | | | |
| G1 | supported | | direct | door_log.csv#row184 |
| G2 | contradicted | R2 | direct | door_log.csv#row185 |
| G3 | supported | | direct | door_log.csv#row185 |
| G4 | no_evidence | | | |
| G5 | supported | | direct | door_log.csv (no employee IN after 22:00) |

Totals: 8 supported, 5 contradicted, 2 uncertain, 3 no evidence. `answers.json` is the machine-readable copy; if this table and `answers.json` disagree, regenerate the pack and fix this table, never the other way round.

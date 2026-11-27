"""P0.2 pack integrity and P1.3 one-command loader."""
import json
from collections import Counter

from app.db import connect
from app.intake import audit, service
from conftest import DEMO


def answers():
    return json.loads((DEMO / "answers.json").read_text(encoding="utf-8"))


def test_answer_key_quotes_are_exact_substrings():
    meta = json.loads((DEMO / "statements" / "statements.json").read_text(encoding="utf-8"))["statements"]
    texts = {m["file"].removesuffix(".txt"): (DEMO / "statements" / m["file"]).read_text(encoding="utf-8") for m in meta}
    claims = answers()["claims"]
    assert len(claims) == 18
    for c in claims:
        assert texts[c["statement"]][c["char_start"]:c["char_end"]] == c["quote"], c["id"]


def test_answer_key_totals_match_plan():
    a = answers()
    verdicts = Counter(c["expected_verdict"] for c in a["claims"])
    assert verdicts == {"supported": 8, "contradicted": 5, "uncertain": 2, "no_evidence": 3}
    assert sorted(a["planted"]["real_contradictions"]) == sorted(c["id"] for c in a["claims"] if c["expected_verdict"] == "contradicted")
    assert a["planted"]["false_alarm"] == "door_log.csv#row186"
    assert a["planted"]["known_failure"] == "cctv/cam_b_blurry.png"


def test_evidence_refs_point_at_planted_rows():
    a = answers()
    door = (DEMO / "artifacts" / "door_log.csv").read_text(encoding="utf-8").splitlines()
    assert door[185].endswith("V-03,VISITOR CARD,MAIN-ENTRANCE,IN")  # row 185 = line index 185 (header is 0)
    assert door[185].startswith("2025-12-03 22:06:10")
    chat = (DEMO / "artifacts" / "whatsapp_ravi_aman.txt").read_text(encoding="utf-8").splitlines()
    line = int(a["refs"]["dhaba_chat"].split("#line")[1])
    assert chat[line - 1] == "03/12/2025, 22:07 - Ravi Kumar: dhaba pahunch gaya, khana order kar raha hu"


def test_load_demo_in_one_call(demo_case):
    assert demo_case["statements"] == 3
    assert demo_case["artifacts"] == 12
    assert demo_case["events"] == 187 + 33 + 16
    case = demo_case["case"]
    assert case["synthetic"] is True
    with connect() as conn:
        arts = service.list_artifacts(conn, case["id"])
        names = {a["filename"] for a in arts}
        assert "answers.json" not in names and "door_log.csv" in names and "cctv/cam_b_blurry.png" in names
        assert all(service.verify_artifact(conn, a["id"])["ok"] for a in arts)
        assert audit.verify(conn, case["id"])["ok"]
        calib = conn.execute("SELECT source_id, offset_s, uncertainty_s FROM calibrations WHERE case_id = ?", (case["id"],)).fetchall()
        assert sorted(tuple(r) for r in calib) == [("CAM-A", 0, 60), ("CAM-B", 420, 60)]


def test_demo_statement_text_survives_round_trip(demo_case, client):
    cid = demo_case["case"]["id"]
    stmts = client.get(f"/cases/{cid}/statements").json()
    guard = next(s for s in stmts if s["role"] == "witness")
    assert guard["language"] == "hi" and "विज़िटर कार्ड V-03" in guard["text"]
    events = client.get(f"/cases/{cid}/events").json()
    assert len(events) == 236

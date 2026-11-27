"""Checkpoint flows through the public API with local inference switched off."""
from app.db import connect
from app.intake.audit import verify


def test_analysis_review_and_report(client, demo_case, monkeypatch):
    monkeypatch.setenv("UBHAYA_EXTRACT_MODE","cached")
    cid = demo_case["case"]["id"]
    base = "/cases/"+cid
    counts = client.post(base+"/analyze")
    assert counts.status_code == 200, counts.text
    assert counts.json() == {"claims":18,"events":276,"findings":18}
    claims = client.get(base+"/claims").json()
    copy = next(c for c in claims if c["action"]=="file_copy")
    assert copy["finding"]["verdict"] == "supported"
    evidence = client.get("/claims/"+copy["id"]).json()["events"]
    assert {e["locator"] for e in evidence} == {f"row {n}" for n in range(22,32)}
    assert client.post(base+"/analyze").json() == counts.json()
    assert client.get(base+"/claims").json() == claims
    before = client.get(base+"/observations?calibrated=false").json()
    after = client.get(base+"/observations").json()
    assert any(a["certainty"]=="possible" for a in before)
    assert not any(a["certainty"]=="possible" for a in after)
    double = next(a for a in after if "42 seconds" in a["explanation"])
    review = client.post("/reviews",json={"reviewer":"Demo reviewer","reason":"Possible double tap",
                                          "target_id":double["id"],"decision":"reject"})
    assert review.status_code == 200, review.text
    report = client.get(base+"/report.json").json()
    assert [r["id"] for r in report["reviews"]] == [review.json()["id"]]
    assert len(report["manual_time_required"]) == 1
    aid = report["manual_time_required"][0]
    r = client.post(f"/artifacts/{aid}/manual-time",params={"timestamp":"2025-12-03T22:24:05","reviewer":"Demo"})
    assert r.status_code == 200
    assert client.get(base+"/report.json").json()["manual_time_required"] == []
    assert [r["catalogue_id"] for r in report["requests"][:3]] == ["visitor_register","dhaba_cctv","telecom_location"]
    with connect() as conn:
        assert verify(conn,cid)["ok"]


def test_chat_and_overlay_keep_source_locators(demo_case,client):
    base="/cases/"+demo_case["case"]["id"]
    timeline=client.get(base+"/timeline").json()
    arrival=next(e for e in timeline if "dhaba pahunch" in (e["raw"] or ""))
    assert arrival["locator"]=="line 22"
    assert arrival["original_time"]=="03/12/2025, 22:07"
    cam=next(e for e in timeline if e["fields"].get("camera")=="CAM-B")
    assert cam["t_min"]=="2025-12-03T22:11:40+05:30"
    assert cam["t_max"]=="2025-12-03T22:13:40+05:30"


def test_operator_identity_rationale(demo_case, client):
    base = "/cases/" + demo_case["case"]["id"]
    assert client.post(base + "/analyze").status_code == 200
    claims = client.get(base + "/claims").json()
    claim = next(c for c in claims if c["action"] == "personal_copy")
    detail = client.get("/claims/" + claim["id"]).json()
    assert detail["finding"]["verdict"] == "uncertain"
    assert "ravi.k" in detail["rationale"]["summary"]
    assert "physically operating" in detail["rationale"]["unresolved"]
    assert [r["id"] for r in detail["rationale"]["rules"]] == detail["finding"]["rule_ids"]
    linked = [r for r in client.get(base + "/requests").json() if claim["id"] in r["claim_ids"]]
    assert linked[0]["catalogue_id"] == "dhaba_cctv"


def test_payment_alone_cannot_support_operator_identity():
    from app.rules import match

    config = {"case_date": "2025-12-03", "actors": {"Ravi Kumar": {"accounts": ["ravi.k"]}},
              "places": {"dhaba": {"merchants": ["Sharma Dhaba"]}}}
    payment = {"id": "E1", "action": "upi_debit", "actor": "Ravi Kumar",
               "fields": {"counterparty": "Sharma Dhaba"}, "t_min": "2025-12-03T22:19:31+05:30",
               "t_max": "2025-12-03T22:21:31+05:30"}
    claim = {"action": "personal_copy", "quote": "Ravi copied the files himself", "t_min": None}
    result = match(claim, [payment], config)
    assert (result["verdict"], result["strength"], result["event_ids"]) == ("no_evidence", None, [])

"""Case analysis, traceable findings and review records."""
import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from . import models
from .db import connect, encode, fetch_all, fetch_one, insert, next_id
from .extract import extract_statement
from .intake import audit, service
from .parsers import PARSERS, list_events, parse_artifact
from .ranking import rank_requests
from .report import CHECKLIST, LEGAL_SOURCE, render_pdf
from .rules import explain_finding, match
from .timeengine.claims import claim_window

router = APIRouter()


def require_case(conn, cid):
    try:
        return service.get_case(conn, cid)
    except service.NotFound as exc:
        raise HTTPException(404, str(exc))


def findings(conn, cid):
    rows = fetch_all(conn, "SELECT c.* FROM claims c JOIN statements s ON s.id=c.statement_id WHERE s.case_id=? ORDER BY s.id,c.char_start", (cid,))
    for row in rows:
        row["finding"] = fetch_one(conn, "SELECT * FROM findings WHERE claim_id=?", (row["id"],))
    return rows


@router.post("/cases/{cid}/analyze")
def analyze(cid: str):
    with connect() as conn:
        require_case(conn, cid)
        artifacts = service.list_artifacts(conn, cid)
        config = next((a for a in artifacts if a["type"] == "site_config"), None)
        if config is None:
            raise HTTPException(422, "Analysis requires the PC-14 site configuration")
        settings = json.loads(Path(config["path"]).read_text(encoding="utf-8"))
        statements = fetch_all(conn, "SELECT id FROM statements WHERE case_id=?", (cid,))
    for statement in statements:
        with connect() as conn:
            try:
                extract_statement(conn, cid, statement["id"])
            except ConnectionError as exc:
                raise HTTPException(503, str(exc))
            except ValueError as exc:
                raise HTTPException(422, str(exc))
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        for a in service.list_artifacts(conn, cid):
            if a["type"] in PARSERS and not conn.execute("SELECT 1 FROM events WHERE artifact_id=? LIMIT 1", (a["id"],)).fetchone():
                parse_artifact(conn, a)
        events = list_events(conn, cid)
        claims = findings(conn, cid)
        if events:
            case_window = (min(datetime.fromisoformat(e["t_min"]) for e in events),
                           max(datetime.fromisoformat(e["t_max"]) for e in events))
        for claim in claims:
            if events:
                try:
                    low, high = claim_window(claim["quote"], settings["case_date"], case_window)
                except ValueError as exc:
                    raise HTTPException(422, f"Cannot resolve time for {claim['id']}: {exc}") from exc
                claim["t_min"], claim["t_max"] = low.isoformat(), high.isoformat()
                conn.execute("UPDATE claims SET t_min=?,t_max=? WHERE id=?", (claim["t_min"], claim["t_max"], claim["id"]))
            result = match(claim, events, settings)
            if claim["finding"]:
                assignments = ", ".join(f"{key}=?" for key in result)
                conn.execute(f"UPDATE findings SET {assignments} WHERE claim_id=?",
                             [encode(value, key) for key, value in result.items()] + [claim["id"]])
            else:
                insert(conn, "findings", dict(id=next_id(conn, "F"), claim_id=claim["id"], **result))
        counts = dict(events=len(events), claims=len(claims), findings=len(claims))
        audit.append(conn, cid, "api", "analysis_run", counts)
        return counts


@router.get("/cases/{cid}/claims")
def case_claims(cid: str):
    with connect() as conn:
        require_case(conn, cid)
        return findings(conn, cid)


@router.get("/claims/{claim_id}")
def detail(claim_id: str):
    with connect() as conn:
        claim = fetch_one(conn, "SELECT * FROM claims WHERE id=?", (claim_id,))
        if not claim:
            raise HTTPException(404, "Unknown claim")
        finding = fetch_one(conn, "SELECT * FROM findings WHERE claim_id=?", (claim_id,))
        events = [fetch_one(conn, "SELECT * FROM events WHERE id=?", (eid,)) for eid in finding["event_ids"]] if finding else []
        alternatives = fetch_all(conn, "SELECT * FROM alternatives WHERE finding_id=?", (finding["id"],)) if finding else []
        reviews = fetch_all(conn, "SELECT * FROM reviews WHERE target_id=? ORDER BY id", (finding["id"],)) if finding else []
        return dict(claim=claim, finding=finding, events=events, alternatives=alternatives, reviews=reviews,
                    rationale=explain_finding(claim, finding, events) if finding else None)


@router.post("/reviews", response_model=models.Review)
def review(body: models.ReviewCreate):
    if not body.reason.strip() or not body.reviewer.strip() or (body.decision == "edit" and not body.edit):
        raise HTTPException(422, "Provide reviewer, reason and any requested edit")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        target = fetch_one(conn, "SELECT s.case_id FROM statements s JOIN claims c ON s.id=c.statement_id JOIN findings f ON f.claim_id=c.id WHERE f.id=?", (body.target_id,))
        if not target and body.target_id.startswith("O-"):
            target = fetch_one(conn, "SELECT case_id FROM events WHERE id=?", (body.target_id[2:],))
            if target and not any(a["id"] == body.target_id for a in observations(target["case_id"], False)):
                target = None
        if not target:
            raise HTTPException(404, "Unknown review target")
        row = dict(body.model_dump(), id=next_id(conn, "RV"), time=audit.now_ist())
        insert(conn, "reviews", row)
        audit.append(conn, target["case_id"], body.reviewer, "review_recorded", row)
        return row


@router.get("/cases/{cid}/accounts")
def accounts(cid: str):
    with connect() as conn:
        require_case(conn, cid)
        statements = fetch_all(conn, "SELECT * FROM statements WHERE case_id=?", (cid,))
        result = {s["speaker"]: dict(supported=[], contradicted=[], open=[]) for s in statements}
        by_id = {s["id"]: s["speaker"] for s in statements}
        for c in findings(conn, cid):
            verdict = (c["finding"] or {}).get("verdict")
            result[by_id[c["statement_id"]]][verdict if verdict in ("supported", "contradicted") else "open"].append(c)
        return result


@router.get("/cases/{cid}/timeline")
def timeline(cid: str, calibrated: bool = True):
    from datetime import datetime, timedelta
    from .config import IST

    with connect() as conn:
        require_case(conn, cid)
        events = list_events(conn, cid)
        records = fetch_all(conn, "SELECT * FROM calibrations WHERE case_id=?", (cid,))
        for e in events:
            if e["action"] != "camera_sighting" or not calibrated:
                continue
            low, high = map(datetime.fromisoformat, (e["t_min"], e["t_max"]))
            center = low + (high - low) / 2
            for rec in records:
                if rec["source_id"] == e["fields"].get("camera") and datetime.fromisoformat(rec["valid_from"]) <= center <= datetime.fromisoformat(rec["valid_to"]):
                    corrected = center + timedelta(seconds=rec["offset_s"])
                    width = timedelta(seconds=rec["uncertainty_s"])
                    e.update(t_min=(corrected-width).astimezone(IST).isoformat(), t_max=(corrected+width).astimezone(IST).isoformat(), calibration=rec)
                    break
        return sorted(events, key=lambda e: (e["t_min"], e["id"]))


@router.get("/cases/{cid}/requests")
def requests(cid: str):
    claims = case_claims(cid)
    with connect() as conn:
        config = fetch_one(conn, "SELECT path FROM artifacts WHERE case_id=? AND type='site_config' ORDER BY id LIMIT 1", (cid,))
    if not config:
        return []
    date = json.loads(Path(config["path"]).read_text(encoding="utf-8"))["case_date"]
    return rank_requests(cid, date, claims)


@router.get("/cases/{cid}/report.json")
def report(cid: str):
    with connect() as conn:
        case = require_case(conn, cid)
        claims = findings(conn, cid)
        reviews = fetch_all(conn, "SELECT r.* FROM reviews r JOIN audit_entries a ON a.action='review_recorded' AND json_extract(a.payload,'$.id')=r.id WHERE a.case_id=? ORDER BY r.id", (cid,))
        manual = [a["id"] for a in service.list_artifacts(conn,cid) if a["type"] == "cctv_still" and
                  not conn.execute("SELECT 1 FROM events WHERE artifact_id=?", (a["id"],)).fetchone()]
        return dict(manual_time_required=manual, section_63_checklist=CHECKLIST, checklist_source=LEGAL_SOURCE, requests=requests(cid), observations=observations(cid), case=case, claims=claims, events=list_events(conn,cid), reviews=reviews,
                    artifacts=[{key: value for key, value in a.items() if key != "path"} for a in service.list_artifacts(conn,cid)], audit=audit.verify(conn,cid),
                    limitations=["Synthetic case. Device activity alone cannot identify the operator."])


@router.post("/artifacts/{aid}/manual-time")
def manual_time(aid: str, timestamp: str, reviewer: str):
    from .timeengine import event_range

    if not reviewer.strip():
        raise HTTPException(422, "Reviewer required")
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        a = fetch_one(conn, "SELECT * FROM artifacts WHERE id=? AND type='cctv_still'", (aid,))
        if not a:
            raise HTTPException(404, "Unknown camera still")
        if conn.execute("SELECT 1 FROM events WHERE artifact_id=?", (aid,)).fetchone():
            raise HTTPException(409, "A reading already exists")
        try:
            low, high = event_range("cctv_still", timestamp, "Asia/Kolkata")
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        row = dict(id=next_id(conn,"E",4), case_id=a["case_id"], artifact_id=aid, locator="frame 1",
                   action="camera_sighting", original_time=timestamp, original_tz="Asia/Kolkata",
                   t_min=low,t_max=high,fields={"camera":a["meta"].get("camera"),"reading":"manual"})
        insert(conn,"events",row)
        audit.append(conn,a["case_id"],reviewer,"manual_time_entry",row)
        return row


@router.get("/cases/{cid}/observations")
def observations(cid: str, calibrated: bool = True):
    from datetime import datetime
    events = timeline(cid, calibrated)
    alerts = []
    previous = {}
    cameras = {}
    for e in events:
        if e["action"] == "camera_sighting":
            cameras.setdefault(e["fields"]["camera"], e)
        if e["action"] not in ("badge_in","badge_out"):
            continue
        key = (e["artifact_id"], e["fields"]["badge_id"])
        prior = previous.get(key)
        if prior and prior["action"] == e["action"] and prior["place"] == e["place"]:
            gap = (datetime.fromisoformat(e["t_min"]) - datetime.fromisoformat(prior["t_min"])).total_seconds()
            if gap <= 2:
                continue
            alerts.append(dict(id="O-"+e["id"], rule="R1", certainty="certain", event_ids=[prior["id"],e["id"]],
                               explanation=f"Repeated {e['action']} for {key[1]}, {gap:g} seconds apart. Check for a double tap."))
        previous[key] = e
    first, second = cameras.get("CAM-A"), cameras.get("CAM-B")
    if first and second and second["t_min"] < first["t_max"]:
        alerts.append(dict(id="O-"+second["id"],rule="R1",certainty="certain" if second["t_max"] < first["t_min"] else "possible",
                           event_ids=[first["id"],second["id"]],explanation="The camera ranges allow the corridor sighting to precede the entrance."))
    with connect() as conn:
        for alert in alerts:
            alert["reviews"] = fetch_all(conn, "SELECT * FROM reviews WHERE target_id=? ORDER BY id", (alert["id"],))
    return alerts


@router.get("/cases/{cid}/report.pdf")
def pdf_report(cid: str):
    try:
        content = render_pdf(report(cid))
    except RuntimeError as exc:
        raise HTTPException(503, str(exc))
    return Response(content, media_type="application/pdf")


@router.post("/cases/{cid}/statements/{sid}/manual-claims", response_model=models.Claim)
def manual_claim(cid: str, sid: str, body: dict):
    from .extract import ExtractedClaim
    from pydantic import ValidationError
    try:
        claim = ExtractedClaim.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(422, str(exc))
    with connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        statement = fetch_one(conn, "SELECT * FROM statements WHERE id=? AND case_id=?", (sid,cid))
        if not statement:
            raise HTTPException(404, "Unknown statement")
        start = body.get("char_start", statement["text"].find(claim.quote))
        if type(start) is not int or start < 0 or statement["text"][start:start+len(claim.quote)] != claim.quote:
            raise HTTPException(422, "Select the exact quote in the statement")
        existing = fetch_one(conn, "SELECT * FROM claims WHERE statement_id=? AND char_start=? AND quote=?", (sid,start,claim.quote))
        if existing:
            return existing
        row = dict(claim.model_dump(), id=next_id(conn,"CL"), statement_id=sid, char_start=start,
                   char_end=start+len(claim.quote), source="manual")
        insert(conn,"claims",row)
        audit.append(conn,cid,"reviewer","claims_extracted",{"statement_id":sid,"claim_id":row["id"],"source":"manual"})
        return row


@router.post("/claims/{claim_id}/alternatives")
def alternatives(claim_id: str):
    import os
    from .extract.alternatives import options, select_alternatives
    result = detail(claim_id)
    f = result["finding"]
    if not f or f["verdict"] not in ("uncertain","contradicted"):
        raise HTTPException(422, "Select a conflict first")
    try:
        live = os.getenv("UBHAYA_EXTRACT_MODE", "cached") == "live"
        rows = select_alternatives(result["events"]) if live else options(result["events"])
    except ValueError as exc:
        raise HTTPException(503, str(exc))
    with connect() as conn:
        conn.execute("DELETE FROM alternatives WHERE finding_id=?", (f["id"],))
        for row in rows:
            insert(conn,"alternatives",dict(row,id=next_id(conn,"AL"),finding_id=f["id"],ai_generated=live))
    return rows

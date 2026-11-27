"""Load the whole synthetic demo case in one call (P1.3).

answers.json is the answer key and is deliberately never registered as evidence."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .config import DEMO_CASE_DIR
from .db import fetch_one, insert, next_id
from .intake import audit, service
from .parsers import parse_artifact

DEMO_TITLE = "PC-14 file copy (synthetic demo)"
ACQUIRED_AT = "2025-12-05T14:00:00+05:30"
ACTOR = "demo-loader"

ARTIFACTS = [
    # (relative path, type, source, meta)
    ("artifacts/door_log.csv", "door_log", "Office access-control export, main and staff doors", {"timezone": "Asia/Kolkata"}),
    ("artifacts/pc14_events.csv", "pc_event_log", "PC-14 Windows Security log export", {"device": "PC-14"}),
    ("artifacts/upi_ravi.csv", "bank_upi", "Bank statement, Ravi Kumar's UPI account", {"holder": "Ravi Kumar", "timezone": "Asia/Kolkata"}),
    ("artifacts/whatsapp_ravi_aman.txt", "chat_export", "WhatsApp chat export from Ravi Kumar's phone", {"owner": "Ravi Kumar"}),
    ("artifacts/cctv/cam_a_2206.png", "cctv_still", "Office CCTV still, entrance camera", {"camera": "CAM-A"}),
    ("artifacts/cctv/cam_b_2205.png", "cctv_still", "Office CCTV still, corridor camera", {"camera": "CAM-B"}),
    ("artifacts/cctv/cam_b_blurry.png", "cctv_still", "Office CCTV still, corridor camera", {"camera": "CAM-B"}),
    ("calibration.json", "calibration", "Clock calibration record prepared by investigator", {}),
    ("site_config.json", "site_config", "Site layout, required orders and travel times", {}),
]


def find_demo_case(conn: sqlite3.Connection) -> dict | None:
    return fetch_one(conn, "SELECT * FROM cases WHERE title = ? ORDER BY id DESC LIMIT 1", (DEMO_TITLE,))


def load_demo(conn: sqlite3.Connection, demo_dir: Path = DEMO_CASE_DIR) -> dict:
    if not (demo_dir / "artifacts" / "door_log.csv").exists():
        raise FileNotFoundError(f"demo pack missing in {demo_dir}; run: python manage.py make-demo")
    case = service.create_case(conn, DEMO_TITLE, scope="Copying of finance files from PC-14 on the night of 3 Dec 2025",
                               synthetic=True, actor=ACTOR)
    cid = case["id"]
    artifacts = []
    for rel, typ, source, meta in ARTIFACTS:
        art = service.register_artifact(conn, cid, filename=rel.split("/", 1)[-1] if rel.startswith("artifacts/") else rel,
                                        type=typ, source=source, acquired_at=ACQUIRED_AT, meta=meta,
                                        path=demo_dir / rel, actor=ACTOR)
        artifacts.append(art)

    statements_meta = json.loads((demo_dir / "statements" / "statements.json").read_text(encoding="utf-8"))["statements"]
    statements = []
    for s in statements_meta:
        path = demo_dir / "statements" / s["file"]
        art = service.register_artifact(conn, cid, filename=f"statements/{s['file']}", type="statement",
                                        source=f"Recorded statement of {s['speaker']} ({s['role']})",
                                        acquired_at=ACQUIRED_AT, meta={"speaker": s["speaker"], "role": s["role"], "language": s["language"]},
                                        path=path, actor=ACTOR)
        text = Path(art["path"]).read_text(encoding="utf-8")  # read from the store, not the original
        stmt = {"id": next_id(conn, "S"), "case_id": cid, "artifact_id": art["id"], "speaker": s["speaker"],
                "role": s["role"], "language": s["language"], "text": text}
        insert(conn, "statements", stmt)
        audit.append(conn, cid, ACTOR, "statement_registered", {"statement_id": stmt["id"], "artifact_id": art["id"],
                                                                 "speaker": s["speaker"], "role": s["role"]})
        statements.append(stmt)

    calib_art = next(a for a in artifacts if a["type"] == "calibration")
    for rec in json.loads(Path(calib_art["path"]).read_text(encoding="utf-8"))["records"]:
        insert(conn, "calibrations", {"case_id": cid, **{k: rec[k] for k in (
            "source_id", "offset_s", "uncertainty_s", "method", "reference_artifact", "valid_from", "valid_to")}})

    event_count = sum(len(parse_artifact(conn, a, actor=ACTOR)) for a in artifacts)
    return {"case": service.get_case(conn, cid), "artifacts": len(artifacts) + len(statements),
            "statements": len(statements), "events": event_count}

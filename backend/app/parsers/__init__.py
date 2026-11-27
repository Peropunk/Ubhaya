"""Parser registry: artifact type -> parse(path, meta) -> list of event dicts."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from ..db import fetch_all, insert, next_id
from ..intake import audit
from . import door, pc_log, upi

PARSERS = {
    "door_log": door.parse,
    "pc_event_log": pc_log.parse,
    "bank_upi": upi.parse,
    # chat_export (P3.1) and cctv_still (P3.2) are added in Phase 3
}


def parse_artifact(conn: sqlite3.Connection, artifact: dict, actor: str = "system") -> list[dict]:
    """Parse one stored artifact and save its events. Re-parsing replaces earlier events."""
    parser = PARSERS.get(artifact["type"])
    if parser is None:
        return []
    raw_events = parser(Path(artifact["path"]), artifact.get("meta") or {})
    conn.execute("DELETE FROM events WHERE artifact_id = ?", (artifact["id"],))
    for ev in raw_events:
        insert(conn, "events", {"id": next_id(conn, "E", 4), "case_id": artifact["case_id"],
                                "artifact_id": artifact["id"], **ev})
    audit.append(conn, artifact["case_id"], actor, "events_parsed", {
        "artifact_id": artifact["id"], "sha256": artifact["sha256"], "parser": artifact["type"],
        "events": len(raw_events),
    })
    return list_events(conn, artifact["case_id"], artifact["id"])


def list_events(conn: sqlite3.Connection, case_id: str, artifact_id: str | None = None) -> list[dict]:
    if artifact_id:
        return fetch_all(conn, "SELECT * FROM events WHERE case_id = ? AND artifact_id = ? ORDER BY id", (case_id, artifact_id))
    return fetch_all(conn, "SELECT * FROM events WHERE case_id = ? ORDER BY id", (case_id,))

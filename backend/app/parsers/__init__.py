"""Parser registry: artifact type -> parse(path, meta) -> list of event dicts."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from ..db import fetch_all, insert, next_id
from ..intake import audit
from ..timeengine import event_range
from . import camera, chat, door, pc_log, upi

PARSERS = {
    "door_log": door.parse,
    "pc_event_log": pc_log.parse,
    "bank_upi": upi.parse,
    "cctv_still": camera.parse,
    "chat_export": chat.parse,
}


def parse_artifact(conn: sqlite3.Connection, artifact: dict, actor: str = "system") -> list[dict]:
    """Parse one stored artifact and save its events. Re-parsing replaces earlier events."""
    parser = PARSERS.get(artifact["type"])
    if parser is None:
        return []
    raw_events = parser(Path(artifact["path"]), artifact.get("meta") or {})
    for ev in raw_events:
        try:
            ev["t_min"], ev["t_max"] = event_range(
                artifact["type"], ev["original_time"], ev["original_tz"],
            )
        except ValueError as exc:
            raise ValueError(f"{artifact['filename']} {ev['locator']}: {exc}") from exc

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
    sql = (
        "SELECT e.*, a.type AS artifact_type FROM events e "
        "JOIN artifacts a ON a.id = e.artifact_id WHERE e.case_id = ?"
    )
    params = (case_id,)
    if artifact_id:
        sql += " AND e.artifact_id = ?"
        params += (artifact_id,)
    events = fetch_all(conn, sql + " ORDER BY e.id", params)
    for ev in events:
        artifact_type = ev.pop("artifact_type")
        # Phase 1 databases have source timestamps with no stored bounds.
        if ev["t_min"] is None or ev["t_max"] is None:
            ev["t_min"], ev["t_max"] = event_range(artifact_type, ev["original_time"], ev["original_tz"])
    return events

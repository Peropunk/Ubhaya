"""Hash-chained audit log, one chain per case (P1.2). Formula in docs/SPEC.md."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone

from ..db import fetch_all, insert

GENESIS = "0" * 64
IST = timezone(timedelta(hours=5, minutes=30))


def now_ist() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def payload_hash(seq: int, time: str, actor: str, action: str, payload: dict) -> str:
    return sha256_hex(canonical_json({"seq": seq, "time": time, "actor": actor, "action": action, "payload": payload}))


def entry_hash(prev: str, p_hash: str, action: str) -> str:
    return sha256_hex(prev + p_hash + action)


def append(conn: sqlite3.Connection, case_id: str, actor: str, action: str, payload: dict) -> dict:
    last = conn.execute(
        "SELECT seq, entry_hash FROM audit_entries WHERE case_id = ? ORDER BY seq DESC LIMIT 1", (case_id,)
    ).fetchone()
    seq = (last["seq"] + 1) if last else 1
    prev = last["entry_hash"] if last else GENESIS
    time = now_ist()
    p_hash = payload_hash(seq, time, actor, action, payload)
    entry = {
        "case_id": case_id, "seq": seq, "time": time, "actor": actor, "action": action,
        "payload": payload, "payload_hash": p_hash, "prev_hash": prev,
        "entry_hash": entry_hash(prev, p_hash, action),
    }
    insert(conn, "audit_entries", entry)
    return entry


def entries(conn: sqlite3.Connection, case_id: str) -> list[dict]:
    return fetch_all(conn, "SELECT * FROM audit_entries WHERE case_id = ? ORDER BY seq", (case_id,))


def verify(conn: sqlite3.Connection, case_id: str) -> dict:
    rows = entries(conn, case_id)
    prev = GENESIS
    for expected_seq, e in enumerate(rows, start=1):
        if e["seq"] != expected_seq:
            return {"ok": False, "entries": len(rows), "broken_at": expected_seq, "reason": "missing or reordered entry"}
        if e["prev_hash"] != prev:
            return {"ok": False, "entries": len(rows), "broken_at": e["seq"], "reason": "prev_hash does not match the previous entry"}
        if payload_hash(e["seq"], e["time"], e["actor"], e["action"], e["payload"]) != e["payload_hash"]:
            return {"ok": False, "entries": len(rows), "broken_at": e["seq"], "reason": "entry content was changed"}
        if entry_hash(prev, e["payload_hash"], e["action"]) != e["entry_hash"]:
            return {"ok": False, "entries": len(rows), "broken_at": e["seq"], "reason": "entry_hash does not match"}
        prev = e["entry_hash"]
    return {"ok": True, "entries": len(rows), "broken_at": None, "reason": None}

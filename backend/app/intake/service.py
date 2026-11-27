"""Cases, artifact registration and verification (P1.1, P1.2)."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import BinaryIO, Optional

from ..config import CASE_TIMEZONE
from ..db import fetch_all, fetch_one, insert, next_id
from . import audit
from .store import put_file, put_stream, sha256_file

SYSTEM = "system"


class NotFound(LookupError):
    pass


def create_case(conn: sqlite3.Connection, title: str, scope: Optional[str] = None,
                synthetic: bool = False, actor: str = SYSTEM) -> dict:
    case = {
        "id": next_id(conn, "C"), "title": title, "timezone": CASE_TIMEZONE, "scope": scope,
        "created_at": audit.now_ist(), "synthetic": synthetic,
    }
    insert(conn, "cases", case)
    audit.append(conn, case["id"], actor, "case_created", {"title": title, "scope": scope, "synthetic": synthetic})
    return get_case(conn, case["id"])


def get_case(conn: sqlite3.Connection, case_id: str) -> dict:
    case = fetch_one(conn, "SELECT * FROM cases WHERE id = ?", (case_id,))
    if case is None:
        raise NotFound(f"case {case_id} not found")
    for key, table in (("artifact_count", "artifacts"), ("statement_count", "statements"), ("event_count", "events")):
        case[key] = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE case_id = ?", (case_id,)).fetchone()[0]
    return case


def list_cases(conn: sqlite3.Connection) -> list[dict]:
    return [get_case(conn, c["id"]) for c in fetch_all(conn, "SELECT id FROM cases ORDER BY id")]


def register_artifact(conn: sqlite3.Connection, case_id: str, *, filename: str, type: str,
                      source: Optional[str] = None, acquired_at: Optional[str] = None,
                      meta: Optional[dict] = None, path: Optional[Path] = None,
                      stream: Optional[BinaryIO] = None, actor: str = SYSTEM) -> dict:
    get_case(conn, case_id)
    if (path is None) == (stream is None):
        raise ValueError("give exactly one of path or stream")
    digest, size, stored = put_file(path) if path is not None else put_stream(stream)
    artifact = {
        "id": next_id(conn, "A"), "case_id": case_id, "filename": filename, "sha256": digest,
        "size": size, "type": type, "source": source, "acquired_at": acquired_at,
        "path": str(stored), "meta": meta or {}, "registered_at": audit.now_ist(),
    }
    insert(conn, "artifacts", artifact)
    audit.append(conn, case_id, actor, "artifact_registered", {
        "artifact_id": artifact["id"], "filename": filename, "sha256": digest, "size": size,
        "type": type, "source": source, "acquired_at": acquired_at,
    })
    return get_artifact(conn, artifact["id"])


def get_artifact(conn: sqlite3.Connection, artifact_id: str) -> dict:
    art = fetch_one(conn, "SELECT * FROM artifacts WHERE id = ?", (artifact_id,))
    if art is None:
        raise NotFound(f"artifact {artifact_id} not found")
    return art


def list_artifacts(conn: sqlite3.Connection, case_id: str) -> list[dict]:
    get_case(conn, case_id)
    return fetch_all(conn, "SELECT * FROM artifacts WHERE case_id = ? ORDER BY id", (case_id,))


def verify_artifact(conn: sqlite3.Connection, artifact_id: str, actor: str = SYSTEM) -> dict:
    art = get_artifact(conn, artifact_id)
    stored = Path(art["path"])
    actual = sha256_file(stored) if stored.exists() else None
    result = {"artifact_id": artifact_id, "expected": art["sha256"], "actual": actual, "ok": actual == art["sha256"]}
    audit.append(conn, art["case_id"], actor, "artifact_verified", result)
    return result

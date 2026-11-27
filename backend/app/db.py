"""SQLite storage. Plain sqlite3, one short-lived connection per unit of work.
Tables follow docs/SPEC.md; JSON columns are encoded and decoded here."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

from .config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS cases (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, timezone TEXT NOT NULL, scope TEXT,
  created_at TEXT NOT NULL, synthetic INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), filename TEXT NOT NULL,
  sha256 TEXT NOT NULL, size INTEGER NOT NULL, type TEXT NOT NULL, source TEXT,
  acquired_at TEXT, path TEXT NOT NULL, meta TEXT NOT NULL DEFAULT '{}', registered_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY, case_id TEXT NOT NULL, artifact_id TEXT NOT NULL REFERENCES artifacts(id),
  locator TEXT NOT NULL, actor TEXT, action TEXT NOT NULL, place TEXT,
  original_time TEXT NOT NULL, original_tz TEXT NOT NULL, t_min TEXT, t_max TEXT,
  confidence REAL NOT NULL DEFAULT 1.0, fields TEXT NOT NULL DEFAULT '{}', raw TEXT);
CREATE TABLE IF NOT EXISTS calibrations (
  id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, source_id TEXT NOT NULL,
  offset_s INTEGER NOT NULL, uncertainty_s INTEGER NOT NULL, method TEXT,
  reference_artifact TEXT, valid_from TEXT NOT NULL, valid_to TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS statements (
  id TEXT PRIMARY KEY, case_id TEXT NOT NULL, artifact_id TEXT NOT NULL REFERENCES artifacts(id),
  speaker TEXT NOT NULL, role TEXT NOT NULL, language TEXT NOT NULL, text TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS claims (
  id TEXT PRIMARY KEY, statement_id TEXT NOT NULL REFERENCES statements(id), quote TEXT NOT NULL,
  char_start INTEGER NOT NULL, char_end INTEGER NOT NULL, type TEXT NOT NULL, subject TEXT,
  action TEXT, place TEXT, value TEXT, time_expr TEXT, t_min TEXT, t_max TEXT,
  negated INTEGER NOT NULL DEFAULT 0, exclusive INTEGER NOT NULL DEFAULT 0,
  prompt_version TEXT, source TEXT NOT NULL DEFAULT 'llm');
CREATE TABLE IF NOT EXISTS findings (
  id TEXT PRIMARY KEY, claim_id TEXT NOT NULL REFERENCES claims(id), verdict TEXT NOT NULL,
  strength TEXT, event_ids TEXT NOT NULL DEFAULT '[]', rule_ids TEXT NOT NULL DEFAULT '[]',
  certainty TEXT, explanation TEXT, ai_generated INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS alternatives (
  id TEXT PRIMARY KEY, finding_id TEXT NOT NULL REFERENCES findings(id), text TEXT NOT NULL,
  event_ids TEXT NOT NULL DEFAULT '[]', ai_generated INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS evidence_requests (
  id TEXT PRIMARY KEY, case_id TEXT NOT NULL, claim_ids TEXT NOT NULL DEFAULT '[]',
  catalogue_id TEXT NOT NULL, score REAL NOT NULL, score_parts TEXT NOT NULL DEFAULT '{}', draft_text TEXT);
CREATE TABLE IF NOT EXISTS reviews (
  id TEXT PRIMARY KEY, target_id TEXT NOT NULL, reviewer TEXT NOT NULL, decision TEXT NOT NULL,
  reason TEXT, edit TEXT, time TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_entries (
  case_id TEXT NOT NULL, seq INTEGER NOT NULL, time TEXT NOT NULL, actor TEXT NOT NULL,
  action TEXT NOT NULL, payload TEXT NOT NULL, payload_hash TEXT NOT NULL,
  prev_hash TEXT NOT NULL, entry_hash TEXT NOT NULL, PRIMARY KEY (case_id, seq));
CREATE INDEX IF NOT EXISTS idx_events_case ON events(case_id, artifact_id);
"""

JSON_COLUMNS = {"meta", "fields", "event_ids", "rule_ids", "claim_ids", "score_parts", "payload", "edit"}
BOOL_COLUMNS = {"synthetic", "negated", "exclusive", "ai_generated"}


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(get_settings().db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def next_id(conn: sqlite3.Connection, prefix: str, width: int = 3) -> str:
    conn.execute("INSERT INTO counters(name, value) VALUES (?, 0) ON CONFLICT(name) DO NOTHING", (prefix,))
    conn.execute("UPDATE counters SET value = value + 1 WHERE name = ?", (prefix,))
    (value,) = conn.execute("SELECT value FROM counters WHERE name = ?", (prefix,)).fetchone()
    return f"{prefix}{value:0{width}d}"


def encode(value: Any, column: str) -> Any:
    if column in JSON_COLUMNS and value is not None and not isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return int(value)
    return value


def decode_row(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    out = {}
    for key in row.keys():
        value = row[key]
        if key in JSON_COLUMNS and isinstance(value, str):
            value = json.loads(value)
        elif key in BOOL_COLUMNS and value is not None:
            value = bool(value)
        out[key] = value
    return out


def insert(conn: sqlite3.Connection, table: str, values: dict) -> None:
    cols = list(values)
    conn.execute(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
        [encode(values[c], c) for c in cols],
    )


def fetch_one(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> dict | None:
    return decode_row(conn.execute(sql, params).fetchone())


def fetch_all(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [decode_row(r) for r in conn.execute(sql, params).fetchall()]

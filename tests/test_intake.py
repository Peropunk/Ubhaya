"""P1.2 done-when: re-hashing a file matches; editing a log entry breaks the chain check."""
import json
import os
import stat
from pathlib import Path

from app.db import connect
from app.intake import audit, service
from app.intake.store import is_read_only, sha256_file


def _case_with_file(tmp_path):
    original = tmp_path / "evidence.txt"
    original.write_bytes(b"original evidence\n")
    with connect() as conn:
        case = service.create_case(conn, "t")
        art = service.register_artifact(conn, case["id"], filename="evidence.txt", type="statement", path=original)
    return case, art, original


def test_store_copy_is_read_only_and_hash_matches(tmp_path):
    _, art, original = _case_with_file(tmp_path)
    stored = Path(art["path"])
    assert stored != original and stored.name == art["sha256"]
    assert is_read_only(stored)
    assert sha256_file(stored) == sha256_file(original) == art["sha256"]
    assert not is_read_only(original)  # the original is left exactly as it was


def test_same_content_stored_once(tmp_path):
    case, art, original = _case_with_file(tmp_path)
    with connect() as conn:
        again = service.register_artifact(conn, case["id"], filename="copy.txt", type="statement", path=original)
    assert again["id"] != art["id"] and again["path"] == art["path"]


def test_verify_detects_tampering(tmp_path):
    _, art, _ = _case_with_file(tmp_path)
    with connect() as conn:
        assert service.verify_artifact(conn, art["id"])["ok"]
    stored = Path(art["path"])
    os.chmod(stored, stat.S_IWRITE | stat.S_IREAD)
    stored.write_bytes(b"tampered\n")
    with connect() as conn:
        res = service.verify_artifact(conn, art["id"])
    assert res["ok"] is False and res["actual"] != res["expected"]


def test_audit_chain_ok_then_broken_by_payload_edit(tmp_path):
    case, art, _ = _case_with_file(tmp_path)
    with connect() as conn:
        assert audit.verify(conn, case["id"])["ok"]
        conn.execute("UPDATE audit_entries SET payload = ? WHERE case_id = ? AND seq = 2",
                     (json.dumps({"artifact_id": art["id"], "sha256": "0" * 64}), case["id"]))
        res = audit.verify(conn, case["id"])
    assert res["ok"] is False and res["broken_at"] == 2


def test_audit_chain_broken_by_time_or_actor_edit(tmp_path):
    case, _, _ = _case_with_file(tmp_path)
    with connect() as conn:
        conn.execute("UPDATE audit_entries SET time = '2020-01-01T00:00:00+05:30' WHERE case_id = ? AND seq = 1", (case["id"],))
        assert audit.verify(conn, case["id"])["broken_at"] == 1


def test_audit_chain_broken_by_deleted_entry(tmp_path):
    case, art, _ = _case_with_file(tmp_path)
    with connect() as conn:
        service.verify_artifact(conn, art["id"])
        conn.execute("DELETE FROM audit_entries WHERE case_id = ? AND seq = 2", (case["id"],))
        res = audit.verify(conn, case["id"])
    assert res["ok"] is False and res["broken_at"] == 2


def test_entry_hash_formula():
    p = audit.payload_hash(1, "t", "a", "x", {"k": 1})
    assert audit.entry_hash(audit.GENESIS, p, "x") == audit.sha256_hex(audit.GENESIS + p + "x")

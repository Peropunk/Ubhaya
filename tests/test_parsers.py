"""P1.4 done-when: each row becomes an Event with its source row number and original timestamp."""
import pytest

from app.parsers import door, pc_log, upi
from conftest import DEMO

ART = DEMO / "artifacts"


def by_locator(events, locator):
    return next(e for e in events if e["locator"] == locator)


def test_door_log_every_row_and_planted_rows():
    events = door.parse(ART / "door_log.csv")
    assert len(events) == 187
    assert [e["locator"] for e in events[:2]] == ["row 1", "row 2"]
    ravi = by_locator(events, "row 184")
    assert (ravi["actor"], ravi["action"], ravi["original_time"], ravi["original_tz"]) == \
        ("Ravi Kumar", "badge_out", "2025-12-03 21:52:07", "Asia/Kolkata")
    assert ravi["raw"] == "2025-12-03 21:52:07,E-1047,Ravi Kumar,MAIN-ENTRANCE,OUT"
    v_in, v_double = by_locator(events, "row 185"), by_locator(events, "row 186")
    assert v_in["actor"] == v_double["actor"] == "V-03" and v_in["fields"]["visitor_card"] is True
    assert (v_in["original_time"], v_double["original_time"]) == ("2025-12-03 22:06:10", "2025-12-03 22:06:52")
    assert all(e["t_min"] is None for e in events)  # ranges are the time engine's job (P2.2)


def test_pc_log_keeps_utc():
    events = pc_log.parse(ART / "pc14_events.csv", {"device": "PC-14"})
    assert len(events) == 33
    logon = by_locator(events, "row 21")
    assert (logon["actor"], logon["action"], logon["original_time"], logon["original_tz"], logon["place"]) == \
        ("ravi.k", "logon", "2025-12-03T16:43:21Z", "UTC", "PC-14")
    assert by_locator(events, "row 22")["action"] == "usb_connected"
    copies = [e for e in events if e["action"] == "file_copy"]
    assert [c["locator"] for c in copies] == [f"row {n}" for n in range(23, 32)]


def test_upi_amounts_and_holder():
    events = upi.parse(ART / "upi_ravi.csv", {"holder": "Ravi Kumar"})
    assert len(events) == 16
    dhaba = by_locator(events, "row 11")
    assert dhaba["action"] == "upi_debit" and dhaba["actor"] == "Ravi Kumar"
    assert dhaba["fields"]["counterparty"] == "Sharma Dhaba" and dhaba["fields"]["amount"] == 340
    aman = by_locator(events, "row 12")
    assert (aman["action"], aman["fields"]["amount"], aman["original_time"]) == ("upi_credit", 15000, "2025-12-04 11:42:05")


def test_pc_log_rejects_non_utc(tmp_path):
    bad = tmp_path / "pc.csv"
    bad.write_text("time_utc,event_id,user,detail\n2025-12-03 16:43:21,4624,x,Logon\n", encoding="utf-8")
    with pytest.raises(ValueError, match="UTC"):
        pc_log.parse(bad)


def test_bad_column_count(tmp_path):
    bad = tmp_path / "door.csv"
    bad.write_text("time,badge_id,holder,door,direction\n2025-12-03 21:00:00,E-1,A,OUT\n", encoding="utf-8")
    with pytest.raises(ValueError, match="row 1"):
        door.parse(bad)

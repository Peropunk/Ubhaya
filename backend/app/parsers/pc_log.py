"""PC event log CSV exported from the Windows Security log: time_utc, event_id, user, detail.
Times stay in UTC here; P2.2 converts them to IST ranges."""
from __future__ import annotations

from pathlib import Path

from .base import event, read_csv_rows

EVENT_IDS = {4624: "logon", 4634: "logoff", 6416: "usb_connected", 6417: "usb_removed"}


def action_for(event_id: int, detail: str) -> str:
    if event_id in EVENT_IDS:
        return EVENT_IDS[event_id]
    if event_id == 4663:
        return "file_copy" if detail.lower().startswith("file copy") else "file_access"
    raise ValueError(f"unmapped Windows event id {event_id}")


def parse(path: Path, meta: dict | None = None) -> list[dict]:
    device = (meta or {}).get("device")
    out = []
    for n, row, raw in read_csv_rows(path):
        event_id = int(row["event_id"])
        detail = row["detail"].strip()
        original = row["time_utc"].strip()
        if not original.endswith("Z"):
            raise ValueError(f"PC log row {n}: expected a UTC time ending in Z, got {original!r}")
        out.append(event(
            f"row {n}", action_for(event_id, detail), original, "UTC",
            actor=row["user"].strip(), place=device,
            fields={"event_id": event_id, "user": row["user"].strip(), "detail": detail, "device": device},
            raw=raw,
        ))
    return out

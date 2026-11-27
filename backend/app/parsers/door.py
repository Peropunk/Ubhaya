"""Door access log CSV: time, badge_id, holder, door, direction (local time, IST)."""
from __future__ import annotations

from pathlib import Path

from .base import event, read_csv_rows

DIRECTIONS = {"IN": "badge_in", "OUT": "badge_out"}


def parse(path: Path, meta: dict | None = None) -> list[dict]:
    tz = (meta or {}).get("timezone", "Asia/Kolkata")
    out = []
    for n, row, raw in read_csv_rows(path):
        direction = row["direction"].strip().upper()
        if direction not in DIRECTIONS:
            raise ValueError(f"door log row {n}: unknown direction {row['direction']!r}")
        badge, holder = row["badge_id"].strip(), row["holder"].strip()
        is_visitor = badge.upper().startswith("V-")
        out.append(event(
            f"row {n}", DIRECTIONS[direction], row["time"].strip(), tz,
            actor=badge if is_visitor else holder,
            place=row["door"].strip(),
            fields={"badge_id": badge, "holder": holder, "door": row["door"].strip(),
                    "direction": direction, "visitor_card": is_visitor},
            raw=raw,
        ))
    return out

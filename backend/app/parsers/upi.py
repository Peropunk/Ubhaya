"""Bank / UPI statement CSV: time, direction (DR/CR), counterparty, amount, note, ref.
The account holder is not in the file, so it comes from artifact meta ("holder")."""
from __future__ import annotations

from pathlib import Path

from .base import event, read_csv_rows

DIRECTIONS = {"DR": "upi_debit", "CR": "upi_credit"}


def parse(path: Path, meta: dict | None = None) -> list[dict]:
    meta = meta or {}
    holder, tz = meta.get("holder"), meta.get("timezone", "Asia/Kolkata")
    out = []
    for n, row, raw in read_csv_rows(path):
        direction = row["direction"].strip().upper()
        if direction not in DIRECTIONS:
            raise ValueError(f"UPI row {n}: unknown direction {row['direction']!r}")
        amount_text = row["amount"].replace(",", "").strip()
        amount = float(amount_text)
        out.append(event(
            f"row {n}", DIRECTIONS[direction], row["time"].strip(), tz,
            actor=holder, place=None,
            fields={"direction": direction, "counterparty": row["counterparty"].strip(),
                    "amount": int(amount) if amount.is_integer() else amount,
                    "currency": "INR", "note": row["note"].strip(), "ref": row["ref"].strip()},
            raw=raw,
        ))
    return out

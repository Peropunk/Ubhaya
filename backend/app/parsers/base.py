"""Shared helpers for parsers. A parser turns one artifact into event dicts
(without id/case_id); it never changes times - that is the time engine's job."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator


def read_csv_rows(path: Path) -> Iterator[tuple[int, dict[str, str], str]]:
    """Yield (row_number, row_dict, raw_line). Row 1 is the first line after the header."""
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    if not lines:
        return
    header = next(csv.reader([lines[0]]))
    for n, line in enumerate(lines[1:], start=1):
        if not line.strip():
            continue
        values = next(csv.reader([line]))
        if len(values) != len(header):
            raise ValueError(f"{Path(path).name} row {n}: expected {len(header)} columns, got {len(values)}")
        yield n, dict(zip(header, values)), line


def event(locator: str, action: str, original_time: str, original_tz: str, *, actor=None,
          place=None, fields=None, raw=None, confidence: float = 1.0) -> dict:
    return {
        "locator": locator, "actor": actor, "action": action, "place": place,
        "original_time": original_time, "original_tz": original_tz,
        "t_min": None, "t_max": None, "confidence": confidence,
        "fields": fields or {}, "raw": raw,
    }

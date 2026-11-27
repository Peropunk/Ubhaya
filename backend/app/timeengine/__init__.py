"""Convert source timestamps to uncalibrated IST ranges (P2.2)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..config import CASE_TIMEZONE, IST

DEFAULT_UNCERTAINTY = {
    "door_log": timedelta(minutes=1),
    "pc_event_log": timedelta(minutes=1),
    "bank_upi": timedelta(minutes=1),
    "chat_export": timedelta(minutes=1),
    "cctv_still": timedelta(minutes=10),
}
DATE_AND_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}")


def event_range(artifact_type: str, original_time: str, original_tz: str) -> tuple[str, str]:
    """Return inclusive IST bounds, using the source's default uncertainty."""
    if artifact_type == "chat_export" and "/" in original_time:
        source_time = datetime.strptime(original_time, "%d/%m/%Y, %H:%M")
    elif artifact_type == "cctv_still" and not DATE_AND_TIME.match(original_time):
        source_time = datetime.strptime(original_time, "%d-%m-%Y %H:%M:%S")
    elif DATE_AND_TIME.match(original_time):
        source_time = datetime.fromisoformat(original_time)
    else:
        raise ValueError(f"expected an ISO date and time, got {original_time!r}")
    if source_time.tzinfo is None:
        source_time = _localize(source_time, original_tz)
    center = source_time.astimezone(IST)
    uncertainty = DEFAULT_UNCERTAINTY[artifact_type]
    return (center - uncertainty).isoformat(), (center + uncertainty).isoformat()


def _localize(local_time: datetime, zone_name: str) -> datetime:
    if zone_name == CASE_TIMEZONE:
        return local_time.replace(tzinfo=IST)
    if zone_name == "UTC":
        return local_time.replace(tzinfo=timezone.utc)
    try:
        zone = ZoneInfo(zone_name)
    except (TypeError, ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError(f"unknown source timezone {zone_name!r}") from exc

    earlier = local_time.replace(tzinfo=zone, fold=0)
    later = local_time.replace(tzinfo=zone, fold=1)
    if earlier.utcoffset() != later.utcoffset():
        raise ValueError(f"local time {local_time} in {zone_name} requires an explicit UTC offset")
    return earlier

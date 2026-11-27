"""Resolve the statement time expressions used in the evening PC-14 incident."""
import re
from datetime import datetime, timedelta

from ..config import IST


def claim_window(quote, case_date, case_window):
    date = datetime.fromisoformat(case_date).replace(tzinfo=IST)
    night = date + timedelta(hours=18), date + timedelta(days=1,hours=6)
    clock = re.search(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)(?:\s*([ap])\.?m\.?\b)?", quote, re.I)
    if clock:
        hour, minute = int(clock[1]), int(clock[2])
        period = clock[3]
        if minute > 59 or hour > 23 or (period and not 1 <= hour <= 12):
            raise ValueError(f"Invalid clock time {clock.group().strip()!r}")
        if period:
            hour = hour % 12 + (12 if period.lower() == "p" else 0)
        elif 0 < hour < 12:
            hour += 12
        if "4 December" in quote:
            date += timedelta(days=1)
        center = date.replace(hour=hour,minute=minute)
        width = timedelta(minutes=15 if re.search("around|about|करीब|kareeb",quote,re.I) else 5)
        return center-width, center+width
    if "4 December" in quote:
        return date+timedelta(days=1), date+timedelta(days=2,seconds=-1)
    if "दस बजे के बाद" in quote:
        return date.replace(hour=22), night[1]
    if re.search("night|raat|रात",quote,re.I):
        return night
    return case_window

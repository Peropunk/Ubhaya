"""Read WhatsApp text exports with day/month/year timestamps."""
import re
from pathlib import Path

from .base import event

MESSAGE = re.compile(r"^(\d{1,2}/\d{1,2}/\d{4}, \d{2}:\d{2}) - ([^:]+): (.*)$")


def parse(path: Path, meta: dict | None = None) -> list[dict]:
    events = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        match = MESSAGE.match(line)
        if match:
            timestamp, actor, message = match.groups()
            events.append(event(f"line {number}", "chat_message", timestamp,
                                (meta or {}).get("timezone", "Asia/Kolkata"), actor=actor,
                                fields={"message": message}, raw=line))
        elif events:
            events[-1]["raw"] += "\n" + line
            events[-1]["fields"]["message"] += "\n" + line
    return events

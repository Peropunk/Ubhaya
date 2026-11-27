from pathlib import Path
from ..extract.overlay import read_overlay_time
from .base import event


def parse(path: Path, meta: dict | None = None) -> list[dict]:
    value, confidence = read_overlay_time(path)
    if value is None:
        return []
    camera = (meta or {}).get("camera")
    timestamp = value.strftime("%d-%m-%Y %H:%M:%S")
    return [event("frame 1", "camera_sighting", timestamp, "Asia/Kolkata", place=camera,
                  fields={"camera": camera, "reading": "overlay"}, raw=timestamp, confidence=confidence)]

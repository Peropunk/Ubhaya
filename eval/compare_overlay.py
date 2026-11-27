"""Compare the built-in reader with a local Tesseract installation."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import DEMO_CASE_DIR
from app.extract.overlay import read_overlay_time


def edit_distance(expected, actual):
    row = list(range(len(actual) + 1))
    for idx, first in enumerate(expected, 1):
        previous = row
        row = [idx]
        for jdx, second in enumerate(actual, 1):
            row.append(min(previous[jdx] + 1, row[-1] + 1, previous[jdx - 1] + (first != second)))
    return row[-1]


def compare(executable, tessdata):
    planted = json.loads((DEMO_CASE_DIR / "answers.json").read_text(encoding="utf-8"))["planted"]
    truth = dict(planted["cctv_truth"])
    truth[planted["known_failure"]] = planted["known_failure_truth"]["overlay"]
    results = []
    with TemporaryDirectory() as temp:
        crop = Path(temp) / "overlay.png"
        for name, expected in truth.items():
            path = DEMO_CASE_DIR / "artifacts" / name
            timestamp, score = read_overlay_time(path)
            builtin = timestamp.strftime("%d-%m-%Y %H:%M:%S") if timestamp else None
            with Image.open(path) as image:
                strip = image.convert("L").crop((image.width - 250, 0, image.width, 34))
                strip = ImageOps.invert(strip)
                strip.resize((750, 102)).save(crop)
            command = [executable, str(crop), "stdout", "--psm", "7",
                       "-c", "tessedit_char_whitelist=0123456789-: "]
            if tessdata:
                command.extend(["--tessdata-dir", tessdata])
            raw = subprocess.run(command, check=True, capture_output=True, text=True, timeout=20).stdout
            compact = "".join(raw.split())
            guess = compact[:10] + " " + compact[10:] if len(compact) == 18 else " ".join(raw.split())
            results.append(dict(frame=name, expected=expected, built_in=builtin, built_in_score=round(score, 3),
                                built_in_errors=edit_distance(expected, builtin) if builtin else None,
                                tesseract=guess, tesseract_errors=edit_distance(expected, guess)))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tesseract", default="tesseract")
    parser.add_argument("--tessdata")
    args = parser.parse_args()
    print(json.dumps(compare(args.tesseract, args.tessdata), indent=2))

"""Read the fixed-layout timestamp strip used by the synthetic cameras."""
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat


def read_overlay_time(path: Path):
    with Image.open(path) as image:
        strip = image.convert("L").crop((image.width - 250, 0, image.width, 34))
    font = ImageFont.load_default(size=22)
    prefix = ""
    errors = []
    for token in "dd-dd-dddd dd:dd:dd":
        candidates = []
        for char in "0123456789" if token == "d" else token:
            label = prefix + char
            template = Image.new("L", strip.size)
            ImageDraw.Draw(template).text((0, 5), label, font=font, fill=255)
            left = int(font.getlength(prefix))
            right = max(left + 1, int(font.getlength(label)))
            delta = ImageChops.difference(template, strip).crop((left, 5, right, 30))
            candidates.append((ImageStat.Stat(delta).mean[0], char))
        error, char = min(candidates)
        prefix += char
        if token == "d":
            errors.append(error)
    confidence = max(0, 1 - max(errors) / 128)
    try:
        value = datetime.strptime(prefix, "%d-%m-%Y %H:%M:%S")
    except ValueError:
        return None, confidence
    return (value if confidence >= 0.80 else None), confidence

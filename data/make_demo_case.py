"""Generate the synthetic PC-14 demo case and its answer key (chunk P0.2).

Everything here is invented: people, company, numbers, places and images.
Run:  python data/make_demo_case.py
The random seed is fixed, so the pack (and the row numbers in answers.json)
never drift. Re-run after any change and commit the outputs.
"""
from __future__ import annotations

import csv
import io
import json
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 1403
CASE_DATE = date(2025, 12, 3)
OUT = Path(__file__).resolve().parent / "demo_case"
ART = OUT / "artifacts"
STM = OUT / "statements"

IST_FMT = "%Y-%m-%d %H:%M:%S"


def ist(day: int, hh: int, mm: int, ss: int = 0, month: int = 12) -> datetime:
    return datetime(2025, month, day, hh, mm, ss)


# ---------------------------------------------------------------- door log
EMPLOYEES = [
    ("E-1001", "Sunil Mehta"), ("E-1012", "Priya Nair"), ("E-1019", "Arjun Rao"),
    ("E-1023", "Kavita Joshi"), ("E-1031", "Imran Shaikh"), ("E-1036", "Deepa Iyer"),
    ("E-1040", "Manoj Pillai"), ("E-1044", "Sneha Kulkarni"), ("E-1047", "Ravi Kumar"),
    ("E-1052", "Farhan Ali"), ("E-1055", "Meera Das"), ("E-1058", "Rohit Bansal"),
    ("E-1063", "Anita George"), ("E-1067", "Vikram Sethi"), ("E-1071", "Pooja Menon"),
    ("E-1075", "Harish Gupta"), ("E-1079", "Lata Reddy"), ("E-1084", "Naveen Chawla"),
]
DOORS = ["MAIN-ENTRANCE", "STAFF-SIDE"]


@dataclass
class DoorRow:
    t: datetime
    badge: str
    holder: str
    door: str
    direction: str
    tag: str = ""  # internal marker for planted rows, not written out


def door_rows(rng: random.Random) -> list[DoorRow]:
    rows: list[DoorRow] = []
    for day in (2, 3):
        for badge, holder in EMPLOYEES:
            door = rng.choice(DOORS)
            t_in = ist(day, 8, 40) + timedelta(seconds=rng.randint(0, 80 * 60))
            rows.append(DoorRow(t_in, badge, holder, door, "IN"))
            # lunch break out and back in
            l_out = ist(day, 13, 0) + timedelta(seconds=rng.randint(0, 50 * 60))
            l_in = l_out + timedelta(seconds=rng.randint(20 * 60, 55 * 60))
            rows.append(DoorRow(l_out, badge, holder, "MAIN-ENTRANCE", "OUT"))
            rows.append(DoorRow(l_in, badge, holder, "MAIN-ENTRANCE", "IN"))
            if rng.random() < 0.45:  # a tea or errand trip
                e_out = ist(day, 16, 0) + timedelta(seconds=rng.randint(0, 60 * 60))
                e_in = e_out + timedelta(seconds=rng.randint(5 * 60, 25 * 60))
                rows.append(DoorRow(e_out, badge, holder, "STAFF-SIDE", "OUT"))
                rows.append(DoorRow(e_in, badge, holder, "STAFF-SIDE", "IN"))
            if day == 3 and badge == "E-1047":
                # Ravi stays late; planted OUT at 21:52:07
                rows.append(DoorRow(ist(3, 21, 52, 7), badge, holder, "MAIN-ENTRANCE", "OUT", "ravi_out"))
            else:
                t_out = ist(day, 17, 45) + timedelta(seconds=rng.randint(0, 3 * 3600 + 15 * 60))
                rows.append(DoorRow(t_out, badge, holder, rng.choice(DOORS), "OUT"))
    # visitor card V-03: planted entry, double tap (false alarm) and exit
    rows.append(DoorRow(ist(3, 22, 6, 10), "V-03", "VISITOR CARD", "MAIN-ENTRANCE", "IN", "v03_in"))
    rows.append(DoorRow(ist(3, 22, 6, 52), "V-03", "VISITOR CARD", "MAIN-ENTRANCE", "IN", "v03_double"))
    rows.append(DoorRow(ist(3, 22, 31, 24), "V-03", "VISITOR CARD", "MAIN-ENTRANCE", "OUT", "v03_out"))
    # a daytime visitor on 2 Dec, harmless
    rows.append(DoorRow(ist(2, 11, 15, 3), "V-01", "VISITOR CARD", "MAIN-ENTRANCE", "IN"))
    rows.append(DoorRow(ist(2, 12, 2, 40), "V-01", "VISITOR CARD", "MAIN-ENTRANCE", "OUT"))
    rows.sort(key=lambda r: r.t)
    # guard statement G5: no employee badges IN after 22:00 on 3 Dec
    assert not any(r.direction == "IN" and r.badge.startswith("E-") and r.t >= ist(3, 22, 0) for r in rows)
    # Ravi's OUT must be the last employee event on 3 Dec
    late = [r for r in rows if r.t.date() == CASE_DATE and r.badge.startswith("E-") and r.t > ist(3, 21, 0)]
    assert [r.tag for r in late][-1] == "ravi_out", "another employee is still in after Ravi"
    return rows


# ---------------------------------------------------------------- PC-14 log (UTC)
def utc(hh: int, mm: int, ss: int) -> datetime:
    return datetime(2025, 12, 3, hh, mm, ss)


def pc_rows(rng: random.Random) -> list[tuple[datetime, int, str, str, str]]:
    rows: list[tuple[datetime, int, str, str, str]] = []
    rows.append((utc(3, 58, 12), 4624, "priya.n", "Logon type 2 (interactive)", ""))
    t = utc(4, 5, 0)
    day_files = ["Vendor_master.xlsx", "Invoice_batch_1127.pdf", "Payroll_draft_Nov.xlsx",
                 "GST_returns_Q3.xlsx", "Bank_reco_Nov.xlsx", "Petty_cash_log.docx"]
    for _ in range(18):
        t += timedelta(seconds=rng.randint(600, 1700))
        f = rng.choice(day_files)
        rows.append((t, 4663, "priya.n", f"Object access: D:\\Finance\\{f} (read)", ""))
    rows.append((utc(12, 4, 55), 4634, "priya.n", "Logoff", ""))
    # planted: ravi.k account logs on at 16:43:21 UTC = 22:13:21 IST
    rows.append((utc(16, 43, 21), 4624, "ravi.k", "Logon type 2 (interactive)", "logon"))
    rows.append((utc(16, 44, 5), 6416, "ravi.k",
                 "New external device: USB mass storage, vendor DEMO-USB, serial 0019E06B, mounted E:", "usb"))
    copied = ["Q3_vendor_payments.xlsx", "Vendor_bank_details.xlsx", "Tender_bids_2025.pdf",
              "Rate_contract_Dec.xlsx", "Board_note_Nov.docx", "Vendor_master.xlsx",
              "Audit_observations.pdf", "Payment_approvals_Q3.pdf"]
    t = utc(16, 44, 38)
    for f in copied:
        rows.append((t, 4663, "ravi.k", f"File copy: D:\\Finance\\{f} -> E:\\{f}", "copy"))
        t += timedelta(seconds=rng.randint(40, 60))
    assert t <= utc(16, 52, 41)
    rows.append((utc(16, 52, 41), 4663, "ravi.k", "File copy: D:\\Finance\\Signatory_list.pdf -> E:\\Signatory_list.pdf", "copy"))
    rows.append((utc(16, 53, 2), 6417, "ravi.k", "Device removed: USB mass storage, serial 0019E06B", ""))
    rows.append((utc(16, 53, 30), 4634, "ravi.k", "Logoff", ""))
    rows.sort(key=lambda r: r[0])
    return rows


# ---------------------------------------------------------------- UPI (IST)
def upi_rows(rng: random.Random) -> list[tuple[datetime, str, str, int, str, str]]:
    planted = [
        (ist(1, 19, 41, 12), "DR", "Aman Verma", 15000, "udhaar", "aman_loan"),
        (ist(3, 22, 20, 31), "DR", "Sharma Dhaba", 340, "dinner", "dhaba"),
        (ist(4, 11, 42, 5), "CR", "Aman Verma", 15000, "udhaar wapas", "aman_return"),
    ]
    filler_merchants = [("Ganesh Kirana Store", 180, 900), ("City Metro Card Topup", 200, 500),
                        ("Mobile Recharge", 199, 399), ("Hari Chai Stall", 20, 60),
                        ("Bharat Medicals", 90, 450), ("Shree Sabzi Bhandar", 60, 240)]
    rows = list(planted)
    days = [(11, 28), (11, 29), (11, 30), (12, 1), (12, 2), (12, 3), (12, 4), (12, 5)]
    while len(rows) < 15:
        m, d = rng.choice(days)
        name, lo, hi = rng.choice(filler_merchants)
        t = datetime(2025, m, d, rng.randint(8, 20), rng.randint(0, 59), rng.randint(0, 59))
        if t.date() == CASE_DATE and t.hour >= 21:
            continue
        rows.append((t, "DR", name, rng.randint(lo, hi), "", ""))
    rows.append((datetime(2025, 11, 30, 10, 2, 44), "CR", "Saanvi Logistics Pvt Ltd", 41250, "salary nov", ""))
    rows.sort(key=lambda r: r[0])
    return rows


# ---------------------------------------------------------------- WhatsApp export
def chat_lines() -> list[tuple[str, str]]:
    """(line, tag). Standard Android export: dd/mm/yyyy, HH:MM - Name: text"""
    msgs = [
        ("28/11/2025, 20:14", "Aman Verma", "bhai kal match dekhne chalega?"),
        ("28/11/2025, 20:16", "Ravi Kumar", "nahi yaar, month end hai, office mein kaam bahut hai"),
        ("28/11/2025, 20:17", "Aman Verma", "theek hai"),
        ("29/11/2025, 09:03", "Aman Verma", "good morning"),
        ("29/11/2025, 09:40", "Ravi Kumar", "gm"),
        ("30/11/2025, 18:22", "Ravi Kumar", "salary aa gayi finally"),
        ("30/11/2025, 18:25", "Aman Verma", "party?"),
        ("30/11/2025, 18:26", "Ravi Kumar", "haha dekhte hai"),
        ("01/12/2025, 19:30", "Aman Verma", "bhai ek help chahiye, 15k urgent chahiye. 4 tareekh tak wapas kar dunga pakka", "loan_ask"),
        ("01/12/2025, 19:33", "Ravi Kumar", "theek hai, bhej raha hu", "loan_ok"),
        ("01/12/2025, 19:42", "Ravi Kumar", "bhej diya, check kar"),
        ("01/12/2025, 19:44", "Aman Verma", "mil gaya, thanks bhai"),
        ("02/12/2025, 13:10", "Aman Verma", "lunch kiya?"),
        ("02/12/2025, 13:31", "Ravi Kumar", "haan canteen mein"),
        ("02/12/2025, 21:05", "Aman Verma", "<Media omitted>"),
        ("02/12/2025, 21:06", "Ravi Kumar", "lol"),
        ("03/12/2025, 12:48", "Aman Verma", "aaj raat free hai?"),
        ("03/12/2025, 12:55", "Ravi Kumar", "late niklunga, audit ka kaam hai"),
        ("03/12/2025, 21:40", "Ravi Kumar", "bas nikal raha hu office se"),
        ("03/12/2025, 21:41", "Aman Verma", "ok, main ghar pe hu"),
        ("03/12/2025, 22:07", "Ravi Kumar", "dhaba pahunch gaya, khana order kar raha hu", "dhaba_chat"),
        ("03/12/2025, 22:08", "Aman Verma", "kaunsa dhaba?"),
        ("03/12/2025, 22:09", "Ravi Kumar", "Sharma Dhaba, highway wala"),
        ("03/12/2025, 22:10", "Aman Verma", "badhiya, enjoy"),
        ("03/12/2025, 22:41", "Ravi Kumar", "ghar ja raha hu ab"),
        ("03/12/2025, 22:43", "Aman Verma", "\U0001F44D"),
        ("04/12/2025, 09:15", "Aman Verma", "aaj paise bhej dunga"),
        ("04/12/2025, 09:20", "Ravi Kumar", "ok"),
        ("04/12/2025, 11:43", "Aman Verma", "bhej diye 15k, thanks bhai", "aman_paid_chat"),
        ("04/12/2025, 11:50", "Ravi Kumar", "mil gaye"),
        ("04/12/2025, 18:02", "Ravi Kumar", "office mein kuch problem hui hai, kal baat karta hu"),
        ("04/12/2025, 18:05", "Aman Verma", "kya hua?"),
        ("04/12/2025, 18:30", "Ravi Kumar", "pata nahi, koi files ka issue hai"),
        ("04/12/2025, 18:31", "Aman Verma", "tension mat le"),
        ("05/12/2025, 08:12", "Aman Verma", "sab theek?"),
        ("05/12/2025, 08:40", "Ravi Kumar", "police statement dene jaana hai aaj"),
        ("05/12/2025, 08:41", "Aman Verma", "main saath chalu?"),
        ("05/12/2025, 08:45", "Ravi Kumar", "nahi, theek hai"),
    ]
    lines = [("Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them.", "")]
    for m in msgs:
        ts, who, text = m[0], m[1], m[2]
        tag = m[3] if len(m) > 3 else ""
        lines.append((f"{ts} - {who}: {text}", tag))
    return lines


# ---------------------------------------------------------------- statements and claims
# Each statement is built from fragments; claim fragments carry their answer-key entry,
# so every quote is an exact substring and char offsets are computed, never typed.
MANAGER = [
    "Statement of Sunil Mehta, Operations Manager, Saanvi Logistics Pvt Ltd, recorded on 5 December 2025.\n\n",
    "On the night of 3 December, confidential vendor payment files were taken from the finance computer PC-14. ",
    ("M1", "Ravi was the only person with access to PC-14 that night"), ". ",
    ("M3", "Ravi's account was used to log in to PC-14 at about 10:10 pm"), ". ",
    ("M2", "The files were copied around 22:15"), ". ",
    ("M4", "Ravi copied the files himself"), ". ",
    "I believe he did it for money. ",
    ("M5", "His friend Aman paid him that same night"), ". ",
    ("M6", "Aman transferred him Rs 20,000"), ". ",
    ("M7", "Ravi has been asking colleagues for money for months"), ". ",
    "I want this matter investigated.\n",
]
RAVI = [
    "Bayan: Ravi Kumar, Accounts Executive, Saanvi Logistics, 5 December 2025.\n\n",
    ("R1", "Main 9:50 pe office se nikal gaya tha"), ". ",
    ("R2", "9:55 tak main Sharma Dhaba pahunch gaya tha"), ". ",
    ("R4", "Dhaba pe maine 340 rupaye UPI se pay kiye, kareeb 10:20 baje"), ". ",
    ("R3", "Maine us raat PC-14 pe login nahi kiya"), ". ",
    ("R6", "Mera password team ki shared sheet mein likha hua tha"), ". ",
    ("R5", "Aman ne 4 December ko mere 15,000 rupaye wapas kiye the"), ", woh udhaar tha. ",
    "Main nirdosh hoon.\n",
]
GUARD = [
    "बयान: रमेश यादव, सुरक्षा गार्ड, सानवी लॉजिस्टिक्स, 5 दिसंबर 2025।\n\n",
    ("G1", "रवि साहब रात करीब 9:50 बजे ऑफिस से बाहर निकले"), "। ",
    ("G2", "करीब 10:30 बजे एक विज़िटर आया"), "। ",
    ("G3", "मैंने उसे विज़िटर कार्ड V-03 दिया"), "। ",
    ("G4", "विज़िटर ने रजिस्टर में अपना नाम लिखा"), "। ",
    ("G5", "दस बजे के बाद कोई और कर्मचारी ऑफिस नहीं आया"), "। ",
    "मुझे लगता है कि वह विज़िटर किसी से मिलने आया था।\n",
]
STATEMENTS = {
    "manager": {"file": "manager.txt", "speaker": "Sunil Mehta", "role": "complainant", "language": "en", "parts": MANAGER},
    "ravi": {"file": "ravi.txt", "speaker": "Ravi Kumar", "role": "suspect", "language": "hi-Latn", "parts": RAVI},
    "guard": {"file": "guard.txt", "speaker": "Ramesh Yadav", "role": "witness", "language": "hi", "parts": GUARD},
}


def build_statement(parts: list) -> tuple[str, dict[str, tuple[int, int, str]]]:
    text, spans = "", {}
    for p in parts:
        if isinstance(p, tuple):
            cid, quote = p
            spans[cid] = (len(text), len(text) + len(quote), quote)
            text += quote
        else:
            text += p
    return text, spans


# ---------------------------------------------------------------- CCTV stills
def make_still(path: Path, cam: str, label: str, overlay: str, rng: random.Random, blurry: bool = False) -> None:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    w, h = 640, 360
    img = Image.new("RGB", (w, h), (92, 96, 104))
    d = ImageDraw.Draw(img)
    d.polygon([(0, h), (w, h), (w * 0.7, h * 0.45), (w * 0.3, h * 0.45)], fill=(120, 116, 108))  # floor
    if cam == "CAM-A":
        d.rectangle([250, 70, 390, 230], fill=(60, 64, 70), outline=(30, 30, 30), width=3)  # entrance door
        d.rectangle([60, 200, 190, 250], fill=(140, 110, 80))  # guard desk
    else:
        for x in (120, 470):
            d.rectangle([x, 90, x + 50, 220], fill=(70, 74, 82))  # corridor doors
    # faceless figure: plain head disc, body block, visitor lanyard
    fx = 300 if cam == "CAM-A" else 330
    d.ellipse([fx, 150, fx + 34, 184], fill=(50, 50, 55))
    d.rectangle([fx - 8, 186, fx + 42, 290], fill=(45, 60, 90))
    d.rectangle([fx + 12, 200, fx + 22, 214], fill=(230, 200, 40))
    for _ in range(1800):  # sensor noise
        x, y = rng.randrange(w), rng.randrange(h)
        v = rng.randint(-25, 25)
        r, g, b = img.getpixel((x, y))
        img.putpixel((x, y), (max(0, min(255, r + v)),) * 3)
    font = ImageFont.load_default(size=22)
    d.rectangle([0, 0, w, 34], fill=(0, 0, 0))
    d.text((10, 5), f"{cam} {label}", fill=(255, 255, 255), font=font)
    d.text((w - 250, 5), overlay, fill=(255, 255, 255), font=font)
    if blurry:
        img = img.filter(ImageFilter.GaussianBlur(radius=4.5))
        img = img.resize((w // 3, h // 3)).resize((w, h))
    img.save(path, format="PNG", optimize=False)


# ---------------------------------------------------------------- writer
def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(header)
    wr.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8", newline="")


def main() -> None:
    rng = random.Random(SEED)
    (ART / "cctv").mkdir(parents=True, exist_ok=True)
    STM.mkdir(parents=True, exist_ok=True)
    ref: dict[str, str] = {}  # planted tag -> "file#rowN" / "file#lineN"

    # door log
    drows = door_rows(rng)
    write_csv(ART / "door_log.csv", ["time", "badge_id", "holder", "door", "direction"],
              [[r.t.strftime(IST_FMT), r.badge, r.holder, r.door, r.direction] for r in drows])
    for i, r in enumerate(drows, start=1):
        if r.tag:
            ref[r.tag] = f"door_log.csv#row{i}"
        if r.badge == "E-1047" and r.t.date() == CASE_DATE and r.direction == "IN" and r.t.hour < 10:
            ref["ravi_in"] = f"door_log.csv#row{i}"

    # PC-14 log
    prows = pc_rows(rng)
    write_csv(ART / "pc14_events.csv", ["time_utc", "event_id", "user", "detail"],
              [[r[0].strftime("%Y-%m-%dT%H:%M:%SZ"), r[1], r[2], r[3]] for r in prows])
    copy_refs = []
    for i, r in enumerate(prows, start=1):
        if r[4] in ("logon", "usb"):
            ref[r[4]] = f"pc14_events.csv#row{i}"
        if r[4] == "copy":
            copy_refs.append(f"pc14_events.csv#row{i}")
    ref["copy_first"], ref["copy_last"] = copy_refs[0], copy_refs[-1]

    # UPI
    urows = upi_rows(rng)
    write_csv(ART / "upi_ravi.csv", ["time", "direction", "counterparty", "amount", "note", "ref"],
              [[r[0].strftime(IST_FMT), r[1], r[2], r[3], r[4], f"UPI{530000000000 + n * 7919:012d}"]
               for n, r in enumerate(urows, start=1)])
    for i, r in enumerate(urows, start=1):
        if r[5]:
            ref[r[5]] = f"upi_ravi.csv#row{i}"

    # WhatsApp
    lines = chat_lines()
    (ART / "whatsapp_ravi_aman.txt").write_text("\n".join(l for l, _ in lines) + "\n", encoding="utf-8", newline="")
    for i, (_, tag) in enumerate(lines, start=1):
        if tag:
            ref[tag] = f"whatsapp_ravi_aman.txt#line{i}"

    # CCTV stills (overlay = what the camera clock showed; CAM-B runs 7 min slow)
    make_still(ART / "cctv" / "cam_a_2206.png", "CAM-A", "ENTRANCE", "03-12-2025 22:06:20", rng)
    make_still(ART / "cctv" / "cam_b_2205.png", "CAM-B", "CORRIDOR", "03-12-2025 22:05:40", rng)
    make_still(ART / "cctv" / "cam_b_blurry.png", "CAM-B", "CORRIDOR", "03-12-2025 22:24:05", rng, blurry=True)

    calibration = {
        "records": [
            {"source_id": "CAM-A", "offset_s": 0, "uncertainty_s": 60,
             "method": "CAM-A overlay compared with door log badge E-1012 IN at 08:58 on 3 Dec; difference under 1 minute",
             "reference_artifact": "door_log.csv", "valid_from": "2025-12-01T00:00:00+05:30", "valid_to": "2025-12-10T23:59:59+05:30"},
            {"source_id": "CAM-B", "offset_s": 420, "uncertainty_s": 60,
             "method": "Investigator photographed CAM-B monitor beside a phone showing network time on 5 Dec; CAM-B 7 min slow",
             "reference_artifact": "calibration photo (not in demo pack)", "valid_from": "2025-12-01T00:00:00+05:30", "valid_to": "2025-12-10T23:59:59+05:30"},
        ],
        "note": "Synthetic calibration record for the UBHAYA demo.",
    }
    (OUT / "calibration.json").write_text(json.dumps(calibration, indent=2) + "\n", encoding="utf-8")

    site_config = {
        "case_date": CASE_DATE.isoformat(),
        "timezone": "Asia/Kolkata",
        "places": {
            "office": {"label": "Saanvi Logistics office", "devices": ["PC-14", "MAIN-ENTRANCE", "STAFF-SIDE", "CAM-A", "CAM-B"]},
            "dhaba": {"label": "Sharma Dhaba (highway)", "merchants": ["Sharma Dhaba"], "keywords": ["dhaba"]},
        },
        "required_orders": [
            {"id": "entrance_before_corridor", "first": "CAM-A", "then": "CAM-B",
             "note": "A visitor is seen at the entrance camera before the corridor camera"},
            {"id": "badge_alternates", "kind": "badge_in_out_alternate",
             "note": "A badge should go IN then OUT before it goes IN again (anti-passback)"},
        ],
        "min_travel_s": [{"from": "office", "to": "dhaba", "seconds": 720}],
        "duplicate_window_s": 2,
        "actors": {"Ravi Kumar": {"accounts": ["ravi.k"], "badges": ["E-1047"], "upi": ["upi_ravi.csv"], "chat_name": "Ravi Kumar"}},
        "note": "Synthetic site configuration for the UBHAYA demo. Travel time is a demo assumption.",
    }
    (OUT / "site_config.json").write_text(json.dumps(site_config, indent=2) + "\n", encoding="utf-8")

    # statements
    meta, claim_spans = [], {}
    for key, s in STATEMENTS.items():
        text, spans = build_statement(s["parts"])
        (STM / s["file"]).write_text(text, encoding="utf-8", newline="")
        meta.append({"file": s["file"], "speaker": s["speaker"], "role": s["role"], "language": s["language"]})
        for cid, (a, b, q) in spans.items():
            assert text[a:b] == q
            claim_spans[cid] = (key, a, b, q)
    (STM / "statements.json").write_text(json.dumps({"statements": meta}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # answer key
    def c(cid, verdict, rules, evidence, ctype, strength=None, note=""):
        st, a, b, q = claim_spans[cid]
        return {"id": cid, "statement": st, "quote": q, "char_start": a, "char_end": b, "type": ctype,
                "expected_verdict": verdict, "expected_rule": rules[0] if rules else None, "expected_rules": rules,
                "expected_strength": strength, "evidence": evidence, "note": note}

    claims = [
        c("M1", "contradicted", ["R3"], [ref["v03_in"]], "presence", "direct", "Exclusive claim; V-03 enters at 22:06:10 while Ravi's account is active"),
        c("M2", "supported", [], [ref["usb"], ref["copy_first"], ref["copy_last"]], "time", "direct", "PC log is UTC: 16:44Z = 22:14 IST"),
        c("M3", "supported", [], [ref["logon"]], "action", "direct", "Account-level claim; 16:43:21Z = 22:13:21 IST"),
        c("M4", "uncertain", ["R4"], [ref["logon"], ref["dhaba"], ref["dhaba_chat"]], "action", None, "Login names ravi.k (direct) but Ravi's phone pays at the dhaba 7 min later; evidence points both ways"),
        c("M5", "contradicted", ["R2"], [ref["aman_return"]], "time", "direct", "Aman's payment is on 4 Dec 11:42, not the night of 3 Dec"),
        c("M6", "contradicted", ["R5"], [ref["aman_return"]], "amount", "direct", "Bank shows Rs 15,000, not Rs 20,000"),
        c("M7", "no_evidence", [], [], "action", None, "Nothing in the case covers this"),
        c("R1", "supported", [], [ref["ravi_out"]], "time", "direct", "Badge OUT 21:52:07 inside 9:50 +/- 5 min"),
        c("R2", "contradicted", ["R4", "R2"], [ref["ravi_out"], ref["dhaba_chat"]], "presence", "direct", "Badge OUT 21:52 at office + 12 min travel makes 9:55 at the dhaba impossible; his own chat says arrived 22:07"),
        c("R3", "uncertain", ["R3", "R4"], [ref["logon"], ref["dhaba"]], "absence", None, "Account ravi.k logs on at 22:13 but Ravi's UPI pays at the dhaba at 22:20"),
        c("R4", "supported", [], [ref["dhaba"]], "presence", "indirect", "UPI Rs 340 Sharma Dhaba 22:20:31 places his phone, not him, at the dhaba: supported, not proven"),
        c("R5", "supported", [], [ref["aman_return"], ref["aman_paid_chat"]], "amount", "direct", "UPI CR Rs 15,000 from Aman on 4 Dec"),
        c("R6", "no_evidence", [], [], "relationship", None, "Password sheet not in the case"),
        c("G1", "supported", [], [ref["ravi_out"]], "time", "direct", "Around 9:50 = 21:35-22:05; badge OUT 21:52:07"),
        c("G2", "contradicted", ["R2"], [ref["v03_in"]], "time", "direct", "Around 10:30 = 22:15-22:45; V-03 IN 22:06:10"),
        c("G3", "supported", [], [ref["v03_in"]], "identity", "direct", "Door log shows V-03 in use that night"),
        c("G4", "no_evidence", [], [], "action", None, "Visitor register not collected; top evidence request"),
        c("G5", "supported", [], [ref["ravi_out"]], "absence", "direct", "No employee badge IN after 22:00 on 3 Dec"),
    ]
    assert len(claims) == 18
    answers = {
        "case": "PC-14 synthetic demo",
        "generator": "data/make_demo_case.py",
        "seed": SEED,
        "claims": claims,
        "planted": {
            "real_contradictions": ["M1", "M5", "M6", "R2", "G2"],
            "harmless_conflicts": [
                {"id": "CAM-B order", "rule": "R1", "items": ["cctv/cam_a_2206.png", "cctv/cam_b_2205.png"],
                 "fixed_by": "calibration: CAM-B +420 s, so 22:05:40 becomes 22:12:40 +/- 60 s"},
                {"id": "PC log UTC", "items": [ref["usb"]], "fixed_by": "UTC to IST: 16:44:05Z = 22:14:05 IST"},
            ],
            "two_places_conflict": {"rule": "R4", "items": [ref["logon"], ref["dhaba"]],
                                     "note": "ravi.k logs on at the office at 22:13:21; Ravi's UPI pays at the dhaba at 22:20:31; travel is at least 12 min"},
            "false_alarm": ref["v03_double"],
            "false_alarm_note": "V-03 IN twice 42 s apart without an OUT: a double tap. R6 (2 s) does not merge them; the reviewer rejects it.",
            "known_failure": "cctv/cam_b_blurry.png",
            "known_failure_truth": {"overlay": "03-12-2025 22:24:05", "corrected": "2025-12-03T22:31:05+05:30"},
            "cctv_truth": {"cctv/cam_a_2206.png": "03-12-2025 22:06:20", "cctv/cam_b_2205.png": "03-12-2025 22:05:40"},
        },
        "expected_requests_top3": ["visitor_register", "dhaba_cctv", "telecom_location"],
        "refs": ref,
    }
    (OUT / "answers.json").write_text(json.dumps(answers, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"door_log.csv        {len(drows)} rows")
    print(f"pc14_events.csv     {len(prows)} rows")
    print(f"upi_ravi.csv        {len(urows)} rows")
    print(f"whatsapp export     {len(lines)} lines")
    print("cctv stills         3")
    print(f"claims labelled     {len(claims)}")
    for k in sorted(ref):
        print(f"  {k:16s} {ref[k]}")


if __name__ == "__main__":
    main()

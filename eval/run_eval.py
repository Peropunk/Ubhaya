"""Score a fresh synthetic case. Only this evaluation step reads the answer key."""
import json
import os
import sys
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.analysis import analyze, case_claims, requests
from app.config import DEMO_CASE_DIR
from app.db import connect, fetch_all
from app.demo import load_demo


def evaluate():
    with connect() as conn:
        case = load_demo(conn)["case"]
        sources = fetch_all(conn, "SELECT s.id,a.filename FROM statements s JOIN artifacts a ON s.artifact_id=a.id WHERE s.case_id=?", (case["id"],))
    analyze(case["id"])
    speakers = {s["id"]: Path(s["filename"]).stem for s in sources}
    actual = {(speakers[c["statement_id"]], c["char_start"], c["char_end"]): c for c in case_claims(case["id"])}
    key = json.loads((DEMO_CASE_DIR / "answers.json").read_text(encoding="utf-8"))
    expected = {(c["statement"], c["char_start"], c["char_end"]): c for c in key["claims"]}
    common = actual.keys() & expected.keys()
    misses = [expected[k]["id"] for k in expected.keys() - common]
    errors = [expected[k]["id"] for k in common if actual[k]["finding"]["verdict"] != expected[k]["expected_verdict"]]
    contradictions = {k for k,c in actual.items() if c["finding"]["verdict"] == "contradicted"}
    planted = {k for k,c in expected.items() if c["expected_verdict"] == "contradicted"}
    return dict(claim_sources=dict(Counter(c["source"] for c in actual.values())), found=len(common), missed=sorted(misses),
                extra=len(actual.keys()-common), correct_verdicts=len(common)-len(errors), expected=len(expected),
                incorrect_verdicts=sorted(errors), contradictions_found=len(contradictions & planted),
                false_contradictions=len(contradictions-planted), top_requests=[r["catalogue_id"] for r in requests(case["id"])[:3]])


def benchmark(models):
    from time import monotonic
    from app.extract import extract_claims
    speakers = json.loads((DEMO_CASE_DIR/"statements/statements.json").read_text(encoding="utf-8"))["statements"]
    key = json.loads((DEMO_CASE_DIR/"answers.json").read_text(encoding="utf-8"))["claims"]
    results = []
    for model in models:
        for speaker in speakers:
            statement = dict(speaker, text=(DEMO_CASE_DIR/"statements"/speaker["file"]).read_text(encoding="utf-8"))
            start = monotonic()
            row = dict(model=model, statement=speaker["file"])
            try:
                guesses = extract_claims(statement, "2025-12-03", model=model, timeout=30)
                expected = {c["quote"] for c in key if c["statement"] == Path(speaker["file"]).stem}
                quotes = {c["quote"] for c in guesses}
                row.update(found=len(expected & quotes), extra=len(quotes-expected), missed=len(expected-quotes))
            except (ValueError, ConnectionError) as exc:
                row["error"] = str(exc)
            row["seconds"] = round(monotonic()-start, 2)
            results.append(row)
    return results


if __name__ == "__main__":
    with TemporaryDirectory() as directory:
        os.environ["UBHAYA_DATA_DIR"] = directory
        print(json.dumps(benchmark(sys.argv[2:]) if sys.argv[1:2] == ["--benchmark"] else evaluate(), indent=2))

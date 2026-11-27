"""Measure whether a shorter local-model prompt meets the latency gate."""
import argparse
import json
from pathlib import Path
from time import monotonic
from urllib.error import URLError
from urllib.request import Request, urlopen

DEMO = Path(__file__).resolve().parents[1] / "data" / "demo_case"
PROMPT = (
    "Copy each factual claim verbatim from the statement. Split the claims. "
    "Skip introductions and opinions. Return a JSON object with a quotes array."
)


def benchmark(model):
    expected = json.loads((DEMO / "answers.json").read_text(encoding="utf-8"))["claims"]
    metadata = json.loads((DEMO / "statements/statements.json").read_text(encoding="utf-8"))
    for statement in metadata["statements"]:
        filename = statement["file"]
        source = (DEMO / "statements" / filename).read_text(encoding="utf-8")
        body = {
            "model": model, "prompt": PROMPT + "\n" + source,
            "stream": False, "format": "json", "keep_alive": "10m",
            "options": {"temperature": 0, "num_ctx": 512, "num_thread": 4, "num_predict": 240},
        }
        request = Request("http://127.0.0.1:11434/api/generate", method="POST",
                          headers={"Content-Type": "application/json"}, data=json.dumps(body).encode())
        row = dict(model=model, statement=filename, method="shortened exact-quote prompt with capped generation")
        started = monotonic()
        try:
            with urlopen(request, timeout=30) as response:
                reply = json.loads(json.load(response)["response"])
            returned = reply["quotes"]
            if not isinstance(returned, list) or any(not isinstance(quote, str) for quote in returned):
                raise ValueError("Invalid quote array")
            gold = {claim["quote"] for claim in expected if claim["statement"] == Path(filename).stem}
            found = {quote for quote in returned if quote and quote in source}
            row.update(matched=len(gold & found), expected=len(gold), unmatched=len(found - gold),
                       invalid=sum(not quote or quote not in source for quote in returned))
        except (TimeoutError, URLError, ValueError, KeyError, TypeError) as exc:
            row["error"] = str(exc)
        row["seconds"] = round(monotonic() - started, 2)
        yield row


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5:0.5b")
    print(json.dumps(list(benchmark(parser.parse_args().model)), indent=2))

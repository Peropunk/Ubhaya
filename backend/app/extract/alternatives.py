"""Bounded local model selection for reviewer hypotheses."""
import json
import os
from urllib.error import URLError
from urllib.request import urlopen, Request


def options(events):
    result = []
    for e in events:
        if e["action"] in ("logon", "file_copy"):
            text = "Check whether another operator used the same account."
        elif e["action"].startswith("upi_"):
            text = "Check who controlled the payment device at the recorded time."
        elif e["action"].startswith("badge_"):
            text = "Check who held the badge when the reader registered it."
        else:
            text = "Check the source clock against an independent time record."
        if all(item["text"] != text for item in result):
            result.append({"text":text, "event_ids":[e["id"]]})
    return result[:3]


def select_alternatives(events):
    choices = options(events)
    if not choices:
        return []
    prompt = "Select applicable reviewer hypotheses by zero-based index. Return JSON with indices. " + json.dumps(choices)
    body = {"model": os.getenv("UBHAYA_MODEL","gemma:2b"),"prompt":prompt,"stream":False,"format":"json",
            "options":{"temperature":0,"num_predict":35}}
    request = Request("http://127.0.0.1:11434/api/generate", data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            indices = json.loads(json.load(response)["response"])["indices"]
        if not isinstance(indices,list) or not indices or any(type(i) is not int or not 0 <= i < len(choices) for i in indices):
            raise ValueError("Invalid selection")
        return [choices[i] for i in dict.fromkeys(indices)]
    except (URLError, TimeoutError, KeyError, ValueError) as exc:
        raise ValueError("Local model could not select a grounded hypothesis") from exc

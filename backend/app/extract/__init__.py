"""Validated claim extraction through the laptop's local Ollama service."""
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field, ValidationError

from ..config import REPO_ROOT
from ..db import fetch_all, fetch_one, insert, next_id
from ..intake import audit
from ..intake.service import NotFound
from ..models import ClaimType

PROMPT_VERSION = "claims-v1"


class ExtractedClaim(BaseModel):
    quote: str = Field(min_length=1)
    type: ClaimType
    subject: str | None = None
    action: str | None = None
    place: str | None = None
    value: str | None = None
    time_expr: str | None = None
    negated: bool = False
    exclusive: bool = False


class Extraction(BaseModel):
    claims: list[ExtractedClaim]


def extract_claims(statement: dict, case_date: str | None, *, model: str | None = None, timeout: int = 120) -> list[dict]:
    prompt = (Path(__file__).parent / "prompts" / f"{PROMPT_VERSION}.txt").read_text(encoding="utf-8")
    context = {key: statement[key] for key in ("text", "speaker", "role", "language")}
    context["case_date"] = case_date
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": json.dumps(context, ensure_ascii=False)}]
    for attempt in range(2):
        body = {"model": model or os.getenv("UBHAYA_MODEL", "gemma:2b"), "stream": False, "format": Extraction.model_json_schema(),
                "messages": messages, "options": {"temperature": 0}}
        request = Request("http://127.0.0.1:11434/api/chat", data=json.dumps(body).encode(),
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=timeout) as response:
                reply = json.load(response)["message"]["content"]
        except (URLError, TimeoutError) as exc:
            raise ConnectionError("Local Ollama extraction unavailable") from exc
        try:
            claims = []
            seen = set()
            for item in Extraction.model_validate_json(reply).claims:
                start = statement["text"].find(item.quote)
                if start < 0 or statement["text"].find(item.quote, start + 1) >= 0:
                    raise ValueError("Each quote must occur exactly once in the statement.")
                if item.quote in seen:
                    raise ValueError("Each claim may appear only once.")
                if item.time_expr and item.time_expr not in statement["text"]:
                    raise ValueError("Copy the time expression verbatim.")
                seen.add(item.quote)
                claims.append(dict(item.model_dump(), char_start=start, char_end=start + len(item.quote)))
            return claims
        except (ValidationError, ValueError) as exc:
            if attempt:
                raise ValueError("Statement needs manual claims after two invalid model responses.") from exc
            messages.extend([{"role": "assistant", "content": reply}, {"role": "user", "content": str(exc)}])


def extract_statement(conn: sqlite3.Connection, case_id: str, statement_id: str) -> list[dict]:
    statement = fetch_one(conn, "SELECT * FROM statements WHERE case_id=? AND id=?", (case_id, statement_id))
    if statement is None:
        raise NotFound("Statement does not exist in this case")
    query = "SELECT * FROM claims WHERE statement_id=? ORDER BY char_start"
    existing = fetch_all(conn, query, (statement_id,))
    if existing:
        return existing
    config = fetch_one(conn, "SELECT path FROM artifacts WHERE case_id=? AND type='site_config' ORDER BY id LIMIT 1", (case_id,))
    date = json.loads(Path(config["path"]).read_text(encoding="utf-8")).get("case_date") if config else None
    digest = hashlib.sha256(statement["text"].encode()).hexdigest()
    cache = REPO_ROOT / "cache" / f"{digest}.json"
    source = "llm"
    if os.getenv("UBHAYA_EXTRACT_MODE", "cached") == "cached" and cache.exists():
        result = json.loads(cache.read_text(encoding="utf-8"))
        for row in result:
            ExtractedClaim.model_validate(row)
            if statement["text"][row["char_start"]:row["char_end"]] != row["quote"]:
                raise ValueError("Cached quote does not match its source")
        source = "cached"
    else:
        result = extract_claims(statement, date)
    conn.execute("BEGIN IMMEDIATE")
    existing = fetch_all(conn, query, (statement_id,))
    if existing:
        return existing
    for claim in result:
        insert(conn, "claims", dict(claim, id=next_id(conn, "CL"), statement_id=statement_id,
                                    source=source, prompt_version=PROMPT_VERSION))
    audit.append(conn, case_id, "api", "claims_extracted", {"statement_id": statement_id, "count": len(result), "source": source,
                                                            "prompt_version": PROMPT_VERSION})
    return fetch_all(conn, query, (statement_id,))

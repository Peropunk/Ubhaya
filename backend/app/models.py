"""Pydantic models for every entity in docs/SPEC.md. Storage lives in db.py."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

ArtifactType = Literal[
    "door_log", "pc_event_log", "bank_upi", "chat_export", "cctv_still",
    "statement", "calibration", "site_config",
]
EventAction = Literal[
    "badge_in", "badge_out", "logon", "logoff", "usb_connected", "usb_removed",
    "file_copy", "file_access", "upi_debit", "upi_credit", "chat_message", "camera_sighting",
]
ClaimType = Literal["presence", "absence", "time", "action", "amount", "identity", "relationship"]
Verdict = Literal["supported", "contradicted", "uncertain", "no_evidence"]
Strength = Literal["direct", "indirect"]
Certainty = Literal["certain", "possible"]
Role = Literal["complainant", "suspect", "witness"]


class CaseCreate(BaseModel):
    title: str
    scope: Optional[str] = None
    synthetic: bool = False


class Case(BaseModel):
    id: str
    title: str
    timezone: str
    scope: Optional[str] = None
    created_at: str
    synthetic: bool
    artifact_count: Optional[int] = None
    statement_count: Optional[int] = None
    event_count: Optional[int] = None


class Artifact(BaseModel):
    id: str
    case_id: str
    filename: str
    sha256: str
    size: int
    type: ArtifactType
    source: Optional[str] = None
    acquired_at: Optional[str] = None
    path: str
    meta: dict[str, Any] = Field(default_factory=dict)
    registered_at: str


class VerifyResult(BaseModel):
    artifact_id: str
    expected: str
    actual: Optional[str]
    ok: bool


class Event(BaseModel):
    id: str
    case_id: str
    artifact_id: str
    locator: str
    actor: Optional[str] = None
    action: EventAction
    place: Optional[str] = None
    original_time: str
    original_tz: str
    t_min: Optional[str] = None
    t_max: Optional[str] = None
    confidence: float = 1.0
    fields: dict[str, Any] = Field(default_factory=dict)
    raw: Optional[str] = None


class Calibration(BaseModel):
    source_id: str
    offset_s: int
    uncertainty_s: int
    method: Optional[str] = None
    reference_artifact: Optional[str] = None
    valid_from: str
    valid_to: str


class Statement(BaseModel):
    id: str
    case_id: str
    artifact_id: str
    speaker: str
    role: Role
    language: str
    text: str


class Claim(BaseModel):
    id: str
    statement_id: str
    quote: str
    char_start: int
    char_end: int
    type: ClaimType
    subject: Optional[str] = None
    action: Optional[str] = None
    place: Optional[str] = None
    value: Optional[str] = None
    time_expr: Optional[str] = None
    t_min: Optional[str] = None
    t_max: Optional[str] = None
    negated: bool = False
    exclusive: bool = False
    prompt_version: Optional[str] = None
    source: Literal["llm", "cached", "manual"] = "llm"


class Finding(BaseModel):
    id: str
    claim_id: str
    verdict: Verdict
    strength: Optional[Strength] = None
    event_ids: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    certainty: Optional[Certainty] = None
    explanation: Optional[str] = None
    ai_generated: bool = False


class Alternative(BaseModel):
    id: str
    finding_id: str
    text: str
    event_ids: list[str] = Field(default_factory=list)
    ai_generated: bool = True


class EvidenceRequest(BaseModel):
    id: str
    case_id: str
    claim_ids: list[str] = Field(default_factory=list)
    catalogue_id: str
    score: float
    score_parts: dict[str, float] = Field(default_factory=dict)
    draft_text: Optional[str] = None


class ReviewCreate(BaseModel):
    target_id: str
    reviewer: str
    decision: Literal["accept", "reject", "edit"]
    reason: str
    edit: Optional[dict[str, Any]] = None


class Review(ReviewCreate):
    id: str
    time: str


class AuditEntry(BaseModel):
    case_id: str
    seq: int
    time: str
    actor: str
    action: str
    payload: dict[str, Any]
    payload_hash: str
    prev_hash: str
    entry_hash: str


class AuditVerify(BaseModel):
    ok: bool
    entries: int
    broken_at: Optional[int] = None
    reason: Optional[str] = None

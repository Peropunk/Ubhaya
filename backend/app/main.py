"""FastAPI app and routes. Contract: docs/SPEC.md (frozen v1)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import models
from .config import FRONTEND_DIR
from .db import connect, fetch_all
from .intake import audit, service
from .intake.service import NotFound
from .parsers import list_events

app = FastAPI(title="UBHAYA", version="0.1.0",
              description="Offline evidence-versus-statement checker. Synthetic demo data only.")

MEDIA_TYPES = {".csv": "text/csv; charset=utf-8", ".txt": "text/plain; charset=utf-8",
               ".json": "application/json", ".png": "image/png"}


def _not_found(exc: NotFound) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/cases", response_model=models.Case, status_code=201)
def create_case(body: models.CaseCreate):
    with connect() as conn:
        return service.create_case(conn, body.title, body.scope, body.synthetic, actor="api")


@app.get("/cases", response_model=list[models.Case])
def list_cases():
    with connect() as conn:
        return service.list_cases(conn)


@app.get("/cases/{case_id}", response_model=models.Case)
def get_case(case_id: str):
    with connect() as conn:
        try:
            return service.get_case(conn, case_id)
        except NotFound as exc:
            raise _not_found(exc)


@app.post("/cases/{case_id}/artifacts", response_model=models.Artifact, status_code=201)
def upload_artifact(case_id: str, file: UploadFile = File(...), type: models.ArtifactType = Form(...),
                    source: str = Form(...), acquired_at: Optional[str] = Form(None), meta: Optional[str] = Form(None)):
    try:
        meta_obj = json.loads(meta) if meta else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="meta must be a JSON object")
    with connect() as conn:
        try:
            return service.register_artifact(conn, case_id, filename=file.filename or "upload", type=type,
                                             source=source, acquired_at=acquired_at, meta=meta_obj,
                                             stream=file.file, actor="api")
        except NotFound as exc:
            raise _not_found(exc)


@app.get("/cases/{case_id}/artifacts", response_model=list[models.Artifact])
def list_artifacts(case_id: str):
    with connect() as conn:
        try:
            return service.list_artifacts(conn, case_id)
        except NotFound as exc:
            raise _not_found(exc)


@app.get("/artifacts/{artifact_id}", response_model=models.Artifact)
def get_artifact(artifact_id: str):
    with connect() as conn:
        try:
            return service.get_artifact(conn, artifact_id)
        except NotFound as exc:
            raise _not_found(exc)


@app.get("/artifacts/{artifact_id}/content")
def artifact_content(artifact_id: str):
    with connect() as conn:
        try:
            art = service.get_artifact(conn, artifact_id)
        except NotFound as exc:
            raise _not_found(exc)
    suffix = Path(art["filename"]).suffix.lower()
    return FileResponse(art["path"], media_type=MEDIA_TYPES.get(suffix, "application/octet-stream"))


@app.get("/artifacts/{artifact_id}/verify", response_model=models.VerifyResult)
def verify_artifact(artifact_id: str):
    with connect() as conn:
        try:
            return service.verify_artifact(conn, artifact_id, actor="api")
        except NotFound as exc:
            raise _not_found(exc)


@app.get("/cases/{case_id}/statements", response_model=list[models.Statement])
def list_statements(case_id: str):
    with connect() as conn:
        return fetch_all(conn, "SELECT * FROM statements WHERE case_id = ? ORDER BY id", (case_id,))


@app.get("/cases/{case_id}/events", response_model=list[models.Event])
def get_events(case_id: str, artifact_id: Optional[str] = None):
    with connect() as conn:
        return list_events(conn, case_id, artifact_id)


@app.get("/cases/{case_id}/audit", response_model=list[models.AuditEntry])
def get_audit(case_id: str):
    with connect() as conn:
        return audit.entries(conn, case_id)


@app.get("/cases/{case_id}/audit/verify", response_model=models.AuditVerify)
def verify_audit(case_id: str):
    with connect() as conn:
        return audit.verify(conn, case_id)


# Interface (static, no build step, no CDN): served at /ui
if FRONTEND_DIR.exists():
    app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="ui")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui/")

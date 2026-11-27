import os
import stat
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parents[1] / "data" / "demo_case"


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    """Every test gets its own empty database and evidence store."""
    d = tmp_path / "ubhaya-data"
    monkeypatch.setenv("UBHAYA_DATA_DIR", str(d))
    yield d
    # read-only store files must be made writable again so the temp dir can be removed
    for p in d.rglob("*"):
        if p.is_file():
            os.chmod(p, stat.S_IWRITE | stat.S_IREAD)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)


@pytest.fixture
def demo_case():
    from app.db import connect
    from app.demo import load_demo

    with connect() as conn:
        return load_demo(conn)

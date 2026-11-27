"""Runtime settings. Read from the environment on every call so tests can point
UBHAYA_DATA_DIR at a temporary folder."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_CASE_DIR = REPO_ROOT / "data" / "demo_case"
FRONTEND_DIR = REPO_ROOT / "frontend"
CASE_TIMEZONE = "Asia/Kolkata"


@dataclass(frozen=True)
class Settings:
    data_dir: Path

    @property
    def db_path(self) -> Path:
        return self.data_dir / "ubhaya.db"

    @property
    def store_dir(self) -> Path:
        return self.data_dir / "store"


def get_settings() -> Settings:
    data_dir = Path(os.environ.get("UBHAYA_DATA_DIR", REPO_ROOT / "var"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return Settings(data_dir=data_dir)

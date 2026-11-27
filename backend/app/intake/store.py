"""Content-addressed, write-once evidence store (P1.2).

Files land at <data_dir>/store/<sha[0:2]>/<sha256> and are made read-only.
Originals outside the store are only ever read, never written."""
from __future__ import annotations

import hashlib
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import BinaryIO

from ..config import get_settings

CHUNK = 1024 * 1024


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def store_path(sha256: str) -> Path:
    return get_settings().store_dir / sha256[:2] / sha256


def make_read_only(path: Path) -> None:
    os.chmod(path, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)


def is_read_only(path: Path) -> bool:
    return not path.stat().st_mode & stat.S_IWRITE


def put_stream(stream: BinaryIO) -> tuple[str, int, Path]:
    """Copy a stream into the store. Returns (sha256, size, stored path)."""
    store = get_settings().store_dir
    store.mkdir(parents=True, exist_ok=True)
    h, size = hashlib.sha256(), 0
    fd, tmp_name = tempfile.mkstemp(dir=store, prefix=".incoming-")
    try:
        with os.fdopen(fd, "wb") as tmp:
            for block in iter(lambda: stream.read(CHUNK), b""):
                h.update(block)
                size += len(block)
                tmp.write(block)
        digest = h.hexdigest()
        dest = store_path(digest)
        if dest.exists():
            # Same content already stored: the stored copy must still match.
            if sha256_file(dest) != digest:
                raise RuntimeError(f"Stored copy {dest} no longer matches its hash")
            os.remove(tmp_name)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(tmp_name, dest)
            make_read_only(dest)
        return digest, size, dest
    except BaseException:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise


def put_file(path: Path) -> tuple[str, int, Path]:
    with open(path, "rb") as f:  # read-only open: the original is never written
        return put_stream(f)

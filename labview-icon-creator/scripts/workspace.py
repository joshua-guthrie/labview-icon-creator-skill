"""Owned temporary directories with inherited Windows sandbox access.

Python 3.14's mode-0700 directory ACL can exclude the managed sandbox identity
even under a writable parent. On Windows, inherit that parent's access instead;
POSIX retains private mode 0700. This is a supported helper, not a monkey patch.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path


def create_work_directory(parent: str | Path | None = None, prefix: str = "labview-icons-") -> Path:
    root = Path(parent or tempfile.gettempdir()).resolve()
    root.mkdir(parents=True, exist_ok=True)
    # Keep nested staging paths below traditional Windows path-length limits.
    directory = root / (prefix + uuid.uuid4().hex[:12])
    directory.mkdir(mode=0o777 if os.name == "nt" else 0o700)
    return directory


@contextmanager
def temporary_directory(*, prefix: str = "labview-icon-", dir: str | Path | None = None):
    directory = create_work_directory(dir, prefix)
    try:
        yield str(directory)
    finally:
        shutil.rmtree(directory)

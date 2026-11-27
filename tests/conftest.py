"""Shared test setup.

The environment is set before the app modules are imported (they read it at import time). Data contributions
written by the tests go to a temporary folder, never to ./submissions.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("SUBMISSION_SECRET", "test-secret-not-used-in-production")
os.environ.setdefault("SUBMISSIONS_DIR", tempfile.mkdtemp(prefix="nsbi-test-submissions-"))


@pytest.fixture(scope="session")
def dash_app() -> Any:
    """The Dash app with all pages registered (importing app.py creates it)."""
    import app

    return app.app


@pytest.fixture
def submissions_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect saved contributions to a fresh temporary folder."""
    from components import submissions

    monkeypatch.setattr(submissions, "SUBMISSIONS_DIR", tmp_path)
    return tmp_path

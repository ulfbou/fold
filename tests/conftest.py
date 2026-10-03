"""Pytest fixtures shared across Fold test modules."""
from __future__ import annotations

from pathlib import Path

import pytest

from support import create_repository


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    return create_repository(tmp_path)

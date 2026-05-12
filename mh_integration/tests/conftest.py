"""Pytest configuration and path helpers for mh_integration tests."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def fixtures_dir() -> Path:
    """Absolute path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture()
def fixture(fixtures_dir: Path):
    """Factory fixture: returns a callable that resolves a fixture filename to an absolute Path."""
    def _get(name: str) -> Path:
        p = fixtures_dir / name
        assert p.exists(), f"Fixture not found: {p}"
        return p
    return _get

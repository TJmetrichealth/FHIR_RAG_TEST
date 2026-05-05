"""Root conftest.py — loaded by pytest before any test module.

Loads the project .env file so that GROQ_API_KEY and any other
environment variables set there are available to all tests.

This file must stay at the repository root so pytest picks it up
regardless of which subdirectory tests are collected from.
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Resolve the .env file relative to this conftest so the path is correct
# even when pytest is invoked from a different working directory.
_ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_FILE, override=False)

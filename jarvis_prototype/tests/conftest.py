"""Shared pytest fixtures for the test suite."""

import sys
from importlib import import_module
from pathlib import Path

import pytest  # pylint: disable=import-error  # type: ignore[import-not-found]

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

jarvis = import_module("jarvis")


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    monkeypatch.setattr(jarvis.config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(jarvis.config, "USERS_FILE", tmp_path / "users.json")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    jarvis.i18n.set_lang("en")


@pytest.fixture
def user():
    users: dict = {}
    return jarvis.auth.create_user(users, "Anna Maria", 25, "Kyiv", "192.168.1.5", 54321, "Strong#Pass1")

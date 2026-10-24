"""Tests for authentication behavior."""

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

auth = importlib.import_module("jarvis.auth")
config = importlib.import_module("jarvis.config")


def test_name_validation():
    assert auth.validate_name("Anna Maria") is None
    assert auth.validate_name("Олена-Марія") is None
    assert auth.validate_name("Bob3") == "name_bad"


def test_ip_and_port_validation():
    assert auth.validate_ip("::1") is None
    assert auth.validate_ip("999.1.1.1") == "ip_bad"
    assert auth.validate_port("65535") is None
    assert auth.validate_port("0") == "port_bad"


def test_password_rules():
    cases = [
        ("Ab1!", "pw_short"), ("Abcdefgh!", "pw_digit"), ("abcdefg1!", "pw_upper"),
        ("ABCDEFG1!", "pw_lower"), ("Abcdefg12", "pw_special"), ("Strong#Pass1", None),
    ]
    for pw, err in cases:
        assert auth.password_error(pw) == err


def test_create_authenticate_and_persist():
    users: dict = {}
    auth.create_user(users, "Anna", 30, "Lviv", "10.0.0.1", 8080, "Strong#Pass1")
    auth.save_users(users)
    loaded = auth.load_users()
    assert auth.authenticate(loaded, "anna", "Strong#Pass1").name == "Anna"
    assert auth.authenticate(loaded, "anna", "wrong") is None
    assert auth.authenticate(loaded, "nobody", "x") is None


def test_underage_and_duplicate():
    users: dict = {}
    with unittest.TestCase().assertRaises(auth.Underage):
        auth.create_user(users, "Kid", 12, "x", "1.1.1.1", 1, "Strong#Pass1")
    auth.create_user(users, "Anna", 30, "x", "1.1.1.1", 1, "Strong#Pass1")
    with unittest.TestCase().assertRaises(auth.UserExists):
        auth.create_user(users, "ANNA", 30, "x", "1.1.1.1", 1, "Strong#Pass1")


def test_lockout_then_recovery():
    users: dict = {}
    auth.create_user(users, "Anna", 30, "x", "1.1.1.1", 1, "Strong#Pass1")
    for _ in range(config.MAX_ATTEMPTS):
        assert auth.authenticate(users, "anna", "bad", now=1000.0) is None
    with unittest.TestCase().assertRaises(auth.LockedOut):
        auth.authenticate(users, "anna", "Strong#Pass1", now=1001.0)
    later = 1000.0 + config.LOCKOUT_SECONDS + 1
    assert auth.authenticate(users, "anna", "Strong#Pass1", now=later) is not None


def test_corrupt_file_is_backed_up():
    config.USERS_FILE.write_text("{not json", encoding="utf-8")
    assert auth.load_users() == {}
    assert config.USERS_FILE.with_suffix(".corrupt").exists()


def test_old_records_without_new_fields_load():
    config.USERS_FILE.write_text(
        '{"a": {"name": "A", "age": 20, "location": "x", "ip": "1.1.1.1", "port": 1,'
        ' "salt": "00", "pw_hash": "00"}}', encoding="utf-8")
    assert auth.load_users()["a"].lang == "en"

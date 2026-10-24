"""Tests for the Jarvis assistant."""

import sys
from pathlib import Path

# Make the repository root importable when pytest is launched outside it.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jarvis.assistant import (  # pylint: disable=import-error,wrong-import-position  # type: ignore[import-not-found]
    Session,
    handle,
)
from jarvis.assistant.speech import (  # pylint: disable=import-error,wrong-import-position  # type: ignore[import-not-found]
    Speaker,
    strip_wake_word,
)
from jarvis.i18n import (  # pylint: disable=import-error,wrong-import-position  # type: ignore[import-not-found]
    set_lang,  # pylint: disable=import-error,wrong-import-position  # type: ignore[import-not-found]
)


def make(user):
    return Session(user, Speaker(enabled=False))


def test_calculator(user):
    s = make(user)
    assert handle("what is 12 times 7", s) == "84"
    assert handle("what is 2 to the power of 10", s) == "1024"
    assert handle("скільки буде 6 плюс 4", s) == "10"
    assert "could not" in handle("calculate 1 / 0", s)


def test_calculator_never_evaluates_code(user):
    out = handle("what is __import__('os').system('echo PWNED_TOKEN')", make(user))
    assert "ANTHROPIC_API_KEY" in out  # fell through to the AI fallback, nothing executed


def test_time_date_who(user):
    s = make(user)
    assert ":" in handle("what time is it", s)
    assert "Anna Maria" in handle("who am i", s)
    set_lang("uk")
    assert "Anna Maria" in handle("хто я", s)


def test_notes_are_per_user(user):
    s = make(user)
    handle("note buy milk", s)
    assert "buy milk" in handle("read notes", s)
    handle("clear notes", s)
    assert handle("read notes", s) == "You have no notes."


def test_timer_can_be_cancelled(user):
    s = make(user)
    assert "Timer set" in handle("timer for 5 minutes", s)
    assert len(s.timers) == 1
    s.close()
    assert not s.timers


def test_unknown_command_without_key(user):
    assert "ANTHROPIC_API_KEY" in handle("tell me a joke", make(user))


def test_wake_word():
    assert strip_wake_word("hey Jarvis what time is it") == "what time is it"
    assert strip_wake_word("jarvis") == ""
    assert strip_wake_word("what time is it") is None

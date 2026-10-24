import pytest

from jarvis.assistant.extra_skills import (
    convert,
    format_number,
    parse_duration,
    safe_calc,
)


def test_calc_basic():
    assert safe_calc("2 + 3 * 4") == 14
    assert safe_calc("10 divided by 4") == 2.5
    assert safe_calc("2 ^ 10") == 1024


def test_calc_rejects_code():
    with pytest.raises((ValueError, SyntaxError)):
        safe_calc("__import__('os').system('echo hi')")


def test_calc_exponent_limit():
    with pytest.raises(ValueError):
        safe_calc("9 ** 9999")


def test_format_number():
    assert format_number(12.0) == "12"
    assert format_number(0.1 + 0.2) == "0.3"


def test_convert_length_and_mass():
    assert convert(1, "km", "m") == 1000
    assert round(convert(1, "mile", "km"), 3) == 1.609
    assert round(convert(1, "kg", "lb"), 3) == 2.205


def test_convert_temperature():
    assert convert(100, "c", "f") == 212
    assert round(convert(0, "c", "k"), 2) == 273.15


def test_convert_incompatible():
    with pytest.raises(ValueError):
        convert(1, "kg", "km")


def test_parse_duration():
    assert parse_duration("5 minutes") == 300
    assert parse_duration("1 hour 30 minutes") == 5400
    assert parse_duration("45 seconds") == 45
    assert parse_duration("soon") == 0

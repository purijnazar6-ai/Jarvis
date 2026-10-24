"""Extra skills for Jarvis (standard library only, so the core stays fast).

Install: save as jarvis/assistant/extra_skills.py and add this line at the
very bottom of jarvis/assistant/skills.py (after @skill is defined):

    from . import extra_skills  # noqa: F401,E402

Every skill returns a string, or None to let the next skill / the AI answer.
"""
from __future__ import annotations

import ast
import operator
import platform
import random
import re
import secrets
import string
import sys
import threading
import time
import webbrowser
from datetime import date, datetime
from urllib.parse import quote_plus

from .skills import skill

# --------------------------------------------------------------------------
# Helpers (pure functions, easy to test)
# --------------------------------------------------------------------------

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_WORDS = (
    ("divided by", "/"),
    ("multiplied by", "*"),
    ("to the power of", "**"),
    ("times", "*"),
    ("plus", "+"),
    ("minus", "-"),
    ("mod", "%"),
)


def format_number(x: float) -> str:
    """12.0 -> '12', 0.1+0.2 -> '0.3'."""
    if isinstance(x, float) and x.is_integer() and abs(x) < 1e15:
        return str(int(x))
    return f"{x:.10g}"


def safe_calc(expr: str):
    """Evaluate a math expression without eval(). Raises ValueError on bad input."""
    text = expr.lower().strip()
    for word, sym in _WORDS:
        text = text.replace(word, sym)
    text = text.replace("^", "**").replace("×", "*").replace("÷", "/")
    tree = ast.parse(text, mode="eval")

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
        ):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError("exponent too large")
            return _OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](ev(node.operand))
        raise ValueError("unsupported expression")

    return ev(tree)


# unit name -> (category, factor to the category's base unit)
_UNITS: dict[str, tuple[str, float]] = {}


def _add_units(category: str, factor: float, *names: str) -> None:
    for n in names:
        _UNITS[n] = (category, factor)


_add_units("length", 1, "m", "meter", "meters", "metre", "metres")
_add_units("length", 1000, "km", "kilometer", "kilometers", "kilometre", "kilometres")
_add_units("length", 0.01, "cm", "centimeter", "centimeters")
_add_units("length", 0.001, "mm", "millimeter", "millimeters")
_add_units("length", 1609.344, "mile", "miles", "mi")
_add_units("length", 0.3048, "ft", "foot", "feet")
_add_units("length", 0.0254, "inch", "inches")
_add_units("mass", 1, "kg", "kilogram", "kilograms")
_add_units("mass", 0.001, "g", "gram", "grams")
_add_units("mass", 0.45359237, "lb", "lbs", "pound", "pounds")
_add_units("mass", 0.028349523125, "oz", "ounce", "ounces")
_add_units("volume", 1, "l", "liter", "liters", "litre", "litres")
_add_units("volume", 0.001, "ml", "milliliter", "milliliters")
_add_units("volume", 3.785411784, "gallon", "gallons")
_add_units("temp", 0, "c", "celsius", "f", "fahrenheit", "k", "kelvin")

_TEMP_KEY = {"c": "c", "celsius": "c", "f": "f", "fahrenheit": "f", "k": "k", "kelvin": "k"}


def convert(value: float, src: str, dst: str) -> float:
    """Convert between supported units. Raises ValueError for unknown/mixed units."""
    src, dst = src.lower(), dst.lower()
    if src not in _UNITS or dst not in _UNITS:
        raise ValueError("unknown unit")
    cat_s, f_s = _UNITS[src]
    cat_d, f_d = _UNITS[dst]
    if cat_s != cat_d:
        raise ValueError("units are not compatible")
    if cat_s == "temp":
        s, d = _TEMP_KEY[src], _TEMP_KEY[dst]
        celsius = {"c": value, "f": (value - 32) * 5 / 9, "k": value - 273.15}[s]
        return {"c": celsius, "f": celsius * 9 / 5 + 32, "k": celsius + 273.15}[d]
    return value * f_s / f_d


_DURATION_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s)\b",
    re.IGNORECASE,
)


def parse_duration(text: str) -> float:
    """'1 hour 30 minutes' -> 5400.0 seconds (0 if nothing recognised)."""
    total = 0.0
    for amount, unit in _DURATION_RE.findall(text):
        u = unit.lower()
        mult = 3600 if u.startswith("h") else 60 if u.startswith("m") else 1
        total += float(amount) * mult
    return total


def _fmt_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    parts = [f"{h}h" if h else "", f"{m}m" if m else "", f"{s}s" if s or not (h or m) else ""]
    return " ".join(p for p in parts if p)


# --------------------------------------------------------------------------
# Skills
# --------------------------------------------------------------------------

@skill(r"(?i)^(?:calculate|calc|compute)\s+(.+)$")
def calculator(match, session):
    try:
        return f"= {format_number(safe_calc(match.group(1)))}"
    except ZeroDivisionError:
        return "I can't divide by zero."
    except (ValueError, SyntaxError, OverflowError, TypeError):
        return "Sorry, I couldn't calculate that."


@skill(r"(?i)^convert\s+(-?\d+(?:\.\d+)?)\s*([a-z]+)\s+(?:to|in|into)\s+([a-z]+)$")
def unit_converter(match, session):
    value = float(match.group(1))
    try:
        result = convert(value, match.group(2), match.group(3))
    except ValueError as exc:
        return f"I can't convert that: {exc}."
    return f"{format_number(value)} {match.group(2)} = {format_number(round(result, 6))} {match.group(3)}"


@skill(r"(?i)^(?:what(?:'s| is) (?:the )?(?:date|day)(?: today)?|what day is it|today'?s date)\??$")
def today_date(match, session):
    return datetime.now().strftime("Today is %A, %d %B %Y.")


@skill(r"(?i)^(?:how many )?days (?:until|to|till) (\d{4}-\d{2}-\d{2})$")
def days_until(match, session):
    try:
        target = date.fromisoformat(match.group(1))
    except ValueError:
        return "That date doesn't look valid. Use YYYY-MM-DD."
    delta = (target - date.today()).days
    if delta > 0:
        return f"{delta} day(s) until {target.isoformat()}."
    if delta == 0:
        return "That's today!"
    return f"{target.isoformat()} was {-delta} day(s) ago."


@skill(r"(?i)^set (?:a )?timer (?:for )?(.+)$")
def set_timer(match, session):
    seconds = parse_duration(match.group(1))
    if seconds <= 0:
        return "How long? For example: set a timer for 5 minutes."
    if seconds > 24 * 3600:
        return "Timers are limited to 24 hours."
    label = _fmt_duration(seconds)

    def ring():
        print(f"\n\u23f0 Timer finished: {label}\n", flush=True)

    t = threading.Timer(seconds, ring)
    t.daemon = True
    t.start()
    return f"Timer set for {label}."


_stopwatch: dict[str, float] = {}


@skill(r"(?i)^(start|stop) (?:the )?stopwatch$")
def stopwatch(match, session):
    if match.group(1).lower() == "start":
        _stopwatch["t0"] = time.monotonic()
        return "Stopwatch started."
    t0 = _stopwatch.pop("t0", None)
    if t0 is None:
        return "The stopwatch isn't running."
    return f"Stopwatch stopped: {_fmt_duration(time.monotonic() - t0)}."


@skill(r"(?i)^(?:flip|toss) a coin$")
def coin_flip(match, session):
    return random.choice(("Heads.", "Tails."))


@skill(r"(?i)^roll (?:a )?(?:dice|die)$|^roll (\d{1,2})d(\d{1,3})$")
def dice(match, session):
    n, sides = (int(match.group(1)), int(match.group(2))) if match.group(1) else (1, 6)
    if n < 1 or sides < 2:
        return "That's not a valid roll."
    rolls = [random.randint(1, sides) for _ in range(n)]
    if n == 1:
        return f"You rolled a {rolls[0]}."
    return f"You rolled {rolls} (total {sum(rolls)})."


@skill(r"(?i)^random number between (-?\d+) and (-?\d+)$")
def random_number(match, session):
    a, b = sorted((int(match.group(1)), int(match.group(2))))
    return str(random.randint(a, b))


@skill(r"(?i)^(?:generate|make|create) (?:a )?(?:strong |secure )?password(?: (?:with|of) (\d+) characters)?$")
def password_generator(match, session):
    length = max(8, min(int(match.group(1) or 16), 64))
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*-_" for c in pwd)
        ):
            return f"{pwd}  (not saved anywhere)"


_JOKES = (
    "There are 10 kinds of people: those who understand binary and those who don't.",
    "A SQL query walks into a bar, sees two tables and asks: can I join you?",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "It works on my machine. Then we'll ship your machine.",
    "I'd tell you a UDP joke, but you might not get it.",
    "There's no place like 127.0.0.1.",
    "Debugging: being the detective in a crime movie where you are also the murderer.",
)


@skill(r"(?i)^(?:tell me )?a programming joke$")
def programming_joke(match, session):
    return random.choice(_JOKES)


_SITES = {
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "wikipedia": "https://www.wikipedia.org",
    "maps": "https://maps.google.com",
}


@skill(r"(?i)^open (youtube|github|google|gmail|wikipedia|maps)$")
def open_site(match, session):
    name = match.group(1).lower()
    ok = webbrowser.open(_SITES[name])
    return f"Opening {name}." if ok else f"I couldn't open a browser. Here is the link: {_SITES[name]}"


@skill(r"(?i)^(?:google|web search(?: for)?|search the web for)\s+(.+)$")
def web_search(match, session):
    url = "https://www.google.com/search?q=" + quote_plus(match.group(1).strip())
    ok = webbrowser.open(url)
    return "Searching the web." if ok else f"I couldn't open a browser. Link: {url}"


@skill(r"(?i)^(?:system info|what (?:os|system) am i (?:on|using))$")
def system_info(match, session):
    return f"{platform.system()} {platform.release()} ({platform.machine()}), Python {sys.version.split()[0]}."

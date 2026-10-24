"""Built-in skills. Patterns accept English and Ukrainian phrasing."""
from __future__ import annotations

import ast
import operator
import platform
import re
import subprocess
import threading
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

from .. import config
from ..i18n import format_date, t
from .core import Session, skill


# --------------------------------------------------------------------------- #
# Profile / info
# --------------------------------------------------------------------------- #
@skill(r"^(?:who am i|what(?:'s| is) my name|хто я)\??$")
def who_am_i(_, s: Session) -> str:
    u = s.user
    return t("who", name=u.name, age=u.age, loc=u.location)


@skill(r"^(?:help|what can you do|допомога|що ти вмієш)\??$")
def help_(_, __) -> str:
    return t("help")


@skill(r"^(?:what(?:'s| is) )?the time\b|^what time is it|^(?:котра година|скільки часу|який час)")
def tell_time(_, __) -> str:
    return t("time", t=f"{datetime.now():%H:%M}")


@skill(r"^(?:what(?:'s| is) )?(?:the )?(?:date|day)\b|^what day is it|"
       r"^яка (?:сьогодні )?дата|^який (?:сьогодні )?день")
def tell_date(_, __) -> str:
    return t("date", d=format_date(datetime.now()))


@skill(r"^system (?:status|info)$|^how is (?:my|the) (?:system|computer)|^стан системи$")
def system_status(_, __) -> str:
    info = t("status", os=f"{platform.system()} {platform.release()}", py=platform.python_version())
    try:
        import psutil
        info += (f", CPU {psutil.cpu_percent(interval=0.3):.0f}%, "
                 f"RAM {psutil.virtual_memory().percent:.0f}%")
    except ImportError:
        pass
    return info


# --------------------------------------------------------------------------- #
# Safe calculator: only numbers and + - * / ** % are evaluated, never eval().
# --------------------------------------------------------------------------- #
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}
_WORDS = (("multiplied by", "*"), ("помножити на", "*"), ("times", "*"), ("plus", "+"),
          ("плюс", "+"), ("minus", "-"), ("мінус", "-"), ("divided by", "/"),
          ("поділити на", "/"), ("to the power of", "**"), ("modulo", "%"))


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("exponent too large")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported expression")


@skill(r"^(?:calculate|compute|what(?:'s| is)|how much is|порахуй|скільки буде)\s+(.+)$")
def calculate(m: re.Match, _) -> str | None:
    expr = m.group(1).lower().rstrip("?")
    for word, sym in _WORDS:
        expr = expr.replace(word, sym)
    if not re.fullmatch(r"[\d\s.+\-*/%()]+", expr):
        return None  # not math: let another skill (or the AI) handle it
    try:
        return f"{_eval(ast.parse(expr.strip(), mode='eval')):g}"
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError):
        return t("calc_fail")


# --------------------------------------------------------------------------- #
# Open things (allowlist only: Jarvis never runs arbitrary commands)
# --------------------------------------------------------------------------- #
SITES = {
    "youtube": "https://www.youtube.com", "google": "https://www.google.com",
    "github": "https://github.com", "gmail": "https://mail.google.com",
    "maps": "https://maps.google.com",
}
APPS = {
    "Windows": {"notepad": ["notepad"], "calculator": ["calc"]},
    "Darwin": {"calculator": ["open", "-a", "Calculator"], "notes": ["open", "-a", "Notes"]},
    "Linux": {"calculator": ["gnome-calculator"], "terminal": ["x-terminal-emulator"]},
}


@skill(r"^(?:open|відкрий)\s+(.+)$")
def open_target(m: re.Match, _) -> str:
    name = m.group(1).strip().lower()
    if name in SITES:
        webbrowser.open(SITES[name])
        return t("open_ok", x=name)
    cmd = APPS.get(platform.system(), {}).get(name)
    if not cmd:
        return t("open_unknown", x=name)
    try:
        subprocess.Popen(cmd)
        return t("open_ok", x=name)
    except OSError:
        return t("open_fail", x=name)


@skill(r"^(?:search(?: for)?|google|знайди|пошукай)\s+(.+)$")
def web_search(m: re.Match, _) -> str:
    q = m.group(1).strip()
    webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote_plus(q))
    return t("search", q=q)


@skill(r"^(?:weather|погода)(?: in| в| у)?\s*(.*)$")
def weather(m: re.Match, s: Session) -> str:
    city = m.group(1).strip() or s.user.location  # default: the user's saved location
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=3"
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.read().decode().strip()
    except OSError:
        return t("weather_fail")


# --------------------------------------------------------------------------- #
# Timers
# --------------------------------------------------------------------------- #
def _unit_seconds(word: str) -> int:
    w = word.lower()
    if w.startswith(("sec", "сек")):
        return 1
    if w.startswith(("min", "хв")):
        return 60
    return 3600


@skill(r"^(?:(?:set (?:a )?)?timer(?: for)?|таймер(?: на)?)\s+(\d+)\s*"
       r"(sec\w*|min\w*|hour\w*|сек\w*|хв\w*|год\w*)$")
def set_timer(m: re.Match, s: Session) -> str:
    amount, unit = int(m.group(1)), m.group(2)
    timer = threading.Timer(
        amount * _unit_seconds(unit),
        lambda: s.speaker.say(t("timer_done", a=amount, u=unit)))
    timer.daemon = True
    timer.start()
    s.timers.append(timer)
    return t("timer_set", a=amount, u=unit)


# --------------------------------------------------------------------------- #
# Notes (one file per user, kept out of other users' reach)
# --------------------------------------------------------------------------- #
def _notes_path(s: Session) -> Path:
    return config.DATA_DIR / "notes" / f"{s.user.uid}.txt"


@skill(r"^(?:(?:take a )?note|запиши|нотатка)[: ]\s*(.+)$")
def add_note(m: re.Match, s: Session) -> str:
    path = _notes_path(s)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M} {m.group(1).strip()}\n")
    return t("note_saved")


@skill(r"^(?:(?:read|show) (?:my )?notes|покажи нотатки)$")
def read_notes(_, s: Session) -> str:
    path = _notes_path(s)
    if not path.exists():
        return t("no_notes")
    lines = path.read_text(encoding="utf-8").splitlines()[-5:]
    return t("notes_last", x=" | ".join(lines))


@skill(r"^(?:(?:clear|delete) (?:my )?notes|очисти нотатки)$")
def clear_notes(_, s: Session) -> str:
    _notes_path(s).unlink(missing_ok=True)
    return t("notes_cleared")

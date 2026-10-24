"""Skill registry, session state and dispatch."""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from typing import Callable

from ..auth import User
from .speech import Speaker

Skill = Callable[[re.Match, "Session"], "str | None"]
SKILLS: list[tuple[re.Pattern, Skill]] = []


@dataclass
class Session:
    user: User
    speaker: Speaker
    history: list[dict] = field(default_factory=list)
    timers: list[threading.Timer] = field(default_factory=list)

    def close(self) -> None:
        for timer in self.timers:
            timer.cancel()
        self.timers.clear()


def skill(pattern: str) -> Callable[[Skill], Skill]:
    """Register a skill. It returns text to say, or None to let the next skill try."""
    rx = re.compile(pattern, re.IGNORECASE)

    def register(fn: Skill) -> Skill:
        SKILLS.append((rx, fn))
        return fn

    return register


def handle(text: str, session: Session) -> str:
    from . import ai  # local import avoids a cycle
    text = text.strip()
    for rx, fn in SKILLS:
        if m := rx.search(text):
            if (reply := fn(m, session)) is not None:
                return reply
    return ai.ask(text, session)

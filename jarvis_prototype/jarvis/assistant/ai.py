"""Optional AI fallback: anything no skill matched goes to Claude (stdlib only)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .. import config
from ..i18n import get_lang, t
from .core import Session

API_URL = "https://api.anthropic.com/v1/messages"
MAX_HISTORY = 20


def ask(text: str, session: Session) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return t("no_ai")
    language = "Ukrainian" if get_lang() == "uk" else "English"
    session.history.append({"role": "user", "content": text})
    body = json.dumps({
        "model": config.MODEL,
        "max_tokens": 300,
        "system": (f"You are Jarvis, a concise voice assistant talking to {session.user.name}. "
                   f"Answer in one to three short sentences, in {language}."),
        "messages": session.history[-MAX_HISTORY:],
    }).encode()
    req = urllib.request.Request(
        API_URL, data=body, method="POST",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            reply = json.load(resp)["content"][0]["text"].strip()
    except (OSError, KeyError, IndexError, json.JSONDecodeError) as exc:
        session.history.pop()  # keep user/assistant turns alternating
        return t("ai_unavailable", e=type(exc).__name__)
    session.history.append({"role": "assistant", "content": reply})
    return reply

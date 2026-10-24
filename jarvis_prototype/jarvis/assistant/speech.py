"""Speech in/out. Printing is instant; speaking runs in a background thread."""
from __future__ import annotations

import importlib.util
import queue
import threading

from .. import config


class VoiceUnavailable(Exception):
    pass


def voice_libs_installed() -> bool:
    return all(importlib.util.find_spec(m) for m in ("pyttsx3", "speech_recognition"))


class Speaker:
    def __init__(self, enabled: bool = False) -> None:
        self._q: queue.Queue[str | None] = queue.Queue()
        self._enabled = enabled
        if enabled:
            threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        try:
            import pyttsx3
            engine = pyttsx3.init()  # must be created in the thread that uses it
        except Exception as exc:  # noqa: BLE001 - any TTS failure just disables speech
            print(f"[tts disabled: {exc}]")
            self._enabled = False
            return
        while (text := self._q.get()) is not None:
            engine.say(text)
            engine.runAndWait()

    def say(self, text: str) -> None:
        print(f"Jarvis: {text}")
        if self._enabled:
            self._q.put(text)

    def close(self) -> None:
        if self._enabled:
            self._q.put(None)


def listen_voice() -> str | None:
    """Return recognised text, or None if nothing was understood.
    Raises VoiceUnavailable if the microphone cannot be used."""
    import speech_recognition as sr
    rec = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            rec.adjust_for_ambient_noise(source, duration=0.3)
            try:
                audio = rec.listen(source, timeout=6, phrase_time_limit=8)
            except sr.WaitTimeoutError:
                return None
    except (OSError, AttributeError) as exc:
        raise VoiceUnavailable(str(exc)) from exc
    try:
        return rec.recognize_google(audio)
    except (sr.UnknownValueError, sr.RequestError):
        return None


def strip_wake_word(heard: str) -> str | None:
    """None if the wake word was not said, else the command after it ('' if none)."""
    import re
    m = re.search(rf"\b{re.escape(config.WAKE_WORD)}\b[,\s]*", heard, re.IGNORECASE)
    return heard[m.end():].strip() if m else None

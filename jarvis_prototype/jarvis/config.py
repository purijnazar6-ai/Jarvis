"""Central settings. Everything can be overridden with environment variables."""
from __future__ import annotations

import logging
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("JARVIS_HOME", "data")).resolve()
USERS_FILE = DATA_DIR / "users.json"
LOG_FILE = DATA_DIR / "jarvis.log"

MIN_AGE = 18
MAX_ATTEMPTS = 3          # wrong passwords before the account is locked
LOCKOUT_SECONDS = 30
WAKE_WORD = "jarvis"
MODEL = os.environ.get("JARVIS_MODEL", "claude-sonnet-5-5")


def setup_logging() -> None:
    """Log to a file so the console stays clean. Never log passwords."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE, level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

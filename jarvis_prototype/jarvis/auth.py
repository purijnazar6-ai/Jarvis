"""Accounts: storage, password hashing, validation, lockout. No printing, no input()."""
from __future__ import annotations

import dataclasses
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import re
import shutil
import socket
import time
import uuid
from dataclasses import asdict, dataclass, field

from . import config

log = logging.getLogger(__name__)

NAME_RE = re.compile(r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)*$")
SPECIALS = "!@#$%^&*()-_=+[]{}|;:'\",.<>?/`~"


class UserExists(Exception):
    pass


class Underage(Exception):
    pass


class LockedOut(Exception):
    def __init__(self, seconds: int) -> None:
        super().__init__(seconds)
        self.seconds = seconds


@dataclass
class User:
    name: str
    age: int
    location: str
    ip: str
    port: int
    salt: str
    pw_hash: str
    lang: str = "en"
    uid: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    failed: int = 0
    locked_until: float = 0.0


# --------------------------------------------------------------------------- #
# Hashing
# --------------------------------------------------------------------------- #
def hash_password(password: str, salt: bytes) -> str:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32).hex()


def check_password(user: User, password: str) -> bool:
    candidate = hash_password(password, bytes.fromhex(user.salt))
    return hmac.compare_digest(candidate, user.pw_hash)


def set_password(user: User, password: str) -> None:
    salt = os.urandom(16)
    user.salt, user.pw_hash = salt.hex(), hash_password(password, salt)


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #
def load_users() -> dict[str, User]:
    path = config.USERS_FILE
    if not path.exists():
        return {}
    known = {f.name for f in dataclasses.fields(User)}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {k: User(**{a: b for a, b in rec.items() if a in known}) for k, rec in raw.items()}
    except (json.JSONDecodeError, TypeError, AttributeError, OSError) as exc:
        # Keep the unreadable file instead of silently overwriting it on the next save.
        backup = path.with_suffix(".corrupt")
        shutil.copy2(path, backup)
        log.error("Could not read %s (%s). Copy kept at %s", path, exc, backup)
        return {}


def save_users(users: dict[str, User]) -> None:
    path = config.USERS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({k: asdict(v) for k, v in users.items()},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass  # best effort (not supported on every OS)
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Validation (each returns a translation key on error, or None)
# --------------------------------------------------------------------------- #
def validate_name(value: str) -> str | None:
    return None if NAME_RE.match(value) else "name_bad"


def validate_ip(value: str) -> str | None:
    try:
        ipaddress.ip_address(value)
        return None
    except ValueError:
        return "ip_bad"


def validate_port(value: str) -> str | None:
    return None if value.isdigit() and 1 <= int(value) <= 65535 else "port_bad"


def password_error(value: str) -> str | None:
    if len(value) < 8:
        return "pw_short"
    if not any(c.isdigit() for c in value):
        return "pw_digit"
    if not any(c.isupper() for c in value):
        return "pw_upper"
    if not any(c.islower() for c in value):
        return "pw_lower"
    if not any(c in SPECIALS for c in value):
        return "pw_special"
    return None


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


# --------------------------------------------------------------------------- #
# Operations
# --------------------------------------------------------------------------- #
def create_user(users: dict[str, User], name: str, age: int, location: str,
                ip: str, port: int, password: str, lang: str = "en") -> User:
    if age < config.MIN_AGE:
        raise Underage
    key = name.lower()
    if key in users:
        raise UserExists
    user = User(name=name, age=age, location=location, ip=ip, port=port,
                salt="", pw_hash="", lang=lang)
    set_password(user, password)
    users[key] = user
    log.info("Registered user %s", name)
    return user


def authenticate(users: dict[str, User], name: str, password: str,
                 now: float | None = None) -> User | None:
    """Return the user on success, None on failure. Raises LockedOut while locked.
    The caller must save_users() afterwards because counters change."""
    now = time.time() if now is None else now
    user = users.get(name.strip().lower())
    if user is None:
        hash_password(password, b"\0" * 16)  # keep timing similar for unknown names
        log.warning("Failed login for unknown user %r", name)
        return None
    if user.locked_until > now:
        raise LockedOut(int(user.locked_until - now) + 1)
    if check_password(user, password):
        user.failed, user.locked_until = 0, 0.0
        log.info("Login OK: %s", user.name)
        return user
    user.failed += 1
    log.warning("Failed login for %s (%d)", user.name, user.failed)
    if user.failed >= config.MAX_ATTEMPTS:
        user.failed = 0
        user.locked_until = now + config.LOCKOUT_SECONDS
        log.warning("Account locked: %s", user.name)
    return None


def delete_user(users: dict[str, User], user: User) -> None:
    users.pop(user.name.lower(), None)
    log.info("Account deleted: %s", user.name)

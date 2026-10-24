"""Interactive entry point: register / log in, then use the account menu or start Jarvis."""
from __future__ import annotations

import getpass
import logging
import platform  # noqa: F401  (kept for easy extension of the profile screen)
import re

from . import auth, config
from .assistant import Session, handle
from .assistant.speech import (Speaker, VoiceUnavailable, listen_voice,
                               strip_wake_word, voice_libs_installed)
from .auth import User
from .i18n import SUPPORTED, set_lang, t

log = logging.getLogger(__name__)
EXIT_RX = re.compile(r"^(exit|quit|goodbye|bye|shut down|вихід|до побачення)\b", re.IGNORECASE)


# --------------------------------------------------------------------------- #
# Input helpers (each loops until the value is valid)
# --------------------------------------------------------------------------- #
def ask(prompt_key: str, validator=None) -> str:
    while True:
        value = input(t(prompt_key)).strip()
        if not value:
            print(t("empty"))
            continue
        err = validator(value) if validator else None
        if err:
            print(t(err))
            continue
        return value


def ask_age() -> int:
    value = ask("age", lambda v: None if v.isdigit() else "age_num")
    if int(value) < config.MIN_AGE:
        raise auth.Underage
    return int(value)


def ask_port() -> int:
    while True:
        port = int(ask("port", auth.validate_port))
        if auth.port_is_free(port):
            return port
        print(t("port_busy", p=port))


def ask_new_password(prompt_key: str = "pw") -> str:
    while True:
        pw = getpass.getpass(t(prompt_key))
        if err := auth.password_error(pw):
            print(t(err))
            continue
        if getpass.getpass(t("pw_repeat")) != pw:
            print(t("pw_mismatch"))
            continue
        return pw


def ask_lang() -> str:
    choice = input(t("lang_ask")).strip().lower()
    return choice if choice in SUPPORTED else "en"


# --------------------------------------------------------------------------- #
# Account actions
# --------------------------------------------------------------------------- #
def register(users: dict[str, User], lang: str) -> None:
    name = ask("name", auth.validate_name)
    if name.lower() in users:
        print(t("exists"))
        return
    try:
        age = ask_age()
    except auth.Underage:
        print(t("underage"))
        return
    ip = ask("ip", auth.validate_ip)
    location = ask("location")
    port = ask_port()
    password = ask_new_password()
    auth.create_user(users, name, age, location, ip, port, password, lang)
    auth.save_users(users)
    print(t("registered", n=name))


def login(users: dict[str, User]) -> User | None:
    for attempt in range(config.MAX_ATTEMPTS):
        name = input(t("login_user")).strip()
        password = getpass.getpass(t("login_pw"))
        try:
            user = auth.authenticate(users, name, password)
        except auth.LockedOut as exc:
            print(t("locked_wait", s=exc.seconds))
            return None
        auth.save_users(users)  # failure counters / lockout are persisted
        if user:
            set_lang(user.lang)
            print(t("login_ok", n=user.name))
            return user
        print(t("login_fail", left=config.MAX_ATTEMPTS - attempt - 1))
    return None


def change_password(user: User, users: dict[str, User]) -> None:
    if not auth.check_password(user, getpass.getpass(t("old_pw"))):
        print(t("pw_wrong"))
        return
    auth.set_password(user, ask_new_password("new_pw"))
    auth.save_users(users)
    log.info("Password changed: %s", user.name)
    print(t("pw_changed"))


def settings_menu(user: User, users: dict[str, User]) -> None:
    while True:
        print(t("settings"))
        choice = input(t("choose")).strip()
        if choice == "1":
            user.location = ask("location")
        elif choice == "2":
            user.ip = ask("ip", auth.validate_ip)
        elif choice == "3":
            user.port = ask_port()
        elif choice == "4":
            user.lang = ask_lang()
            set_lang(user.lang)
        elif choice == "5":
            return
        else:
            print(t("invalid_choice"))
            continue
        auth.save_users(users)
        print(t("saved"))


def delete_account(user: User, users: dict[str, User]) -> bool:
    if input(t("confirm_del")).strip().lower() != user.name.lower():
        print(t("cancelled"))
        return False
    notes = config.DATA_DIR / "notes" / f"{user.uid}.txt"
    notes.unlink(missing_ok=True)
    auth.delete_user(users, user)
    auth.save_users(users)
    print(t("deleted"))
    return True


# --------------------------------------------------------------------------- #
# Assistant loop
# --------------------------------------------------------------------------- #
def run_assistant(user: User, voice: bool) -> None:
    if voice and not voice_libs_installed():
        print(t("voice_missing"))
        voice = False
    session = Session(user, Speaker(enabled=voice))
    session.speaker.say(t("online", n=user.name))
    try:
        while True:
            if voice:
                try:
                    heard = listen_voice()
                except VoiceUnavailable:
                    print(t("voice_no_mic"))
                    voice = False
                    continue
                if not heard:
                    continue
                text = strip_wake_word(heard)
                if text is None:
                    continue
                if not text:
                    session.speaker.say(t("yes"))
                    continue
                print(f"You: {text}")
            else:
                text = input("You: ").strip()
                if not text:
                    continue
            if EXIT_RX.match(text):
                session.speaker.say(t("goodbye"))
                break
            session.speaker.say(handle(text, session))
    except KeyboardInterrupt:
        print()
    finally:
        session.close()
        session.speaker.close()


def main_menu(user: User, users: dict[str, User]) -> None:
    while True:
        print(t("menu"))
        choice = input(t("choose")).strip()
        if choice == "1":
            run_assistant(user, voice=False)
        elif choice == "2":
            run_assistant(user, voice=True)
        elif choice == "3":
            print(t("profile", name=user.name, age=user.age, location=user.location,
                    ip=user.ip, port=user.port))
        elif choice == "4":
            change_password(user, users)
        elif choice == "5":
            settings_menu(user, users)
        elif choice == "6":
            if delete_account(user, users):
                return
        elif choice == "7":
            return
        else:
            print(t("invalid_choice"))


def main() -> None:
    config.setup_logging()
    try:
        lang = input("Language / Мова [en/uk]: ").strip().lower()
        lang = lang if lang in SUPPORTED else "en"
        set_lang(lang)
        users = auth.load_users()
        while True:
            print(t("welcome"))
            choice = input(t("choose")).strip()
            if choice == "1":
                register(users, lang)
            elif choice == "2":
                if user := login(users):
                    main_menu(user, users)
                    set_lang(lang)
            elif choice == "3":
                print(t("bye"))
                return
            else:
                print(t("invalid_choice"))
    except (KeyboardInterrupt, EOFError):
        print()

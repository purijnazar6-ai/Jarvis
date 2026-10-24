"""All user-facing text in one place (English + Ukrainian)."""
from __future__ import annotations

from datetime import datetime

SUPPORTED = ("en", "uk")
_lang = "en"


def set_lang(code: str) -> None:
    global _lang
    _lang = code if code in SUPPORTED else "en"


def get_lang() -> str:
    return _lang


def t(key: str, **kw) -> str:
    text = T.get(_lang, T["en"]).get(key) or T["en"][key]
    return text.format(**kw) if kw else text


_WEEKDAYS_UK = ["понеділок", "вівторок", "середа", "четвер", "пʼятниця", "субота", "неділя"]
_MONTHS_UK = ["січня", "лютого", "березня", "квітня", "травня", "червня",
              "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"]


def format_date(dt: datetime) -> str:
    if _lang == "uk":
        return f"{_WEEKDAYS_UK[dt.weekday()]}, {dt.day} {_MONTHS_UK[dt.month - 1]} {dt.year}"
    return f"{dt:%A, %d %B %Y}"


T: dict[str, dict[str, str]] = {
    "en": {
        # --- input prompts & validation
        "empty": "This field cannot be empty.",
        "name": "Name: ", "name_bad": "Name must contain only letters, spaces, hyphens.",
        "age": "Age: ", "age_num": "Age must be a number.",
        "underage": "You are not allowed to access this program.",
        "ip": "IP address: ", "ip_bad": "Not a valid IP address.",
        "location": "Location: ",
        "port": "Port (1-65535): ", "port_bad": "Enter a number between 1 and 65535.",
        "port_busy": "Port {p} is already in use on this machine. Pick another.",
        "pw": "Password: ", "pw_repeat": "Repeat password: ",
        "pw_short": "Password must be at least 8 characters.",
        "pw_digit": "Password needs at least one digit.",
        "pw_upper": "Password needs an uppercase letter.",
        "pw_lower": "Password needs a lowercase letter.",
        "pw_special": "Password needs a special character.",
        "pw_mismatch": "Passwords do not match.",
        "lang_ask": "Language [en/uk]: ",
        # --- account flow
        "welcome": "\n=== Jarvis ===\n1. Register\n2. Log in\n3. Exit",
        "choose": "Choose: ", "invalid_choice": "Invalid choice.",
        "exists": "A user with this name already exists.",
        "registered": "Registration complete, {n}! You can now log in.",
        "login_user": "Username: ", "login_pw": "Password: ",
        "login_ok": "Login successful. Hello, {n}!",
        "login_fail": "Wrong username or password ({left} attempts left).",
        "locked_wait": "Account temporarily locked. Try again in {s} seconds.",
        "menu": "\n=== Main menu ===\n1. Start Jarvis (text)\n2. Start Jarvis (voice)\n"
                "3. View profile\n4. Change password\n5. Settings\n6. Delete account\n7. Log out",
        "profile": "Name: {name}\nAge: {age}\nLocation: {location}\nIP: {ip}\nPort: {port}",
        "old_pw": "Current password: ", "new_pw": "New password: ",
        "pw_wrong": "Wrong current password.", "pw_changed": "Password changed.",
        "settings": "\n=== Settings ===\n1. Change location\n2. Change IP\n"
                    "3. Change port\n4. Change language\n5. Back",
        "saved": "Saved.",
        "confirm_del": "Type your username to confirm deletion: ",
        "deleted": "Account deleted.", "cancelled": "Cancelled.",
        "bye": "Goodbye!",
        "voice_missing": "Voice mode needs: pip install pyttsx3 SpeechRecognition pyaudio. Using text mode.",
        "voice_no_mic": "No microphone available. Switching to text mode.",
        # --- assistant
        "online": "Jarvis online. Hello, {n}!",
        "goodbye": "Goodbye.", "yes": "Yes?",
        "time": "It is {t}.", "date": "Today is {d}.",
        "calc_fail": "I could not calculate that.",
        "open_ok": "Opening {x}.", "open_unknown": "I don't know how to open {x}.",
        "open_fail": "I could not start {x}.",
        "search": "Searching for {q}.",
        "weather_fail": "I couldn't reach the weather service.",
        "timer_set": "Timer set for {a} {u}.", "timer_done": "Your {a} {u} timer is done.",
        "note_saved": "Noted.", "no_notes": "You have no notes.",
        "notes_last": "Your last notes: {x}", "notes_cleared": "Notes cleared.",
        "status": "{os}, Python {py}",
        "who": "You are {name}, {age} years old, located in {loc}.",
        "no_ai": "I don't know that command. Set ANTHROPIC_API_KEY to let me answer anything.",
        "ai_unavailable": "The AI service is unavailable ({e}).",
        "help": "Try: what time is it, what is 12 times 7, open youtube, search cats, weather, "
                "timer for 5 minutes, note buy milk, read notes, system status, who am I, exit.",
    },
    "uk": {
        "empty": "Поле не може бути порожнім.",
        "name": "Ім'я: ", "name_bad": "Ім'я може містити лише літери, пробіли, дефіси.",
        "age": "Вік: ", "age_num": "Вік має бути числом.",
        "underage": "Вам заборонено доступ до цієї програми.",
        "ip": "IP-адреса: ", "ip_bad": "Некоректна IP-адреса.",
        "location": "Локація: ",
        "port": "Порт (1-65535): ", "port_bad": "Введіть число від 1 до 65535.",
        "port_busy": "Порт {p} вже зайнятий на цьому комп'ютері. Оберіть інший.",
        "pw": "Пароль: ", "pw_repeat": "Повторіть пароль: ",
        "pw_short": "Пароль має містити щонайменше 8 символів.",
        "pw_digit": "Пароль має містити цифру.",
        "pw_upper": "Пароль має містити велику літеру.",
        "pw_lower": "Пароль має містити малу літеру.",
        "pw_special": "Пароль має містити спеціальний символ.",
        "pw_mismatch": "Паролі не збігаються.",
        "lang_ask": "Мова [en/uk]: ",
        "welcome": "\n=== Jarvis ===\n1. Реєстрація\n2. Вхід\n3. Вийти",
        "choose": "Виберіть: ", "invalid_choice": "Невірний вибір.",
        "exists": "Користувач з таким ім'ям уже існує.",
        "registered": "Реєстрацію завершено, {n}! Тепер можна увійти.",
        "login_user": "Логін: ", "login_pw": "Пароль: ",
        "login_ok": "Вхід успішний. Вітаю, {n}!",
        "login_fail": "Неправильний логін або пароль (залишилось спроб: {left}).",
        "locked_wait": "Акаунт тимчасово заблоковано. Спробуйте за {s} с.",
        "menu": "\n=== Головне меню ===\n1. Запустити Jarvis (текст)\n2. Запустити Jarvis (голос)\n"
                "3. Переглянути профіль\n4. Змінити пароль\n5. Налаштування\n"
                "6. Видалити акаунт\n7. Вийти з акаунта",
        "profile": "Ім'я: {name}\nВік: {age}\nЛокація: {location}\nIP: {ip}\nПорт: {port}",
        "old_pw": "Поточний пароль: ", "new_pw": "Новий пароль: ",
        "pw_wrong": "Неправильний поточний пароль.", "pw_changed": "Пароль змінено.",
        "settings": "\n=== Налаштування ===\n1. Змінити локацію\n2. Змінити IP\n"
                    "3. Змінити порт\n4. Змінити мову\n5. Назад",
        "saved": "Збережено.",
        "confirm_del": "Введіть ваш логін для підтвердження видалення: ",
        "deleted": "Акаунт видалено.", "cancelled": "Скасовано.",
        "bye": "До побачення!",
        "voice_missing": "Для голосового режиму: pip install pyttsx3 SpeechRecognition pyaudio. Працюю в текстовому режимі.",
        "voice_no_mic": "Мікрофон недоступний. Перемикаюсь на текстовий режим.",
        "online": "Jarvis на зв'язку. Вітаю, {n}!",
        "goodbye": "До побачення.", "yes": "Слухаю?",
        "time": "Зараз {t}.", "date": "Сьогодні {d}.",
        "calc_fail": "Не вдалося порахувати.",
        "open_ok": "Відкриваю {x}.", "open_unknown": "Не знаю, як відкрити {x}.",
        "open_fail": "Не вдалося запустити {x}.",
        "search": "Шукаю {q}.",
        "weather_fail": "Не вдалося отримати погоду.",
        "timer_set": "Таймер встановлено: {a} {u}.", "timer_done": "Таймер на {a} {u} завершено.",
        "note_saved": "Записано.", "no_notes": "Нотаток немає.",
        "notes_last": "Останні нотатки: {x}", "notes_cleared": "Нотатки очищено.",
        "status": "{os}, Python {py}",
        "who": "Ви {name}, вам {age}, локація: {loc}.",
        "no_ai": "Не знаю такої команди. Задайте ANTHROPIC_API_KEY, і я відповідатиму на будь-що.",
        "ai_unavailable": "ШІ-сервіс недоступний ({e}).",
        "help": "Спробуйте: котра година, скільки буде 12 помножити на 7, відкрий youtube, "
                "знайди коти, погода, таймер на 5 хвилин, запиши купити молоко, "
                "покажи нотатки, стан системи, хто я, вихід.",
    },
}

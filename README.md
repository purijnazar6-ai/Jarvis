# Jarvis

Account system (register / login) plus a modular voice and text assistant, in one package.

## Run
    python -m jarvis

Pick a language, register, log in, then choose **Start Jarvis** (text or voice).

## Optional features
- Voice mode: `pip install pyttsx3 SpeechRecognition pyaudio`, say "Jarvis, what time is it".
- System status with CPU/RAM: `pip install psutil`.
- AI answers for anything not covered by a skill: set `ANTHROPIC_API_KEY`
  (model via `JARVIS_MODEL`, default `claude-sonnet-5-5`). Only your name and the
  conversation are sent, never your password or saved profile details.

## Data
Stored in `./data` (change with `JARVIS_HOME`): `users.json` (scrypt-hashed passwords),
`notes/<user-id>.txt`, `jarvis.log`.

## Add a skill
In `jarvis/assistant/skills.py`:

    @skill(r"^tell me a joke$")
    def joke(match, session):
        return "There are 10 kinds of people..."

Return `None` to let the next skill (or the AI) handle the phrase.

## Tests
    pip install pytest && pytest

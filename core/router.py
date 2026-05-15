#!/data/data/com.termux/files/usr/bin/env python3
"""
MENIX SENTINEL — Router (le cerveau)
=====================================
Reçoit une transcription en argv[1], décide :
  - action directe (torche, sos, photo...)  → exécution immédiate
  - question      (quelle roche...)         → Ollama qwen2.5:1.5b
Tout est journalisé dans SQLite + miroir JSON.
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
PROJECT = HOME / "menix-sentinel"
DB = PROJECT / "data" / "menix.db"
JSON_LOG = PROJECT / "data" / "events.json"
DB.parent.mkdir(parents=True, exist_ok=True)

OLLAMA_MODEL = "qwen2.5:1.5b"
OLLAMA_TIMEOUT = 25

SYSTEM_PROMPT = (
    "Tu es MENIX, assistant vocal d'un mineur en galerie souterraine. "
    "Réponds en français, en UNE phrase courte (max 25 mots), "
    "ton professionnel, pas d'emoji, pas de markdown. "
    "Spécialité : minéralogie, sécurité minière, premiers secours."
)

# --- DB --------------------------------------------------------------------
def db_init():
    con = sqlite3.connect(DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            kind TEXT NOT NULL,
            input TEXT,
            output TEXT,
            meta TEXT
        )""")
    con.commit()
    return con


def log_event(kind: str, input_: str = "", output: str = "", meta: dict = None):
    con = db_init()
    con.execute(
        "INSERT INTO events(ts,kind,input,output,meta) VALUES(?,?,?,?,?)",
        (time.strftime("%Y-%m-%dT%H:%M:%S"), kind, input_, output,
         json.dumps(meta or {}, ensure_ascii=False)),
    )
    con.commit()
    con.close()
    # Miroir JSON (append-only) → lu par PC YMÉNI
    with open(JSON_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "kind": kind, "input": input_, "output": output, "meta": meta or {}
        }, ensure_ascii=False) + "\n")


# --- ACTIONS ATOMIQUES -----------------------------------------------------
def speak(text: str):
    subprocess.run(["termux-tts-speak", "-l", "fr", text], check=False)


def torch(on: bool):
    subprocess.run(["termux-torch", "on" if on else "off"], check=False)


def vibrate(ms: int = 500):
    subprocess.run(["termux-vibrate", "-d", str(ms)], check=False)


def take_photo() -> str:
    out = PROJECT / "data" / f"photo_{int(time.time())}.jpg"
    subprocess.run(
        ["termux-camera-photo", "-c", "0", str(out)],
        check=False, timeout=10,
    )
    return str(out) if out.exists() else ""


def sos_pattern():
    """SOS morse via torche + vibration."""
    short, long_ = 0.2, 0.6
    pattern = [short]*3 + [long_]*3 + [short]*3
    for d in pattern:
        torch(True); vibrate(int(d*1000)); time.sleep(d)
        torch(False); time.sleep(0.15)


# --- INTENT MATCHING (rapide, sans LLM) -----------------------------------
INTENTS = [
    (r"\b(allume|ouvre).*(torche|lampe|flash)", "torch_on"),
    (r"\b(eteins|éteins|ferme|coupe).*(torche|lampe|flash)", "torch_off"),
    (r"\b(photo|prends une photo|capture)", "photo"),
    (r"\b(sos|alerte|au secours|danger)", "sos"),
    (r"\b(stop|annule|arrête|arrete)", "stop"),
    (r"\b(gaz|méthane|methane|monoxyde)", "gas_alert"),
]


def match_intent(text: str) -> str:
    t = text.lower()
    for pattern, intent in INTENTS:
        if re.search(pattern, t):
            return intent
    return ""


# --- OLLAMA ----------------------------------------------------------------
def ask_ollama(question: str) -> str:
    """Appel Ollama local en mode one-shot."""
    try:
        proc = subprocess.run(
            ["ollama", "run", OLLAMA_MODEL],
            input=f"{SYSTEM_PROMPT}\n\nQuestion: {question}\nRéponse:",
            capture_output=True, text=True, timeout=OLLAMA_TIMEOUT,
        )
        answer = proc.stdout.strip()
        # nettoyage : on coupe à la 1ère phrase
        answer = re.split(r"(?<=[.!?])\s", answer)[0]
        return answer or "Je n'ai pas de réponse."
    except subprocess.TimeoutExpired:
        return "Réflexion trop longue, je passe."
    except FileNotFoundError:
        return "Ollama indisponible."


# --- DISPATCH --------------------------------------------------------------
def handle(transcript: str):
    transcript = transcript.strip()
    if not transcript:
        return

    intent = match_intent(transcript)
    log_event("heard", input_=transcript, meta={"intent": intent or "ai"})

    if intent == "torch_on":
        torch(True); speak("Torche allumée.")
        log_event("action", output="torch_on")

    elif intent == "torch_off":
        torch(False); speak("Torche éteinte.")
        log_event("action", output="torch_off")

    elif intent == "photo":
        speak("Photo.")
        path = take_photo()
        speak("Photo enregistrée." if path else "Échec photo.")
        log_event("action", output="photo", meta={"path": path})

    elif intent == "sos":
        speak("Mode SOS activé.")
        vibrate(1500)
        sos_pattern()
        log_event("action", output="sos")

    elif intent == "gas_alert":
        speak("Alerte gaz. Quittez la zone immédiatement.")
        vibrate(2000)
        sos_pattern()
        log_event("alert", output="gas")

    elif intent == "stop":
        torch(False)
        speak("D'accord.")
        log_event("action", output="stop")

    else:
        # Question intelligente → IA
        speak("Je réfléchis.")
        answer = ask_ollama(transcript)
        speak(answer)
        log_event("ai", input_=transcript, output=answer)


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not text:
        # mode stdin pour test manuel
        text = sys.stdin.read().strip()
    handle(text)

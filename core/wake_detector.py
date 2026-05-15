#!/data/data/com.termux/files/usr/bin/env python3
"""
MENIX SENTINEL — Wake-word detector
====================================
Stratégie : Vosk (small-fr) + grammaire restreinte au vocabulaire MENIX.
Capture audio : termux-microphone-record en double-buffer pour ne RIEN manquer
                pendant la rotation des fichiers d'enregistrement.

Architecture :
    [mic Android] --(termux-microphone-record)--> wav chunk
        --> Vosk (grammar={menix, allume, eteins, torche, sos, gaz, photo, stop, oui, non})
        --> si "menix" détecté : on appelle router.py avec la suite de la phrase
        --> router.py s'occupe du reste (Ollama, TTS, action)

Auteur : MENIX team
"""

import json
import os
import queue
import shlex
import signal
import subprocess
import sys
import threading
import time
import wave
from pathlib import Path

# --- CONFIG ----------------------------------------------------------------
HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
PROJECT = HOME / "menix-sentinel"
VOSK_MODEL_PATH = PROJECT / "models" / "vosk-model-small-fr-0.22"
ROUTER_PATH = PROJECT / "core" / "router.py"
LOG_DB = PROJECT / "data" / "menix.db"

CHUNK_SECONDS = 2          # durée d'un enregistrement micro
OVERLAP_MS = 200           # chevauchement entre 2 chunks (anti-perte)
SAMPLE_RATE = 16000        # Vosk attend du 16 kHz mono
TMP_DIR = Path("/data/data/com.termux/files/usr/tmp/menix")
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Vocabulaire restreint = fiabilité maximale dans le bruit
GRAMMAR = json.dumps([
    "menix",
    "oui", "non",
    "allume", "eteins", "ouvre", "ferme",
    "torche", "lampe", "flash",
    "photo", "enregistre", "note",
    "sos", "alerte", "danger", "gaz",
    "stop", "annule",
    "quelle", "roche", "dureté", "minerai",
    "[unk]"
], ensure_ascii=False)

WAKE_WORDS = {"menix", "ménix", "menics", "ménics"}  # tolérance phonétique


# --- VOSK INIT -------------------------------------------------------------
try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    SetLogLevel(-1)  # silence
except ImportError:
    print("[FATAL] pip install vosk  (dans Termux)", file=sys.stderr)
    sys.exit(1)

if not VOSK_MODEL_PATH.exists():
    print(f"[FATAL] Modèle Vosk absent : {VOSK_MODEL_PATH}", file=sys.stderr)
    print("        Lance scripts/install_vosk_model.sh", file=sys.stderr)
    sys.exit(1)

print("[MENIX] Chargement modèle Vosk...", flush=True)
model = Model(str(VOSK_MODEL_PATH))
recognizer = KaldiRecognizer(model, SAMPLE_RATE, GRAMMAR)
recognizer.SetWords(True)
print("[MENIX] Modèle prêt. Écoute en cours...", flush=True)


# --- AUDIO CAPTURE (double-buffer termux-microphone-record) ---------------
audio_q: "queue.Queue[bytes]" = queue.Queue(maxsize=20)
_running = True


def record_chunk(path: Path, seconds: int) -> bool:
    """Enregistre un chunk via termux-microphone-record (bloquant)."""
    cmd = [
        "termux-microphone-record",
        "-f", str(path),
        "-l", str(seconds),
        "-r", str(SAMPLE_RATE),
        "-c", "1",          # mono
        "-e", "wav",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=seconds + 3)
        # Il faut explicitement arrêter sinon le fichier reste verrouillé
        subprocess.run(["termux-microphone-record", "-q"], capture_output=True, timeout=2)
        return path.exists() and path.stat().st_size > 1024
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"[MIC] échec enregistrement: {e}", file=sys.stderr)
        return False


def wav_to_pcm(path: Path) -> bytes:
    """Lit le WAV et renvoie le PCM 16-bit mono brut pour Vosk."""
    with wave.open(str(path), "rb") as wf:
        if wf.getframerate() != SAMPLE_RATE or wf.getnchannels() != 1:
            return b""
        return wf.readframes(wf.getnframes())


def capture_loop():
    """Producteur audio : alterne entre 2 fichiers pour ne rien perdre."""
    a = TMP_DIR / "buf_a.wav"
    b = TMP_DIR / "buf_b.wav"
    files = [a, b]
    idx = 0
    # NOTE : termux-microphone-record n'autorise qu'UN seul enregistrement
    # à la fois, donc le "double-buffer" se fait en série très rapide.
    # L'overlap réel vient du fait qu'on relance immédiatement après stop.
    while _running:
        target = files[idx % 2]
        if target.exists():
            target.unlink()
        ok = record_chunk(target, CHUNK_SECONDS)
        if ok:
            pcm = wav_to_pcm(target)
            if pcm:
                try:
                    audio_q.put(pcm, timeout=1)
                except queue.Full:
                    pass  # on jette plutôt que de bloquer
        idx += 1
        # Pas de sleep : on relance immédiatement pour minimiser le gap


# --- DETECTION LOOP --------------------------------------------------------
def call_router(transcript: str):
    """Délègue au cerveau (router.py)."""
    print(f"[MENIX] → router : {transcript!r}", flush=True)
    try:
        subprocess.Popen(
            ["python3", str(ROUTER_PATH), transcript],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        print(f"[ERR] router.py introuvable : {ROUTER_PATH}", file=sys.stderr)


def speak(text: str):
    """TTS Termux (réponse rapide 'Oui ?')."""
    subprocess.Popen(
        ["termux-tts-speak", "-l", "fr", text],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def listen_command(max_seconds: int = 4) -> str:
    """Après wake-word : on écoute la commande utilisateur."""
    cmd_file = TMP_DIR / "cmd.wav"
    if cmd_file.exists():
        cmd_file.unlink()
    if not record_chunk(cmd_file, max_seconds):
        return ""
    pcm = wav_to_pcm(cmd_file)
    rec = KaldiRecognizer(model, SAMPLE_RATE)  # grammaire libre ici
    rec.AcceptWaveform(pcm)
    res = json.loads(rec.FinalResult())
    return res.get("text", "").strip()


def detection_loop():
    """Consommateur audio : cherche le wake-word."""
    last_trigger = 0.0
    cooldown = 2.0  # secondes anti double-trigger
    while _running:
        try:
            pcm = audio_q.get(timeout=1)
        except queue.Empty:
            continue

        if recognizer.AcceptWaveform(pcm):
            res = json.loads(recognizer.Result())
        else:
            res = json.loads(recognizer.PartialResult())
            res["text"] = res.get("partial", "")

        text = res.get("text", "").lower().strip()
        if not text:
            continue

        # Wake-word ?
        if any(w in text.split() for w in WAKE_WORDS):
            now = time.time()
            if now - last_trigger < cooldown:
                continue
            last_trigger = now
            print(f"[WAKE] détecté dans : {text!r}", flush=True)
            speak("Oui ?")
            time.sleep(0.8)  # laisse le TTS finir
            command = listen_command()
            if command:
                call_router(command)
            else:
                speak("Je n'ai rien entendu.")
            recognizer.Reset()


# --- MAIN ------------------------------------------------------------------
def shutdown(signum, frame):
    global _running
    print("\n[MENIX] Arrêt demandé.", flush=True)
    _running = False
    subprocess.run(["termux-microphone-record", "-q"], capture_output=True)
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    t_cap = threading.Thread(target=capture_loop, daemon=True)
    t_det = threading.Thread(target=detection_loop, daemon=True)
    t_cap.start()
    t_det.start()

    # Heartbeat pour debug
    while _running:
        time.sleep(30)
        print(f"[MENIX] alive | queue={audio_q.qsize()}", flush=True)

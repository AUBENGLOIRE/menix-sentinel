#!/data/data/com.termux/files/usr/bin/env python3
"""
MENIX SENTINEL — Mock ESP32
============================
Simule un ESP32 qui pousse des données capteurs (gaz, température,
humidité, batterie) vers un fichier JSON partagé + déclenche
automatiquement router.py en cas de seuil dangereux.

Le fichier sensors_live.json est lu par :
  - l'app Android Kotlin (UI temps réel)
  - le router en cas d'alerte
"""

import json
import os
import random
import subprocess
import time
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/data/data/com.termux/files/home"))
PROJECT = HOME / "menix-sentinel"
LIVE_FILE = PROJECT / "data" / "sensors_live.json"
ROUTER = PROJECT / "core" / "router.py"
LIVE_FILE.parent.mkdir(parents=True, exist_ok=True)

# Seuils (inspirés normes minières)
THRESHOLDS = {
    "ch4_pct":   1.0,    # méthane > 1% = alerte (LIE = 5%)
    "co_ppm":    50,     # monoxyde de carbone
    "o2_pct":    19.5,   # oxygène insuffisant si <
    "temp_c":    40,
    "battery":   15,
}

state = {
    "ch4_pct": 0.2,
    "co_ppm": 5,
    "o2_pct": 20.9,
    "temp_c": 22.0,
    "humidity": 60,
    "battery": 95,
    "ts": "",
}

last_alert = {}
ALERT_COOLDOWN = 60  # s


def step():
    """Évolution réaliste + petites injections d'événements."""
    state["ch4_pct"] = max(0, state["ch4_pct"] + random.uniform(-0.05, 0.08))
    state["co_ppm"]  = max(0, state["co_ppm"]  + random.randint(-2, 3))
    state["o2_pct"]  = max(15, min(21, state["o2_pct"] + random.uniform(-0.1, 0.05)))
    state["temp_c"]  = state["temp_c"] + random.uniform(-0.2, 0.3)
    state["humidity"] = max(20, min(95, state["humidity"] + random.randint(-1, 1)))
    state["battery"] = max(0, state["battery"] - random.choice([0,0,0,1]))
    state["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")


def check_alerts():
    now = time.time()
    triggers = []
    if state["ch4_pct"] >= THRESHOLDS["ch4_pct"]:
        triggers.append(("gas",  f"alerte gaz méthane {state['ch4_pct']:.1f} pourcent"))
    if state["co_ppm"]  >= THRESHOLDS["co_ppm"]:
        triggers.append(("co",   f"alerte monoxyde de carbone {state['co_ppm']} ppm"))
    if state["o2_pct"]  <= THRESHOLDS["o2_pct"]:
        triggers.append(("o2",   f"alerte oxygène faible {state['o2_pct']:.1f} pourcent"))
    if state["temp_c"]  >= THRESHOLDS["temp_c"]:
        triggers.append(("temp", f"alerte température {state['temp_c']:.0f} degrés"))
    if state["battery"] <= THRESHOLDS["battery"]:
        triggers.append(("bat",  f"batterie faible {state['battery']} pourcent"))

    for kind, msg in triggers:
        if now - last_alert.get(kind, 0) < ALERT_COOLDOWN:
            continue
        last_alert[kind] = now
        print(f"[MOCK] ⚠ {kind}: {msg}", flush=True)
        # Pousse vers router comme si MENIX avait entendu
        subprocess.Popen(["python3", str(ROUTER), msg],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def write_live():
    tmp = LIVE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    tmp.replace(LIVE_FILE)  # écriture atomique → lecteur ne voit jamais à moitié


def main():
    print("[MOCK] ESP32 simulé démarré.", flush=True)
    while True:
        step()
        write_live()
        check_alerts()
        time.sleep(2)


if __name__ == "__main__":
    main()

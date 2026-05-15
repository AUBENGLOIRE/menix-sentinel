# MENIX SENTINEL

> Assistant vocal et de sécurité embarqué pour mineurs en galerie.
> 100 % offline, tourne sur un Android dans un boîtier durci.

## Architecture

```
              ┌──────────────────────────────────────┐
              │   Mineur dit "MENIX, allume torche"  │
              └───────────────┬──────────────────────┘
                              │ micro
                              ▼
        ┌────────────────────────────────────────────┐
        │ wake_detector.py  (Vosk + grammaire FR)    │ ← écoute continue
        │   - détecte "MENIX"                        │
        │   - répond "Oui ?" (TTS)                   │
        │   - capture la commande                    │
        └───────────────┬────────────────────────────┘
                        │ stdin / argv
                        ▼
        ┌────────────────────────────────────────────┐
        │ router.py  (le cerveau)                    │
        │   intent regex  →  action directe          │
        │   sinon         →  Ollama qwen2.5:1.5b     │
        └────┬─────────────────────────────┬─────────┘
             │                             │
             ▼                             ▼
   termux-torch / vibrate /         SQLite + JSON
   tts-speak / camera-photo         (mémoire mission)
                                          │
                                          ▼
                                    export USB → PC YMÉNI

   ┌─────────────────────────┐         ┌─────────────────────────┐
   │ esp32_mock.py           │ ───────►│ sensors_live.json       │
   │ (capteurs simulés)      │         └────────────┬────────────┘
   └─────────────────────────┘                      │ lecture 1 Hz
                                                    ▼
                                          ┌────────────────────┐
                                          │ App Android Kotlin │
                                          │ (UI, boutons)      │
                                          └────────────────────┘
```

## Installation (Termux)

```bash
git clone <ton-repo> ~/menix-sentinel
cd ~/menix-sentinel
bash scripts/install.sh
```

Activer manuellement les permissions Android pour Termux:API
(Microphone, Caméra, Stockage).

## Lancement

```bash
bash scripts/start_menix.sh         # démarre wake_detector + mock ESP32 dans tmux
tmux attach -t menix                # voir les logs (Ctrl+b puis n pour navig.)
```

## Boot automatique

Installer **Termux:Boot** depuis F-Droid, puis :

```bash
mkdir -p ~/.termux/boot
cp ~/menix-sentinel/scripts/boot ~/.termux/boot/menix
chmod +x ~/.termux/boot/menix
```

## App Android

Voir `android-app/README.md`. Build dans Android Studio, installer l'APK,
relier au dossier Termux par lien symbolique :

```bash
ln -s ~/menix-sentinel/data /sdcard/menix-sentinel/data
```

## Fin de mission — export

```bash
bash scripts/export_mission.sh
# → ~/storage/shared/MENIX_export/mission_<timestamp>/
# Branche le câble USB, copie ce dossier vers le PC YMÉNI Mining.
```

## Test rapide sans micro

```bash
python3 core/router.py "allume la torche"
python3 core/router.py "quelle roche a une dureté de 7 ?"
python3 core/router.py "alerte gaz méthane"
```

## Composants livrés

| # | Fichier                          | Rôle                                  |
|---|----------------------------------|---------------------------------------|
| 1 | `core/wake_detector.py`          | Écoute continue + wake-word "MENIX"   |
| 2 | `core/router.py`                 | Cerveau : intent + Ollama + actions   |
| 3 | `mock/esp32_mock.py`             | Capteurs simulés + alertes auto       |
| 4 | `scripts/install.sh`             | Setup Termux complet                  |
| 5 | `scripts/install_vosk_model.sh`  | Téléchargement modèle Vosk small-fr   |
| 6 | `scripts/start_menix.sh`         | Lancement tmux                        |
| 7 | `scripts/stop_menix.sh`          | Arrêt propre                          |
| 8 | `scripts/boot`                   | Boot auto via Termux:Boot             |
| 9 | `scripts/export_mission.sh`      | Export USB pour PC YMÉNI              |
| 10| `android-app/`                   | UI Kotlin + boutons + capteurs live   |

## Limitations connues & solutions

| Limite                                    | Solution dans le code                       |
|-------------------------------------------|---------------------------------------------|
| `termux-microphone-record` un seul à la fois | Boucle serrée + `Reset()` Vosk à chaque trigger |
| Latence chunk de 2 s                      | Réduire `CHUNK_SECONDS` (mais + de CPU)     |
| Vosk en grammaire restreinte rate les mots hors-vocab | C'est volontaire : on optimise pour le wake-word ; la commande post-wake est en grammaire libre |
| Permissions Android refusées silencieusement | Vérifier dans Réglages > Apps > Termux:API  |

## Roadmap

- [ ] Remplacer `termux-microphone-record` par un binding natif AudioRecord
      (via mini app Kotlin qui pipe vers Termux) si la latence est trop forte.
- [ ] Vraie carte ESP32 avec MQ-4 (méthane) + MQ-7 (CO) + DHT22.
- [ ] Sync mission via 4G/WiFi quand le mineur revient en surface.

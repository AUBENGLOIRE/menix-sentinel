#!/data/data/com.termux/files/usr/bin/env bash
# MENIX SENTINEL — Installation complète (Termux ARM64)
set -e

echo "=== MENIX install ==="

# 1. Permissions Termux
termux-setup-storage || true

# 2. Paquets système
pkg update -y
pkg install -y python python-pip git wget unzip sox termux-api ffmpeg sqlite

# 3. Python deps
pip install --upgrade pip
pip install vosk

# 4. Modèle Vosk small-fr (~40 Mo)
bash "$(dirname "$0")/install_vosk_model.sh"

# 5. Permissions Android (à valider à la main au 1er run)
echo
echo ">>> Va dans : Paramètres Android > Apps > Termux:API > Autorisations"
echo ">>> Active : Microphone, Caméra, Stockage, Position"
echo
echo "=== Installation OK ==="

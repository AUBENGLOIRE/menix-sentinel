#!/data/data/com.termux/files/usr/bin/env bash
set -e
MODEL_DIR="$HOME/menix-sentinel/models"
MODEL_NAME="vosk-model-small-fr-0.22"
URL="https://alphacephei.com/vosk/models/${MODEL_NAME}.zip"

mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

if [ -d "$MODEL_NAME" ]; then
    echo "[VOSK] Modèle déjà présent."
    exit 0
fi

echo "[VOSK] Téléchargement ${MODEL_NAME} (~40 Mo)..."
wget -O model.zip "$URL"
unzip -q model.zip
rm model.zip
echo "[VOSK] OK : $MODEL_DIR/$MODEL_NAME"

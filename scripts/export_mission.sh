#!/data/data/com.termux/files/usr/bin/env bash
# Exporte la mission courante vers ~/storage/shared/MENIX_export/
# pour transfert USB vers le PC YMÉNI Mining.
set -e

TS=$(date +%Y%m%d_%H%M%S)
SRC="$HOME/menix-sentinel/data"
DST="$HOME/storage/shared/MENIX_export/mission_$TS"

mkdir -p "$DST"

# 1. Dump SQLite → JSON propre
python3 - <<PY
import sqlite3, json, pathlib
con = sqlite3.connect("$SRC/menix.db")
con.row_factory = sqlite3.Row
rows = [dict(r) for r in con.execute("SELECT * FROM events ORDER BY id")]
pathlib.Path("$DST/events.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=2)
)
print(f"[EXPORT] {len(rows)} événements exportés")
PY

# 2. Copies brutes
cp -f "$SRC/events.json"        "$DST/events_stream.jsonl" 2>/dev/null || true
cp -f "$SRC/sensors_live.json"  "$DST/" 2>/dev/null || true
cp -f "$SRC"/photo_*.jpg        "$DST/" 2>/dev/null || true
cp -f "$SRC/menix.db"           "$DST/" 2>/dev/null || true

# 3. Manifest
cat > "$DST/manifest.json" <<EOF
{
  "mission_id": "mission_$TS",
  "device": "MENIX-SENTINEL",
  "exported_at": "$(date -Iseconds)",
  "files": $(ls "$DST" | python3 -c "import sys,json;print(json.dumps(sys.stdin.read().split()))")
}
EOF

echo "[EXPORT] Mission disponible : $DST"
echo "         Branche le câble USB et copie ce dossier vers le PC."

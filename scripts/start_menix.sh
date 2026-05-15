#!/data/data/com.termux/files/usr/bin/env bash
# Démarre tous les composants MENIX dans une session tmux.
# Permet de garder le système actif et de voir les 3 logs en parallèle.

cd "$HOME/menix-sentinel"
mkdir -p data logs

# Empêche le téléphone de s'endormir pendant la session
termux-wake-lock

SESSION="menix"

if ! command -v tmux >/dev/null; then
    pkg install -y tmux
fi

tmux kill-session -t $SESSION 2>/dev/null || true
tmux new-session  -d -s $SESSION -n wake  "python3 core/wake_detector.py 2>&1 | tee logs/wake.log"
tmux new-window   -t $SESSION:1 -n mock   "python3 mock/esp32_mock.py     2>&1 | tee logs/mock.log"
tmux new-window   -t $SESSION:2 -n shell  "bash"

echo "[MENIX] Session tmux 'menix' lancée."
echo "        tmux attach -t menix     # pour voir les logs"
echo "        bash scripts/stop_menix.sh   # pour arrêter"

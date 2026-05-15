#!/data/data/com.termux/files/usr/bin/env bash
tmux kill-session -t menix 2>/dev/null || true
termux-microphone-record -q 2>/dev/null || true
termux-torch off 2>/dev/null || true
termux-wake-unlock 2>/dev/null || true
echo "[MENIX] Stoppé."

#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

REMOTE="rwfunder@100.67.114.104"
REMOTE_DB="/home/rwfunder/文件/tradingbot/trading_bot/performance.db"
LOCAL_DB="$SCRIPT_DIR/performance.db"

echo "=== quantDashboard ==="
echo "[1/3] Pulling performance.db from rwUbuntu..."

if command -v sshpass &> /dev/null; then
    sshpass -p "0602" scp "$REMOTE:$REMOTE_DB" "$LOCAL_DB"
else
    python "$SCRIPT_DIR/pull_db.py"
fi

echo "      Done ($(du -h "$LOCAL_DB" | cut -f1))"

echo "[2/3] Building dashboard..."
python "$SCRIPT_DIR/build_dashboard.py" "$@"

echo "[3/3] Opening dashboard..."
start dashboard.html

echo "=== Done ==="

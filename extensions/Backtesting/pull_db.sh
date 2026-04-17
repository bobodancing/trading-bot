#!/bin/bash
set -e
# pull_db.sh — 從 rwUbuntu 拉取 performance.db
REMOTE="rwfunder@100.67.114.104"
REMOTE_PATH="/home/rwfunder/文件/tradingbot/trading_bot/performance.db"
LOCAL_PATH="$(dirname "$0")/performance.db"

echo "Pulling perf_db from $REMOTE..."
scp "$REMOTE:$REMOTE_PATH" "$LOCAL_PATH"
echo "Done: $LOCAL_PATH"

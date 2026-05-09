#!/bin/bash
# Jarvis Telegram bridge startup script
# Usage: ./cc_bridge.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$SCRIPT_DIR/.env" ]; then
  export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  echo "Error: TELEGRAM_BOT_TOKEN not set. Add it to .env or export it."
  exit 1
fi

pip install python-telegram-bot --quiet

echo "Starting Jarvis Telegram bridge (auto-restart enabled)..."
while true; do
  caffeinate -i python3 "$SCRIPT_DIR/telegram_bridge.py"
  echo "[$(date)] Bridge crashed, restarting in 5s..."
  sleep 5
done

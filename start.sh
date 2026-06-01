#!/bin/bash
# Cypher Bot — RAM launcher
# Usage: bash start.sh
# Run from the project folder: cd ~/cypher && bash start.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Detect Python version automatically
PY_VER=$(python3 -c "import sys; print(f'python{sys.version_info.major}.{sys.version_info.minor}')")
STDLIB=$(python3 -c "import sysconfig; print(sysconfig.get_path('stdlib'))")
RAM_BASE="/dev/shm/$PY_VER"

echo "=== Cypher Bot Launcher ==="
echo "Python  : $PY_VER"
echo "stdlib  : $STDLIB"
echo "RAM disk: $RAM_BASE"

# Kill any previously running instance
if pkill -0 -f "bot.main" 2>/dev/null; then
    echo "Stopping old bot process..."
    pkill -9 -f "bot.main" 2>/dev/null || true
    sleep 1
fi

# Sync stdlib to RAM (skipped if already cached)
if [ ! -f "$RAM_BASE/enum.py" ]; then
    echo "Copying stdlib → RAM disk..."
    mkdir -p "$RAM_BASE"
    cp -r "$STDLIB"/* "$RAM_BASE/" 2>/dev/null || true
else
    echo "stdlib already in RAM, skipping."
fi

# Sync site-packages to RAM (skipped if already cached)
if [ ! -d "$RAM_BASE/site-packages/aiogram" ]; then
    echo "Copying site-packages → RAM disk..."
    mkdir -p "$RAM_BASE/site-packages"
    # Try all common locations
    for SP in \
        "$STDLIB/site-packages" \
        "/usr/local/lib/$PY_VER/dist-packages" \
        "/usr/lib/$PY_VER/dist-packages" \
        "$HOME/.local/lib/$PY_VER/site-packages"; do
        if [ -d "$SP" ]; then
            cp -rn "$SP"/. "$RAM_BASE/site-packages/" 2>/dev/null || true
        fi
    done
else
    echo "site-packages already in RAM, skipping."
fi

# Launch bot in background
echo "Starting bot in background..."
export PYTHONPATH="$RAM_BASE:$RAM_BASE/site-packages"
nohup python3 -B -u -m bot.main >> bot_run.log 2>&1 &
BOT_PID=$!
disown $BOT_PID

echo ""
echo "Bot started! PID=$BOT_PID"
echo "Logs: tail -f $SCRIPT_DIR/bot_run.log"
echo "      tail -f $SCRIPT_DIR/bot_errors.log"
echo "Stop: kill $BOT_PID  OR  pkill -f bot.main"

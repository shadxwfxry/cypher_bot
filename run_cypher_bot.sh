#!/bin/bash
# ======================================================================
# Cypher Bot Premium Interactive Linux Launcher
# Coordinates automatic virtual env activation, concurrent processes,
# pip dependencies installations, and clean shutdown targets.
# ======================================================================

# Explicitly set project root directory into Python search path to guarantee absolute imports reliability
export PYTHONPATH="$(cd "$(dirname "$0")" && pwd)"

detect_venv() {
    echo ""
    echo "[*] Scanning for active Python Virtual Environments..."
    if [ -f ".venv/bin/activate" ]; then
        echo "[+] Found active environment in .venv"
        source .venv/bin/activate
    elif [ -f "venv/bin/activate" ]; then
        echo "[+] Found active environment in venv"
        source venv/bin/activate
    elif [ -f "env/bin/activate" ]; then
        echo "[+] Found active environment in env"
        source env/bin/activate
    else
        echo "[-] No virtual environment detected. Operating with system Python interpreter."
        echo "[!] Tip: If imports fail, choose Option [4] from the main menu to initialize .venv and install dependencies."
    fi
}

show_menu() {
    clear
    echo "======================================================================"
    echo "**********************************************************************"
    echo "**                                                                  **"
    echo "**                      CYPHER BOT SYSTEM MENU                      **"
    echo "**                                                                  **"
    echo "**********************************************************************"
    echo "======================================================================"
    echo "                  CYPHER BOT :: SYSTEM LAUNCHER"
    echo "======================================================================"
    echo ""
    echo "[1] Run Bot and Export Worker (Concurrent Processes)"
    echo "[2] Run Bot Only (Main runner + Webhook Web-Server)"
    echo "[3] Run Background Export Worker Only"
    echo "[4] Install / Update Dependencies (requirements.txt)"
    echo "[5] Exit"
    echo ""
    echo "======================================================================"
    read -p "Choose an option [1-5]: " opt
    
    case $opt in
        1) launch_all ;;
        2) launch_bot ;;
        3) launch_worker ;;
        4) install_deps ;;
        5) exit_app ;;
        *) show_menu ;;
    esac
}

launch_all() {
    clear
    echo "======================================================================"
    echo "  Launching Cypher Bot and Background Worker in Concurrent Mode"
    echo "======================================================================"
    detect_venv
    echo ""
    echo "[+] Starting Background Export Worker in the background..."
    echo "[+] Logs redirecting to: worker_run.log"
    python3 bot/worker.py > worker_run.log 2>&1 &
    WORKER_PID=$!
    
    # Ensure worker process is terminated when the script exits
    trap "kill $WORKER_PID 2>/dev/null" EXIT
    
    echo "[+] Launching Telegram Bot and Webhook Server on port 8080..."
    echo ""
    python3 bot/main.py
    
    # Kill the worker after bot finishes if trap wasn't triggered
    kill $WORKER_PID 2>/dev/null || true
    trap - EXIT
    
    read -p "Press Enter to return to menu..."
    show_menu
}

launch_bot() {
    clear
    echo "======================================================================"
    echo "  Launching Telegram Bot and Webhook Server Only"
    echo "======================================================================"
    detect_venv
    echo ""
    python3 bot/main.py
    read -p "Press Enter to return to menu..."
    show_menu
}

launch_worker() {
    clear
    echo "======================================================================"
    echo "  Launching Background Export Task Worker Only"
    echo "======================================================================"
    detect_venv
    echo ""
    python3 bot/worker.py
    read -p "Press Enter to return to menu..."
    show_menu
}

install_deps() {
    clear
    echo "======================================================================"
    echo "  Installing Dependencies from requirements.txt"
    echo "======================================================================"
    
    # Check if any standard venv folder exists
    if [ ! -f ".venv/bin/activate" ] && [ ! -f "venv/bin/activate" ] && [ ! -f "env/bin/activate" ]; then
        echo "[*] No virtual environment found. Initializing one in .venv..."
        python3 -m venv .venv
    fi
    
    detect_venv
    
    echo ""
    echo "[+] Upgrading pip to latest version..."
    python3 -m pip install --upgrade pip
    echo "[+] Fetching required packages..."
    pip install -r requirements.txt
    echo ""
    echo "[+] Installation completed successfully!"
    read -p "Press Enter to return to menu..."
    show_menu
}

exit_app() {
    clear
    echo "Thank you for using Cypher Bot. Keep it secure!"
    sleep 2
    exit 0
}

# Start script by showing menu
show_menu

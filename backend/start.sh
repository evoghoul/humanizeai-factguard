#!/bin/bash
echo "=========================================="
echo " Starting HumanizeAI 14B + ngrok Tunnel   "
echo "=========================================="

# 1. Stop any old instances
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "python api_14b.py" 2>/dev/null || true
pkill -f "ngrok" 2>/dev/null || true
sleep 1

# 2. Ensure ngrok binary is present and executable
if [ ! -f "./ngrok" ] && [ -f "ngrok.tgz" ]; then
    tar -xzf ngrok.tgz 2>/dev/null || true
fi
chmod +x ./ngrok 2>/dev/null || true

NGROK_BIN="./ngrok"
if [ ! -f "./ngrok" ] && command -v ngrok >/dev/null 2>&1; then
    NGROK_BIN="ngrok"
fi

# 3. Pull latest api_14b.py
echo "Fetching latest api_14b.py from GitHub..."
curl -s -O https://raw.githubusercontent.com/evoghoul/humanizeai-factguard/main/backend/api_14b.py

# 4. Launch 14B API in background
echo "Starting 14B Model Server (api_14b.py)..."
nohup python api_14b.py > api.log 2>&1 &

# 5. Launch permanent ngrok tunnel
echo "Starting permanent ngrok tunnel using $NGROK_BIN..."
nohup $NGROK_BIN http --domain=resonate-trimester-glade.ngrok-free.dev 8000 > ngrok.log 2>&1 &

sleep 2
echo ""
echo ">>> Checking Running Processes:"
ps aux | grep -E "python api_14b.py|ngrok" | grep -v grep

echo ""
echo ">>> Check logs with:"
echo "    tail -f api.log"
echo "    tail -f ngrok.log"
echo "=========================================="


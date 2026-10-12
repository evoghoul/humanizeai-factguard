#!/bin/bash
echo "=================================================="
echo " Starting HumanizeAI 14B Model & Tunnel Server   "
echo "=================================================="

# 1. Stop any stale instances
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "python api_14b.py" 2>/dev/null || true
pkill -f "ngrok" 2>/dev/null || true
sleep 1

# 2. Ensure ngrok binary is present and executable
if [ ! -f "./ngrok" ] && [ -f "ngrok.tgz" ]; then
    echo "Unpacking ngrok binary..."
    tar -xzf ngrok.tgz 2>/dev/null || true
fi
chmod +x ./ngrok 2>/dev/null || true

NGROK_BIN="./ngrok"
if [ ! -f "./ngrok" ] && command -v ngrok >/dev/null 2>&1; then
    NGROK_BIN="ngrok"
fi

# 3. Pull latest api_14b.py
echo "Pulling latest api_14b.py..."
curl -s -O https://raw.githubusercontent.com/evoghoul/humanizeai-factguard/main/backend/api_14b.py

# 4. Launch 14B API in background
echo "[1/3] Starting 14B API Server..."
nohup python api_14b.py > api.log 2>&1 &

# 5. Launch permanent ngrok tunnel in background
echo "[2/3] Starting permanent ngrok tunnel..."
nohup $NGROK_BIN http --domain=resonate-trimester-glade.ngrok-free.dev 8000 > ngrok.log 2>&1 &

# 6. Wait for model warm-up (~35-45 seconds)
echo "[3/3] Loading 14B model into GPU VRAM (takes ~40 seconds)..."
READY=0
for i in {1..35}; do
    if curl -s http://127.0.0.1:8000/health | grep -q '"loaded":true'; then
        READY=1
        break
    fi
    printf "."
    sleep 2
done

echo ""
if [ $READY -eq 1 ]; then
    echo "=================================================================="
    echo " 🚀 HumanizeAI 14B is 100% LIVE and READY!"
    echo " Tunnel:   https://resonate-trimester-glade.ngrok-free.dev"
    echo " Frontend: https://humanizeai-factguard.vercel.app"
    echo "=================================================================="
else
    echo "Notice: Still initializing. Run 'tail -n 20 api.log' to check progress."
fi


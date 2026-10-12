#!/bin/bash
echo "=================================================="
echo " Starting HumanizeAI 14B Model & Tunnel Server   "
echo "=================================================="

# Check GPU status
if command -v nvidia-smi >/dev/null 2>&1; then
    GPU_NAME=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -n 1)
    echo "Hardware: GPU Detected -> $GPU_NAME"
else
    echo "⚠️ Notice: nvidia-smi not found. Checking system environment..."
fi

# 1. Force-kill any stale instances and free GPU VRAM
pkill -9 -f "api_14b" 2>/dev/null || true
pkill -9 -f "uvicorn" 2>/dev/null || true
pkill -9 -f "ngrok" 2>/dev/null || true
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

# 6. Wait for model warm-up (up to 100 seconds)
echo "[3/3] Loading 14B model into GPU VRAM..."
READY=0
for i in {1..50}; do
    if curl -s http://127.0.0.1:8000/health 2>/dev/null | grep -q '"loaded":true'; then
        READY=1
        break
    fi
    # Check if server process exited unexpectedly
    if ! pgrep -f "api_14b" >/dev/null 2>&1; then
        echo ""
        echo "❌ Server process exited unexpectedly. Log output:"
        tail -n 25 api.log
        exit 1
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
    echo "Notice: Still initializing. Current log output:"
    tail -n 10 api.log
    echo "Run 'tail -f api.log' to monitor completion."
fi


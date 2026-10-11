#!/bin/bash
echo "=========================================="
echo " Starting HumanizeAI 14B + ngrok Tunnel   "
echo "=========================================="

# 1. Stop any old instances
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "ngrok" 2>/dev/null || true
sleep 1

# 2. Pull latest api_14b.py
echo "Fetching latest api_14b.py from GitHub..."
curl -s -O https://raw.githubusercontent.com/evoghoul/humanizeai-factguard/main/backend/api_14b.py

# 3. Launch 14B API in background
echo "Starting 14B Model Server (api_14b.py)..."
nohup python api_14b.py > api.log 2>&1 &

# 4. Launch permanent ngrok tunnel
echo "Starting permanent ngrok tunnel..."
nohup ./ngrok http --domain=resonate-trimester-glade.ngrok-free.dev 8000 > ngrok.log 2>&1 &

echo ""
echo ">>> All services launched in background!"
echo ">>> Check progress with: tail -f api.log"
echo "=========================================="

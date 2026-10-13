"""Convenience script to test model and backend connectivity for HumanizeAI-FactGuard."""

import os
import sys
import httpx
from pathlib import Path

# Load settings if available
sys.path.insert(0, str(Path(__file__).parent))
try:
    from app.core.config import settings
    provider_url = settings.MODEL_PROVIDER_URL
    provider_type = settings.MODEL_PROVIDER_TYPE
    has_gemini = bool(settings.GEMINI_API_KEY)
except Exception:
    provider_url = "https://resonate-trimester-glade.ngrok-free.dev"
    provider_type = "lightning"
    has_gemini = False

print("=" * 70)
print("HUMANIZEAI-FACTGUARD — MODEL & BACKEND STATUS CHECK")
print("=" * 70)

print(f"Configured Provider Type: {provider_type}")
print(f"Configured Provider URL:  {provider_url}")
print(f"Gemini API Key Loaded:    {'YES' if has_gemini else 'NO'}")
print("-" * 70)

sample_text = (
    "The quarterly earnings call took place on October 14, 2025. "
    "Total revenue rose by 14.8% to $12.4M, whereas operating margins did not decline below 21%. "
    "Dr. Aris Thorne stated that product delivery would not commence before Q1 2026."
)

# 1. Check Local Backend
print("[1] Checking Local FastAPI Backend (port 8000)...")
try:
    r = httpx.get("http://localhost:8000/api/config", timeout=3.0)
    print(f"    -> ONLINE (Status {r.status_code})")
except Exception:
    print("    -> OFFLINE (Run 'uvicorn app.main:app --port 8000 --reload' in backend/)")

# 2. Check 14B Model Endpoint
print(f"[2] Checking 14B GPU Model Endpoint ({provider_url})...")
try:
    target = provider_url.rstrip("/")
    if not target.endswith("/humanize"):
        target = f"{target}/humanize"
    res = httpx.post(
        target,
        json={"text": sample_text, "tone": "Professional", "strength": "Medium"},
        headers={"ngrok-skip-browser-warning": "true", "User-Agent": "HumanizeAI/1.0"},
        timeout=15.0
    )
    if res.status_code == 200:
        data = res.json()
        print("    -> ONLINE & RESPONDING!")
        print("    Rewrite snippet:", (data.get("rewrite") or "")[:120], "...")
        print("    Warnings:", data.get("warnings", []))
    else:
        print(f"    -> RETURNED HTTP {res.status_code}")
except httpx.ConnectError:
    print("    -> OFFLINE (The GPU instance or tunnel is not currently running)")
except httpx.TimeoutException:
    print("    -> TIMED OUT (GPU may be waking up or busy)")
except Exception as e:
    print(f"    -> UNREACHABLE ({type(e).__name__}: {e})")

print("-" * 70)
print("Ready. See instructions in terminal or chat.")
print("=" * 70)

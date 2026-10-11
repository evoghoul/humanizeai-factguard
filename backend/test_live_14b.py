import httpx

sample_text = "The quarterly earnings call took place on October 14, 2025. Total revenue rose by 14.8% to $12.4M, whereas operating margins did not decline below 21%. Dr. Aris Thorne stated that product delivery would not commence before Q1 2026 unless client approvals are finalized."

print("--- Testing Live 14B Model (Direct over Tunnel) ---")
tunnel_url = "https://pmc-mhz-fifty-song.trycloudflare.com/humanize"
res = httpx.post(tunnel_url, json={"text": sample_text}, timeout=60.0)
print(f"Status: {res.status_code}")
data = res.json()
print("14B Rewrite:\n", data.get("rewrite"))
print("Warnings:\n", data.get("warnings"))

print("\n--- Testing Full End-to-End Stack (Vite -> Backend -> 14B -> FactGuard) ---")
vite_url = "http://localhost:8443/humanize"
res2 = httpx.post(vite_url, json={"text": sample_text}, timeout=60.0)
print(f"Status: {res2.status_code}")
data2 = res2.json()
print("End-to-End Rewrite:\n", data2.get("rewrite"))
print("Warnings:\n", data2.get("warnings"))
print("Needs Review:", data2.get("needs_review"))

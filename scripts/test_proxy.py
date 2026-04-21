"""Verify the proxy is working and returning a Mexican IP."""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

PROXY_HOST = os.getenv("PROXY_HOST", "geo.iproyal.com")
PROXY_PORT = os.getenv("PROXY_PORT", "12321")
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")

proxy_url = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"

print(f"Testing proxy: {PROXY_HOST}:{PROXY_PORT}")
print(f"User: {PROXY_USER}")

with httpx.Client(proxy=proxy_url, timeout=30.0) as client:
    r = client.get("https://ipinfo.io/json")
    data = r.json()
    print("\n--- Response ---")
    print(f"IP:       {data.get('ip')}")
    print(f"City:     {data.get('city')}")
    print(f"Region:   {data.get('region')}")
    print(f"Country:  {data.get('country')}")
    print(f"Org:      {data.get('org')}")

    if data.get("country") == "MX":
        print("\n✅ SUCCESS: Mexican IP confirmed")
    else:
        print(f"\n❌ FAILED: Expected MX, got {data.get('country')}")

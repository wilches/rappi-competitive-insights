"""Verify city-targeted proxy sessions return the right city.
Works whether IPRoyal expects flags appended to the username or the password.
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

PROXY_HOST = os.getenv("PROXY_HOST", "geo.iproyal.com")
PROXY_PORT = os.getenv("PROXY_PORT", "12321")
BASE_USER = os.getenv("PROXY_USER")
BASE_PASS = os.getenv("PROXY_PASS")
FLAG_TARGET = os.getenv("PROXY_FLAG_TARGET", "password").lower()  # "username" or "password"

CITIES = {
    "cdmx": "mexicocity",
    "gdl":  "guadalajara",
    "mty":  "monterrey",
}

def build_proxy_url(city_flag: str, session_id: str, lifetime_min: int = 5) -> str:
    flags = f"_country-mx_city-{city_flag}_session-{session_id}_lifetime-{lifetime_min}m"
    if FLAG_TARGET == "username":
        user = BASE_USER + flags
        pwd = BASE_PASS
    else:  # default: password
        user = BASE_USER
        pwd = BASE_PASS + flags
    return f"http://{user}:{pwd}@{PROXY_HOST}:{PROXY_PORT}"

print(f"Flag target field: {FLAG_TARGET}\n")

for code, city_flag in CITIES.items():
    proxy_url = build_proxy_url(city_flag, session_id=f"test{code}")
    print(f"--- Testing city flag: {city_flag} ({code}) ---")
    try:
        with httpx.Client(proxy=proxy_url, timeout=30.0) as client:
            r = client.get("https://ipinfo.io/json")
            data = r.json()
            print(f"  IP:      {data.get('ip')}")
            print(f"  City:    {data.get('city')}")
            print(f"  Region:  {data.get('region')}")
            print(f"  Country: {data.get('country')}")
            print(f"  Org:     {data.get('org')}\n")
    except Exception as e:
        print(f"  ❌ FAILED: {e}\n")

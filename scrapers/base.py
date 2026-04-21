"""Shared utilities for all platform scrapers."""
import os
import random
import time
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ───── Configuration ─────
PROXY_HOST = os.getenv("PROXY_HOST", "geo.iproyal.com")
PROXY_PORT = os.getenv("PROXY_PORT", "12321")
BASE_USER = os.getenv("PROXY_USER")
BASE_PASS = os.getenv("PROXY_PASS")
FLAG_TARGET = os.getenv("PROXY_FLAG_TARGET", "password").lower()

MIN_DELAY = float(os.getenv("MIN_DELAY_SECONDS", "3"))
MAX_DELAY = float(os.getenv("MAX_DELAY_SECONDS", "8"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))


# ───── Logging ─────
def setup_logger(name: str) -> logging.Logger:
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler(f"logs/{name}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


# ───── Proxy URL builder ─────
def build_proxy_url(city: str, session_id: Optional[str] = None, lifetime_min: int = 10) -> str:
    """Build an IPRoyal proxy URL with city targeting + sticky session.

    city: our internal city code — 'cdmx', 'gdl', 'mty'
    """
    city_map = {"cdmx": "mexicocity", "gdl": "guadalajara", "mty": "monterrey"}
    city_flag = city_map.get(city, "mexicocity")
    if session_id is None:
        session_id = uuid.uuid4().hex[:10]
    flags = f"_country-mx_city-{city_flag}_session-{session_id}_lifetime-{lifetime_min}m"

    if FLAG_TARGET == "username":
        user = BASE_USER + flags
        pwd = BASE_PASS
    else:
        user = BASE_USER
        pwd = BASE_PASS + flags
    return f"http://{user}:{pwd}@{PROXY_HOST}:{PROXY_PORT}"


def polite_sleep():
    """Random delay between requests to be a good citizen."""
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


# ───── Unified observation schema ─────
@dataclass
class Observation:
    """One row in our final CSV. Matches the schema from the plan."""
    observation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    run_id: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    platform: str = ""
    city: str = ""
    zone_type: str = ""
    address_id: str = ""
    address_label: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    store_id: str = ""
    store_name: str = ""
    product_canonical: Optional[str] = None
    product_raw_name: Optional[str] = None
    product_price: Optional[float] = None
    product_price_final: Optional[float] = None
    delivery_fee: Optional[float] = None
    service_fee: Optional[float] = None
    eta_min: Optional[int] = None
    eta_max: Optional[int] = None
    promo_present: Optional[bool] = None
    promo_description: Optional[str] = None
    store_available: Optional[bool] = None
    currency: str = "MXN"
    capture_error: Optional[str] = None

    def to_dict(self):
        return asdict(self)

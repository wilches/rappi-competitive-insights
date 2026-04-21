"""UberEats MX scraper.

Because UberEats requires session cookies (issued by Cloudflare + Uber session system),
we bootstrap once with Playwright to collect cookies, then use httpx for data calls.

We don't call an anonymous "feed" endpoint. Instead, we pre-mapped ~6 McDonald's
storeUuids per city in config/ubereats_stores.json, and for each target address we
hit getStoreV1 with the nearest store's UUID + the address's coordinates in headers.
"""
import json
import math
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from playwright.sync_api import sync_playwright
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from scrapers.base import (
    Observation, build_proxy_url, setup_logger, polite_sleep, MAX_RETRIES
)
from scrapers.product_matcher import match_product

log = setup_logger("ubereats")

UBEREATS_ENDPOINT = "https://www.ubereats.com/_p/api/getStoreV1?localeCode=mx"
UBEREATS_HOME = "https://www.ubereats.com/mx"

def _dump_raw(payload: dict, address_id: str, run_id: str):
    """Save raw API response to data/raw for debugging."""
    out_dir = Path("data/raw/ubereats")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{run_id}_{address_id}.json"
    try:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # never let logging break the scraper
# ─────────────────────────────────────────────────────
# Store mapping: pick nearest pre-known store per address
# ─────────────────────────────────────────────────────
def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlng / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _load_stores() -> list[dict]:
    path = Path(__file__).parent.parent / "config" / "ubereats_stores.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)["stores"]


def nearest_store(address: dict, stores: list[dict]) -> dict:
    """Pick the nearest store IN THE SAME CITY to the target address."""
    same_city = [s for s in stores if s["city"] == address["city"]] or stores
    return min(same_city, key=lambda s: _haversine_km(
        address["latitude"], address["longitude"], s["latitude"], s["longitude"]
    ))


# ─────────────────────────────────────────────────────
# Bootstrap: get fresh session cookies via Playwright
# ─────────────────────────────────────────────────────
def bootstrap_session(city: str = "cdmx") -> dict:
    """Open ubereats.com through the MX proxy and collect session cookies.

    Returns a dict with: cookies (dict), user_agent (str).
    """
    log.info(f"Bootstrapping UberEats session via {city} proxy...")
    proxy_url = build_proxy_url(city=city, session_id=f"uboot_{uuid.uuid4().hex[:6]}", lifetime_min=15)

    # Parse proxy_url for Playwright's proxy dict format
    # http://user:pass@host:port  -> {"server": "http://host:port", "username": ..., "password": ...}
    m = re.match(r"http://([^:]+):([^@]+)@([^:]+):(\d+)", proxy_url)
    if not m:
        raise ValueError(f"Could not parse proxy URL: {proxy_url}")
    user, pwd, host, port = m.groups()
    proxy_config = {
        "server": f"http://{host}:{port}",
        "username": user,
        "password": pwd,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy=proxy_config)
        context = browser.new_context(
            locale="es-MX",
            timezone_id="America/Mexico_City",
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        try:
            page.goto(UBEREATS_HOME, wait_until="domcontentloaded", timeout=60_000)
            # Small wait for Cloudflare challenge to clear and cookies to set
            page.wait_for_timeout(4_000)
            cookies_list = context.cookies()
            ua = context.pages[0].evaluate("() => navigator.userAgent")
        finally:
            browser.close()

    cookies = {c["name"]: c["value"] for c in cookies_list}
    essential = ["cf_clearance", "uev2.id.session_v2", "dId"]
    have = [k for k in essential if k in cookies]
    log.info(f"Captured {len(cookies)} cookies. Essential present: {have}")

    return {"cookies": cookies, "user_agent": ua}


# ─────────────────────────────────────────────────────
# Fetch & parse
# ─────────────────────────────────────────────────────
def _headers(session: dict, lat: float, lng: float) -> dict:
    return {
        "accept": "*/*",
        "accept-language": "es-MX,es;q=0.9",
        "content-type": "application/json",
        "origin": "https://www.ubereats.com",
        "referer": "https://www.ubereats.com/mx/",
        "user-agent": session["user_agent"],
        "x-csrf-token": "x",  # Observed: UberEats accepts literal "x" on unauth flow
        "x-uber-device-location-latitude": str(lat),
        "x-uber-device-location-longitude": str(lng),
        "x-uber-target-location-latitude": str(lat),
        "x-uber-target-location-longitude": str(lng),
    }


def _body(store_uuid: str) -> dict:
    return {
        "storeUuid": store_uuid,
        "diningMode": "DELIVERY",
        "time": {"asap": True},
        "cbType": "EATER_ENDORSED",
    }


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=2, min=4, max=20),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    reraise=True,
)
def _fetch(client: httpx.Client, store_uuid: str, lat: float, lng: float, session: dict) -> dict:
    r = client.post(
        UBEREATS_ENDPOINT,
        json=_body(store_uuid),
        headers=_headers(session, lat, lng),
        cookies=session["cookies"],
        timeout=30.0,
    )
    r.raise_for_status()
    return r.json()


def _parse_eta(text: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    if not text:
        return None, None
    nums = [int(x) for x in re.findall(r"\d+", text)]
    if not nums:
        return None, None
    if len(nums) == 1:
        return nums[0], nums[0]
    return min(nums), max(nums)


def _iter_products_from_metajson(data: dict):
    """UberEats embeds a schema.org-style menu in data.metaJson.hasMenu.hasMenuSection[].
    Note: metaJson is sometimes a JSON-encoded string, not a dict — handle both."""
    meta = data.get("metaJson") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except json.JSONDecodeError:
            meta = {}

    menu = meta.get("hasMenu") or {}
    for section in menu.get("hasMenuSection") or []:
        for item in section.get("hasMenuItem") or []:
            name = item.get("name")
            offers = item.get("offers") or {}
            price = offers.get("price")
            currency = offers.get("priceCurrency", "MXN")
            try:
                price_f = float(price) if price is not None else None
            except (TypeError, ValueError):
                price_f = None
            if name and price_f is not None:
                yield name, price_f, currency


def scrape_address(address: dict, stores: list[dict], session: dict, run_id: str) -> list[Observation]:
    city = address["city"]
    store = nearest_store(address, stores)
    log.info(f"Scraping UberEats {address['address_id']} → store {store['store_name']} ({store['store_uuid'][:8]}...)")

    proxy_url = build_proxy_url(city=city, session_id=f"ue_{address['address_id']}")
    try:
        with httpx.Client(proxy=proxy_url, timeout=30.0) as client:
            response_json = _fetch(
                client,
                store["store_uuid"],
                address["latitude"],
                address["longitude"],
                session,
            )
    except Exception as e:
        log.error(f"Failed for {address['address_id']}: {e}")
        return [_error_observation(address, run_id, str(e))]

    # Save raw response for inspection (helps debug parser issues)
    _dump_raw(response_json, address["address_id"], run_id)

    data = response_json.get("data", {})
    if not data:
        return [_error_observation(address, run_id, "empty_data")]

    store_name = data.get("title") or store["store_name"]
    store_uuid_ret = data.get("uuid") or store["store_uuid"]
    is_open = data.get("isOpen", True)
    is_orderable = data.get("isOrderable", True)

    # ETA
    eta_range = data.get("etaRange") or {}
    eta_min, eta_max = _parse_eta(eta_range.get("text"))

    # Promos — check modalityInfo (delivery promos) + store flags
    promo_present = False
    promo_descriptions = []
    promo_keywords = (
        "gratis", "promo", "free", "descuento", "oferta",
        "mxn0", "mxn 0", "$0", "nuevos usuarios", "primera",
        "ahorra", "2x1", "off", "-%", "%off", "regalo",
    )
    for opt in (data.get("modalityInfo") or {}).get("modalityOptions") or []:
        title = opt.get("title") or ""
        subtitle = opt.get("subtitle") or ""
        combined = f"{title} {subtitle}".strip()
        if combined and any(kw in combined.lower() for kw in promo_keywords):
            promo_present = True
            promo_descriptions.append(combined)
    if data.get("hasStorePromotion") or data.get("promotion"):
        promo_present = True
        p = data.get("promotion") or {}
        if isinstance(p, dict):
            text = p.get("text") or p.get("title")
            if text:
                promo_descriptions.append(str(text))

    promo_description = " | ".join(promo_descriptions[:2]) if promo_descriptions else None

    # Pick cheapest match per canonical product
    candidates: dict[str, list[tuple[str, float]]] = {}
    for raw_name, price, _currency in _iter_products_from_metajson(data):
        canonical = match_product(raw_name)
        if not canonical:
            continue
        candidates.setdefault(canonical, []).append((raw_name, price))

    observations: list[Observation] = []
    for canonical, matches in candidates.items():
        raw_name, price = min(matches, key=lambda m: m[1])
        observations.append(Observation(
            run_id=run_id,
            platform="ubereats",
            city=city,
            zone_type=address["zone_type"],
            address_id=address["address_id"],
            address_label=address["label"],
            latitude=address["latitude"],
            longitude=address["longitude"],
            store_id=store_uuid_ret,
            store_name=store_name,
            product_canonical=canonical,
            product_raw_name=raw_name,
            product_price=price,
            product_price_final=price,  # UberEats metaJson doesn't expose pre-discount
            eta_min=eta_min,
            eta_max=eta_max,
            promo_present=promo_present,
            promo_description=promo_description,
            store_available=bool(is_open) and bool(is_orderable),
        ))

    if not observations:
        observations.append(Observation(
            run_id=run_id,
            platform="ubereats",
            city=city,
            zone_type=address["zone_type"],
            address_id=address["address_id"],
            address_label=address["label"],
            latitude=address["latitude"],
            longitude=address["longitude"],
            store_id=store_uuid_ret,
            store_name=store_name,
            eta_min=eta_min,
            eta_max=eta_max,
            promo_present=promo_present,
            promo_description=promo_description,
            store_available=bool(is_open),
            capture_error="no_matching_products",
        ))

    log.info(f"  → {len(observations)} observations captured")
    return observations


def _error_observation(address: dict, run_id: str, err: str) -> Observation:
    return Observation(
        run_id=run_id,
        platform="ubereats",
        city=address["city"],
        zone_type=address["zone_type"],
        address_id=address["address_id"],
        address_label=address["label"],
        latitude=address["latitude"],
        longitude=address["longitude"],
        capture_error=err[:300],
    )


def scrape_all(addresses: list[dict], run_id: str) -> list[Observation]:
    stores = _load_stores()
    session = bootstrap_session(city="cdmx")
    results = []
    for addr in addresses:
        results.extend(scrape_address(addr, stores, session, run_id))
        polite_sleep()
    return results


if __name__ == "__main__":
    with open("config/addresses.json", encoding="utf-8") as f:
        addrs = json.load(f)["addresses"]

    run_id = f"smoke_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    stores = _load_stores()
    session = bootstrap_session(city="cdmx")

    test_addr = addrs[0]
    print(f"\nTesting UberEats scraper on: {test_addr['label']}")
    observations = scrape_address(test_addr, stores, session, run_id)
    print(f"\nGot {len(observations)} observations:\n")
    for o in observations:
        err_str = f" | err: {o.capture_error}" if o.capture_error else ""
        print(f"  {o.product_canonical or '(store-only)'}: "
              f"${o.product_price} | ETA {o.eta_min}-{o.eta_max} "
              f"| promo: {o.promo_description}{err_str}")

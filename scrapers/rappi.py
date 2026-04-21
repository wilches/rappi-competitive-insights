"""Rappi MX scraper — hits the brand menu endpoint directly.

Uses the fact that Rappi's /restaurant-bus/store/brand/id/706 endpoint
picks the nearest McDonald's store automatically based on lat/lng in the body.
"""
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from scrapers.base import (
    Observation, build_proxy_url, setup_logger, polite_sleep, MAX_RETRIES
)
from scrapers.product_matcher import match_product

log = setup_logger("rappi")

RAPPI_BRAND_ID = 706  # McDonald's brand ID on Rappi MX
RAPPI_ENDPOINT = f"https://services.mxgrability.rappi.com/api/restaurant-bus/store/brand/id/{RAPPI_BRAND_ID}"

# ⚠️ SESSION TOKENS — refresh these if the scraper starts returning 401/403.
# How to refresh: open rappi.com.mx in Chrome (with MX proxy), enter any address,
# click McDonald's, open DevTools → Network → find a request to services.mxgrability.rappi.com,
# copy the `authorization` and `deviceid` headers here.
RAPPI_AUTH_TOKEN = "ft.gAAAAABp5rw_GwcamM5U0UEb3N5nKM6WQqiFIx4ulqOO_XH1J5_nRtZ9Z3dyp62s3Q_WYzJU1MWgVg1jMY32bxhr25gvjKVtqyCuV1tdawt5yxdwi7IW2Qr1tr7yN58lpYAdqHslyeMrrcxtNwlxN8XRLZzZ-t-ewF4j8SfNN0KSxo7nBmSrs_H9TBN1w_trIj44m5bMyGyYRcHmvM9QQUKfcbtt04qlBZ3eK9bIcGRYkVVyG-cMFamXKihnzIRDRsJ7uZhnO5wuSX6WyKwaOv272NRjqRNDagR1rlFzYoWT745Wp7xhKwySXCh6PmjMXxSxxjJGVyFisJaC68JJMhqJdvTRL0PFC20NsVw9lwqjFNbBQLem4InL8EkW632FPKenoZ7OVvWcBNueIkRdMbCRgNSPYlENtA=="
RAPPI_DEVICE_ID = "c0709df4-3b5c-48eb-b49d-a3f532f0e52aR"

def _dump_raw(payload: dict, address_id: str, run_id: str):
    """Save raw API response to data/raw for debugging."""
    out_dir = Path("data/raw/rappi")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{run_id}_{address_id}.json"
    try:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _headers() -> dict:
    return {
        "accept": "application/json",
        "accept-language": "es-MX",
        "app-version": "1.161.2",
        "app-version-name": "1.161.2",
        "authorization": f"Bearer {RAPPI_AUTH_TOKEN}",
        "content-type": "application/json; charset=UTF-8",
        "deviceid": RAPPI_DEVICE_ID,
        "needappsflyerid": "false",
        "origin": "https://www.rappi.com.mx",
        "referer": "https://www.rappi.com.mx/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    }


def _body(lat: float, lng: float) -> dict:
    return {
        "is_prime": False,
        "lat": lat,
        "lng": lng,
        "store_type": "restaurant",
        "prime_config": {"unlimited_shipping": False},
    }


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=2, min=4, max=20),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    reraise=True,
)
def _fetch(client: httpx.Client, lat: float, lng: float) -> dict:
    r = client.post(RAPPI_ENDPOINT, json=_body(lat, lng), headers=_headers(), timeout=30.0)
    r.raise_for_status()
    return r.json()


def _parse_eta(eta_text: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """'12 min' -> (12, 12). '20-35 min' -> (20, 35). None -> (None, None)."""
    if not eta_text:
        return None, None
    nums = [int(x) for x in re.findall(r"\d+", eta_text)]
    if not nums:
        return None, None
    if len(nums) == 1:
        return nums[0], nums[0]
    return min(nums), max(nums)


def _extract_store_promos(store_json: dict) -> tuple[bool, Optional[str]]:
    """Extract store-level promo presence + description."""
    tags = store_json.get("discount_tags") or []
    if not tags:
        return False, None
    # Concatenate short descriptions of up to 2 promos
    descriptions = []
    for t in tags[:2]:
        title = t.get("title") or t.get("tag") or t.get("message") or t.get("type")
        if title:
            descriptions.append(str(title).strip())
    return True, " | ".join(descriptions) if descriptions else True, None


def _iter_products(store_json: dict):
    """Yield (raw_name, price, price_final, available) for each product in the menu."""
    for corridor in store_json.get("corridors") or []:
        for prod in corridor.get("products") or []:
            raw_name = prod.get("name") or ""
            price = prod.get("real_price") or prod.get("price")
            # Rappi sometimes puts the discounted price in `price` and original in `real_price`.
            # If `discount_percentage` > 0, `price` is usually the after-discount.
            original = prod.get("real_price") or price
            final = prod.get("price") or price
            if price is None:
                continue
            try:
                original_f = float(original) if original is not None else None
                final_f = float(final) if final is not None else None
            except (TypeError, ValueError):
                continue
            available = prod.get("is_available", True)
            yield raw_name, original_f, final_f, available


def scrape_address(address: dict, run_id: str) -> list[Observation]:
    """Scrape one address. Returns one Observation per canonical product + 1 store-level row.

    If the store isn't available or the request fails, returns a single error observation.
    """
    city = address["city"]
    proxy_url = build_proxy_url(city=city, session_id=f"rappi_{address['address_id']}")

    log.info(f"Scraping Rappi for {address['address_id']} ({city})")

    try:
        with httpx.Client(proxy=proxy_url, timeout=30.0) as client:
            data = _fetch(client, address["latitude"], address["longitude"])
    except Exception as e:
        log.error(f"Failed for {address['address_id']}: {e}")
        return [_error_observation(address, run_id, str(e))]

    # Unwrap — sometimes APIs wrap in {data: ...}
    store_json = data.get("data", data)
    _dump_raw(data, address["address_id"], run_id)

    store_id = str(store_json.get("id") or store_json.get("store_id") or "")
    store_name = store_json.get("name") or store_json.get("store_name") or "McDonald's"
    is_open = (
        store_json.get("is_opened")
        or store_json.get("is_open")
        or store_json.get("opened")
        or store_json.get("open")
        or True  # Fallback: if we successfully got a menu, assume open
    )

    eta_text = store_json.get("eta")
    eta_min, eta_max = _parse_eta(eta_text)

    # Promos — safely handled
    tags = store_json.get("discount_tags") or []
    promo_present = bool(tags)
    promo_descriptions = []
    for t in tags[:2]:
        title = t.get("title") or t.get("tag") or t.get("message") or t.get("type")
        if title:
            promo_descriptions.append(str(title).strip())
    promo_description = " | ".join(promo_descriptions) if promo_descriptions else None

    # Collect ALL candidate matches per canonical, then pick the CHEAPEST
    # (standalone items are almost always cheaper than combos/meals)
    candidates: dict[str, list[tuple[str, float, float, bool]]] = {}
    for raw_name, price, final, available in _iter_products(store_json):
        canonical = match_product(raw_name)
        if not canonical:
            continue
        candidates.setdefault(canonical, []).append((raw_name, price, final, available))

    observations: list[Observation] = []
    for canonical, matches in candidates.items():
        # Pick the cheapest (by final price) — standalone beats combo
        best = min(matches, key=lambda m: m[2] if m[2] is not None else float("inf"))
        raw_name, price, final, available = best

        observations.append(Observation(
            run_id=run_id,
            platform="rappi",
            city=city,
            zone_type=address["zone_type"],
            address_id=address["address_id"],
            address_label=address["label"],
            latitude=address["latitude"],
            longitude=address["longitude"],
            store_id=store_id,
            store_name=store_name,
            product_canonical=canonical,
            product_raw_name=raw_name,
            product_price=price,
            product_price_final=final,
            eta_min=eta_min,
            eta_max=eta_max,
            promo_present=promo_present,
            promo_description=promo_description,
            store_available=True if price is not None else False,
        ))

    # If we didn't match any products (maybe menu layout changed), still emit a store-level row
    if not observations:
        observations.append(Observation(
            run_id=run_id,
            platform="rappi",
            city=city,
            zone_type=address["zone_type"],
            address_id=address["address_id"],
            address_label=address["label"],
            latitude=address["latitude"],
            longitude=address["longitude"],
            store_id=store_id,
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
        platform="rappi",
        city=address["city"],
        zone_type=address["zone_type"],
        address_id=address["address_id"],
        address_label=address["label"],
        latitude=address["latitude"],
        longitude=address["longitude"],
        capture_error=err[:300],
    )


def scrape_all(addresses: list[dict], run_id: str) -> list[Observation]:
    results = []
    for addr in addresses:
        obs = scrape_address(addr, run_id)
        results.extend(obs)
        polite_sleep()
    return results


if __name__ == "__main__":
    # Smoke test — one address
    with open("config/addresses.json", encoding="utf-8") as f:
        addrs = json.load(f)["addresses"]

    run_id = f"smoke_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    test_addr = addrs[0]  # cdmx polanco
    print(f"Testing Rappi scraper on: {test_addr['label']}")
    observations = scrape_address(test_addr, run_id)
    print(f"\nGot {len(observations)} observations:\n")
    for o in observations:
        print(f"  {o.product_canonical or '(store-only)'}: "
              f"${o.product_price} → ${o.product_price_final} "
              f"| ETA {o.eta_min}-{o.eta_max} | promo: {o.promo_description}")
    # Save raw response for inspection
    print(f"\nFull observations saved.")

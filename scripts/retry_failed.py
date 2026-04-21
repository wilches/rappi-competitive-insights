"""Retry any addresses that errored out in a specific run.

Usage:
    python scripts/retry_failed.py data/processed/observations_run_20260421_051804.csv
"""
import sys
import json
import pandas as pd
from datetime import datetime, timezone
import sys
from pathlib import Path

# Ensure project root is on sys.path so `scrapers` is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers import rappi, ubereats
from scrapers.base import setup_logger

log = setup_logger("retry")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/retry_failed.py <path_to_csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    df = pd.read_csv(csv_path)

    # Find addresses that errored out, per platform
    errored = df[df["capture_error"].notna() & (df["capture_error"] != "")]
    if errored.empty:
        print("No errors in this run. Nothing to retry.")
        return

    with open("config/addresses.json", encoding="utf-8") as f:
        all_addresses = {a["address_id"]: a for a in json.load(f)["addresses"]}

    run_id = f"retry_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    retry_obs = []
    for platform in errored["platform"].unique():
        addr_ids = errored[errored["platform"] == platform]["address_id"].unique()
        addrs_to_retry = [all_addresses[a] for a in addr_ids if a in all_addresses]
        print(f"\nRetrying {len(addrs_to_retry)} addresses on {platform}")

        if platform == "rappi":
            retry_obs.extend(rappi.scrape_all(addrs_to_retry, run_id))
        elif platform == "ubereats":
            stores = ubereats._load_stores()
            session = ubereats.bootstrap_session(city="cdmx")
            for a in addrs_to_retry:
                retry_obs.extend(ubereats.scrape_address(a, stores, session, run_id))

    # Merge clean retry observations into the original CSV
    clean = [o.to_dict() for o in retry_obs if not o.capture_error]
    print(f"\nRetry captured {len(clean)} new clean observations.")

    if clean:
        # Drop errored rows from original, then append clean retries
        original_clean = df[df["capture_error"].isna() | (df["capture_error"] == "")]
        merged = pd.concat([original_clean, pd.DataFrame(clean)], ignore_index=True)

        out_path = csv_path.replace(".csv", "_retried.csv")
        merged.to_csv(out_path, index=False, encoding="utf-8")
        print(f"Merged output saved → {out_path}")


if __name__ == "__main__":
    main()

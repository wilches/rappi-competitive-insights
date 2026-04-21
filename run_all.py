"""Orchestrator: run all scrapers across all addresses and save unified output.

Usage:
    python run_all.py                 # Full run, both platforms, all addresses
    python run_all.py --platform rappi
    python run_all.py --limit 3       # Only scrape first 3 addresses (for testing)
    python run_all.py --run-id myrun  # Custom run ID (default: timestamp)
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scrapers import rappi, ubereats
from scrapers.base import setup_logger

log = setup_logger("orchestrator")


def _load_addresses() -> list[dict]:
    with open("config/addresses.json", encoding="utf-8") as f:
        return json.load(f)["addresses"]


def _save_observations(observations: list, run_id: str):
    """Save combined observations to JSON (raw) and CSV (for analysis)."""
    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    # JSON dump (full, with nulls)
    json_path = out_dir / f"observations_{run_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([o.to_dict() for o in observations], f, ensure_ascii=False, indent=2, default=str)

    # CSV dump
    import pandas as pd
    df = pd.DataFrame([o.to_dict() for o in observations])
    csv_path = out_dir / f"observations_{run_id}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")

    log.info(f"Saved {len(observations)} observations → {csv_path}")
    log.info(f"Also saved → {json_path}")
    return csv_path, json_path


def _summary(observations: list):
    """Quick stdout summary for sanity-checking each run."""
    by_platform = {}
    errors = 0
    for o in observations:
        by_platform.setdefault(o.platform, {"total": 0, "with_price": 0, "errors": 0})
        by_platform[o.platform]["total"] += 1
        if o.product_price is not None:
            by_platform[o.platform]["with_price"] += 1
        if o.capture_error:
            by_platform[o.platform]["errors"] += 1
            errors += 1

    print("\n" + "=" * 60)
    print(f"RUN SUMMARY")
    print("=" * 60)
    for platform, stats in by_platform.items():
        print(f"{platform:12s}  total={stats['total']:3d}  "
              f"with_price={stats['with_price']:3d}  errors={stats['errors']:3d}")
    print(f"\nTotal observations: {len(observations)}")
    print(f"Total errors:       {errors}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["rappi", "ubereats", "all"], default="all")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only scrape first N addresses (for testing)")
    parser.add_argument("--run-id", type=str, default=None)
    args = parser.parse_args()

    run_id = args.run_id or f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    addresses = _load_addresses()
    if args.limit:
        addresses = addresses[:args.limit]

    log.info(f"Starting run {run_id} | {len(addresses)} addresses | platform={args.platform}")

    all_observations = []

    if args.platform in ("rappi", "all"):
        log.info(">>> RAPPI <<<")
        try:
            obs = rappi.scrape_all(addresses, run_id)
            all_observations.extend(obs)
        except Exception as e:
            log.exception(f"Rappi run failed: {e}")

    if args.platform in ("ubereats", "all"):
        log.info(">>> UBEREATS <<<")
        try:
            obs = ubereats.scrape_all(addresses, run_id)
            all_observations.extend(obs)
        except Exception as e:
            log.exception(f"UberEats run failed: {e}")

    if all_observations:
        _save_observations(all_observations, run_id)
        _summary(all_observations)
    else:
        log.warning("No observations captured. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

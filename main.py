# main.py
import asyncio
import json
import argparse
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.table import Table

from scrapers.rappi_scraper import RappiScraper
from scrapers.ubereats_scraper import UberEatsScraper
from scrapers.didifood_scraper import DidiScraper

console = Console()


def load_config():
    """Load addresses and products configuration."""
    with open('config/addresses.json', 'r', encoding='utf-8') as f:
        addresses_config = json.load(f)

    with open('config/products.json', 'r', encoding='utf-8') as f:
        products_config = json.load(f)

    return addresses_config, products_config


async def run_scraper(scraper_class, addresses, restaurant, products, headless=True):
    """Run a single scraper."""
    scraper = scraper_class(headless=headless)
    try:
        results = await scraper.run(addresses, restaurant, products)
        return results
    except Exception as e:
        console.print(f"[red]Error running {scraper_class.PLATFORM_NAME}: {e}[/red]")
        return []


async def main(num_addresses=5, headless=True, platforms=None):
    """Main orchestration function."""

    console.print("[bold green]🚀 Rappi Competitive Intelligence Scraper[/bold green]")
    console.print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    console.print("=" * 60)

    # Load config
    addresses_config, products_config = load_config()

    # Select addresses (use subset for testing)
    all_addresses = addresses_config['mexico_city']['addresses']
    addresses = all_addresses[:num_addresses]

    console.print(f"\n📍 Scraping {len(addresses)} addresses")
    for addr in addresses:
        console.print(f"   • {addr['zone_name']} ({addr['zone_type']})")

    # Products to scrape
    restaurant = products_config['fast_food']['restaurant']
    products = products_config['fast_food']['products']

    console.print(f"\n🍔 Restaurant: {restaurant}")
    console.print(f"📦 Products: {', '.join(p['name'] for p in products)}")

    # Define scrapers
    available_scrapers = {
        'rappi': RappiScraper,
        'ubereats': UberEatsScraper,
        'didifood': DidiScraper,
    }

    if platforms:
        scrapers_to_run = {k: v for k, v in available_scrapers.items() if k in platforms}
    else:
        scrapers_to_run = available_scrapers

    # Run scrapers sequentially (to avoid detection)
    all_results = []

    for name, scraper_class in scrapers_to_run.items():
        console.print(f"\n{'='*60}")
        console.print(f"[bold blue]🔍 Starting {name.upper()} scraper...[/bold blue]")
        console.print(f"{'='*60}")

        results = await run_scraper(
            scraper_class, addresses, restaurant, products, headless
        )
        all_results.extend(results)

        console.print(f"[green]✅ {name}: {len(results)} data points collected[/green]")

        # Delay between platforms
        if name != list(scrapers_to_run.keys())[-1]:
            console.print("[yellow]⏳ Waiting before next platform...[/yellow]")
            await asyncio.sleep(10)

    # Combine all results
    if all_results:
        all_data = [r.to_dict() if hasattr(r, 'to_dict') else r for r in all_results]
        df = pd.DataFrame(all_data)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        combined_csv = f"data/raw/all_platforms_{timestamp}.csv"
        combined_json = f"data/raw/all_platforms_{timestamp}.json"

        df.to_csv(combined_csv, index=False)
        with open(combined_json, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

        # Print summary
        console.print(f"\n{'='*60}")
        console.print("[bold green]📊 SCRAPING SUMMARY[/bold green]")
        console.print(f"{'='*60}")

        table = Table(title="Results Overview")
        table.add_column("Platform", style="cyan")
        table.add_column("Data Points", justify="right")
        table.add_column("Prices Found", justify="right")
        table.add_column("Errors", justify="right", style="red")

        for platform in df['platform'].unique():
            pdata = df[df['platform'] == platform]
            prices_found = pdata['product_price'].notna().sum()
            errors = (pdata['errors'] != '').sum()
            table.add_row(
                platform,
                str(len(pdata)),
                str(prices_found),
                str(errors)
            )

        console.print(table)
        console.print(f"\n💾 Data saved to: {combined_csv}")

    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Competitive Intelligence Scraper')
    parser.add_argument('--addresses', type=int, default=5, help='Number of addresses to scrape')
    parser.add_argument('--visible', action='store_true', help='Show browser (not headless)')
    parser.add_argument('--platforms', nargs='+', choices=['rappi', 'ubereats', 'didifood'],
                        help='Platforms to scrape (default: all)')

    args = parser.parse_args()

    asyncio.run(main(
        num_addresses=args.addresses,
        headless=not args.visible,
        platforms=args.platforms
    ))

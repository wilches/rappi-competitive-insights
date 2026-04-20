# scrapers/base_scraper.py
import json
import time
import random
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.logging import RichHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("scraper")


class ScrapingResult:
    """Standardized result from any scraper."""

    def __init__(self):
        self.platform = ""
        self.address_id = ""
        self.address = ""
        self.zone_type = ""
        self.zone_name = ""
        self.restaurant_name = ""
        self.product_id = ""
        self.product_name = ""
        self.product_price = None
        self.delivery_fee = None
        self.service_fee = None
        self.small_order_fee = None
        self.estimated_delivery_time_min = None
        self.estimated_delivery_time_max = None
        self.discount_description = ""
        self.discount_amount = None
        self.is_available = True
        self.restaurant_is_open = True
        self.total_price = None  # product + delivery + service fees
        self.timestamp = datetime.now().isoformat()
        self.screenshot_path = ""
        self.raw_data = {}
        self.errors = []

    def to_dict(self):
        return {
            "platform": self.platform,
            "address_id": self.address_id,
            "address": self.address,
            "zone_type": self.zone_type,
            "zone_name": self.zone_name,
            "restaurant_name": self.restaurant_name,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "product_price": self.product_price,
            "delivery_fee": self.delivery_fee,
            "service_fee": self.service_fee,
            "small_order_fee": self.small_order_fee,
            "estimated_delivery_time_min": self.estimated_delivery_time_min,
            "estimated_delivery_time_max": self.estimated_delivery_time_max,
            "discount_description": self.discount_description,
            "discount_amount": self.discount_amount,
            "is_available": self.is_available,
            "restaurant_is_open": self.restaurant_is_open,
            "total_price": self.total_price,
            "timestamp": self.timestamp,
            "screenshot_path": self.screenshot_path,
            "errors": "; ".join(self.errors) if self.errors else ""
        }


class BaseScraper(ABC):
    """Base class for all platform scrapers."""

    PLATFORM_NAME = "base"

    def __init__(self, headless=True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.results = []

        # Rate limiting config
        self.min_delay = 3  # seconds between requests
        self.max_delay = 7

        # Create directories
        Path("data/raw").mkdir(parents=True, exist_ok=True)
        Path("data/processed").mkdir(parents=True, exist_ok=True)
        Path("screenshots").mkdir(parents=True, exist_ok=True)

    async def setup_browser(self):
        """Initialize Playwright browser with anti-detection measures."""
        from playwright.async_api import async_playwright

        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]
        )

        # Create context with realistic settings
        self.context = await self.browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent=(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            locale='es-MX',
            timezone_id='America/Mexico_City',
            geolocation=None,  # We'll set per address
            permissions=['geolocation'],
        )

        # Anti-detection: Override navigator.webdriver
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        self.page = await self.context.new_page()
        logger.info(f"[{self.PLATFORM_NAME}] Browser initialized")

    async def close_browser(self):
        """Clean up browser resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info(f"[{self.PLATFORM_NAME}] Browser closed")

    def random_delay(self, multiplier=1.0):
        """Random delay to be respectful to servers."""
        delay = random.uniform(self.min_delay, self.max_delay) * multiplier
        logger.debug(f"[{self.PLATFORM_NAME}] Waiting {delay:.1f}s...")
        time.sleep(delay)

    async def take_screenshot(self, name):
        """Take a screenshot as evidence."""
        path = f"screenshots/{self.PLATFORM_NAME}_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await self.page.screenshot(path=path, full_page=False)
        logger.info(f"[{self.PLATFORM_NAME}] Screenshot saved: {path}")
        return path

    @abstractmethod
    async def set_address(self, address_data: dict) -> bool:
        """Set delivery address on the platform. Returns True if successful."""
        pass

    @abstractmethod
    async def search_restaurant(self, restaurant_name: str) -> bool:
        """Find and navigate to a restaurant. Returns True if found."""
        pass

    @abstractmethod
    async def get_product_price(self, product_data: dict) -> ScrapingResult:
        """Get price and details for a specific product."""
        pass

    @abstractmethod
    async def get_delivery_info(self) -> dict:
        """Get delivery fee, service fee, and estimated time."""
        pass

    async def scrape_address(self, address_data, restaurant_name, products):
        """Scrape all products for one address."""
        results = []

        try:
            # Set address
            address_set = await self.set_address(address_data)
            if not address_set:
                logger.warning(
                    f"[{self.PLATFORM_NAME}] Could not set address: {address_data['address']}"
                )
                # Create error results for all products
                for product in products:
                    result = ScrapingResult()
                    result.platform = self.PLATFORM_NAME
                    result.address_id = address_data['id']
                    result.address = address_data['address']
                    result.zone_type = address_data['zone_type']
                    result.zone_name = address_data['zone_name']
                    result.product_id = product['id']
                    result.product_name = product['name']
                    result.is_available = False
                    result.errors.append("Could not set address")
                    results.append(result)
                return results

            self.random_delay()

            # Search restaurant
            found = await self.search_restaurant(restaurant_name)
            if not found:
                logger.warning(
                    f"[{self.PLATFORM_NAME}] Restaurant '{restaurant_name}' not found"
                )
                for product in products:
                    result = ScrapingResult()
                    result.platform = self.PLATFORM_NAME
                    result.address_id = address_data['id']
                    result.address = address_data['address']
                    result.zone_type = address_data['zone_type']
                    result.zone_name = address_data['zone_name']
                    result.restaurant_name = restaurant_name
                    result.product_id = product['id']
                    result.product_name = product['name']
                    result.is_available = False
                    result.errors.append("Restaurant not found")
                    results.append(result)
                return results

            self.random_delay()

            # Get delivery info
            delivery_info = await self.get_delivery_info()

            # Get each product
            for product in products:
                try:
                    result = await self.get_product_price(product)
                    result.platform = self.PLATFORM_NAME
                    result.address_id = address_data['id']
                    result.address = address_data['address']
                    result.zone_type = address_data['zone_type']
                    result.zone_name = address_data['zone_name']
                    result.restaurant_name = restaurant_name

                    # Merge delivery info
                    if delivery_info:
                        result.delivery_fee = delivery_info.get('delivery_fee')
                        result.service_fee = delivery_info.get('service_fee')
                        result.estimated_delivery_time_min = delivery_info.get('time_min')
                        result.estimated_delivery_time_max = delivery_info.get('time_max')
                        result.discount_description = delivery_info.get('discount', '')

                    # Calculate total
                    if result.product_price is not None:
                        fees = (result.delivery_fee or 0) + (result.service_fee or 0)
                        discount = result.discount_amount or 0
                        result.total_price = result.product_price + fees - discount

                    results.append(result)
                    self.random_delay(0.5)

                except Exception as e:
                    logger.error(f"[{self.PLATFORM_NAME}] Error getting product {product['name']}: {e}")
                    result = ScrapingResult()
                    result.platform = self.PLATFORM_NAME
                    result.address_id = address_data['id']
                    result.address = address_data['address']
                    result.zone_type = address_data['zone_type']
                    result.zone_name = address_data['zone_name']
                    result.product_id = product['id']
                    result.product_name = product['name']
                    result.errors.append(str(e))
                    results.append(result)

        except Exception as e:
            logger.error(f"[{self.PLATFORM_NAME}] Error scraping address {address_data['id']}: {e}")

        # Take screenshot as evidence
        try:
            screenshot = await self.take_screenshot(f"address_{address_data['id']}")
        except:
            pass

        return results

    async def run(self, addresses, restaurant_name, products):
        """Main execution: scrape all addresses."""
        logger.info(f"[{self.PLATFORM_NAME}] Starting scrape: {len(addresses)} addresses")
        all_results = []

        try:
            await self.setup_browser()

            for i, address in enumerate(addresses):
                logger.info(
                    f"[{self.PLATFORM_NAME}] Progress: {i+1}/{len(addresses)} "
                    f"- {address['zone_name']}"
                )

                results = await self.scrape_address(address, restaurant_name, products)
                all_results.extend(results)

                # Longer delay between addresses
                if i < len(addresses) - 1:
                    self.random_delay(1.5)

        finally:
            await self.close_browser()

        # Save results
        self.results = all_results
        self.save_results()

        return all_results

    def save_results(self):
        """Save results to CSV and JSON."""
        import pandas as pd

        data = [r.to_dict() for r in self.results]
        df = pd.DataFrame(data)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        csv_path = f"data/raw/{self.PLATFORM_NAME}_{timestamp}.csv"
        json_path = f"data/raw/{self.PLATFORM_NAME}_{timestamp}.json"

        df.to_csv(csv_path, index=False)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"[{self.PLATFORM_NAME}] Saved {len(data)} results to {csv_path}")

        return csv_path

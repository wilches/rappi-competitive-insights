# scrapers/rappi_scraper.py
import asyncio
import re
from .base_scraper import BaseScraper, ScrapingResult, logger


class RappiScraper(BaseScraper):
    PLATFORM_NAME = "rappi"
    BASE_URL = "https://www.rappi.com.mx"

    async def set_address(self, address_data: dict) -> bool:
        """Set delivery address on Rappi."""
        try:
            await self.page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)

            # Look for address input / location button
            # Rappi typically has an address bar at the top
            address_selectors = [
                '[data-testid="address-input"]',
                '.address-input',
                'input[placeholder*="dirección"]',
                'input[placeholder*="address"]',
                '[class*="AddressBar"]',
                '[class*="address"]',
                'button[class*="address"]',
            ]

            for selector in address_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=5000)
                    if element:
                        await element.click()
                        await asyncio.sleep(2)
                        break
                except:
                    continue

            # Type the address
            input_selectors = [
                'input[placeholder*="dirección"]',
                'input[placeholder*="busca"]',
                'input[type="text"]',
                '[data-testid="address-search-input"]',
            ]

            input_found = False
            for selector in input_selectors:
                try:
                    input_el = await self.page.wait_for_selector(selector, timeout=3000)
                    if input_el:
                        await input_el.fill('')
                        await input_el.type(address_data['address'], delay=50)
                        input_found = True
                        await asyncio.sleep(3)
                        break
                except:
                    continue

            if not input_found:
                logger.warning(f"[{self.PLATFORM_NAME}] Could not find address input")
                return False

            # Select first suggestion
            suggestion_selectors = [
                '[class*="suggestion"]',
                '[class*="Suggestion"]',
                '[data-testid*="suggestion"]',
                '[class*="autocomplete"] li',
                '[class*="dropdown"] li',
                '[role="option"]',
            ]

            for selector in suggestion_selectors:
                try:
                    suggestion = await self.page.wait_for_selector(selector, timeout=5000)
                    if suggestion:
                        await suggestion.click()
                        await asyncio.sleep(3)

                        # Confirm address if there's a confirm button
                        confirm_selectors = [
                            'button:has-text("Confirmar")',
                            'button:has-text("Guardar")',
                            'button:has-text("Continuar")',
                            '[data-testid="confirm-address"]',
                        ]
                        for cs in confirm_selectors:
                            try:
                                confirm = await self.page.wait_for_selector(cs, timeout=3000)
                                if confirm:
                                    await confirm.click()
                                    await asyncio.sleep(2)
                                    break
                            except:
                                continue

                        return True
                except:
                    continue

            # If we typed the address but couldn't find suggestions,
            # try using geolocation instead
            if address_data.get('lat') and address_data.get('lng'):
                await self.context.set_geolocation({
                    'latitude': address_data['lat'],
                    'longitude': address_data['lng']
                })
                await self.page.reload(wait_until='domcontentloaded')
                await asyncio.sleep(3)
                return True

            return False

        except Exception as e:
            logger.error(f"[{self.PLATFORM_NAME}] Error setting address: {e}")
            return False

    async def search_restaurant(self, restaurant_name: str) -> bool:
        """Search for a restaurant on Rappi."""
        try:
            # Use the search bar
            search_selectors = [
                'input[placeholder*="Busca"]',
                'input[placeholder*="busca"]',
                '[data-testid="search-input"]',
                '[class*="search"] input',
                'input[type="search"]',
            ]

            for selector in search_selectors:
                try:
                    search = await self.page.wait_for_selector(selector, timeout=5000)
                    if search:
                        await search.click()
                        await asyncio.sleep(1)
                        await search.fill('')
                        await search.type(restaurant_name, delay=80)
                        await asyncio.sleep(3)
                        break
                except:
                    continue
            else:
                # Try navigating directly to search URL
                search_url = f"{self.BASE_URL}/search?term={restaurant_name.replace(' ', '%20')}"
                await self.page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)

            # Click on the restaurant from results
            restaurant_selectors = [
                f'a:has-text("{restaurant_name}")',
                f'[class*="store"]:has-text("{restaurant_name}")',
                f'[class*="restaurant"]:has-text("{restaurant_name}")',
                '[data-testid*="store-card"]',
                '[class*="StoreCard"]',
            ]

            for selector in restaurant_selectors:
                try:
                    link = await self.page.wait_for_selector(selector, timeout=5000)
                    if link:
                        await link.click()
                        await asyncio.sleep(3)
                        return True
                except:
                    continue

            # Alternative: try direct URL patterns
            # Rappi URLs are often like /restaurantes/mcdonalds
            slug = restaurant_name.lower().replace("'", "").replace(" ", "-")
            possible_urls = [
                f"{self.BASE_URL}/restaurantes/{slug}",
                f"{self.BASE_URL}/restaurants/{slug}",
            ]

            for url in possible_urls:
                try:
                    response = await self.page.goto(url, wait_until='domcontentloaded', timeout=15000)
                    if response and response.status == 200:
                        await asyncio.sleep(3)
                        return True
                except:
                    continue

            return False

        except Exception as e:
            logger.error(f"[{self.PLATFORM_NAME}] Error searching restaurant: {e}")
            return False

    async def get_product_price(self, product_data: dict) -> ScrapingResult:
        """Get price for a specific product."""
        result = ScrapingResult()
        result.product_id = product_data['id']
        result.product_name = product_data['name']

        try:
            # Search within the restaurant menu
            page_content = await self.page.content()

            for search_term in product_data['search_terms']:
                # Look for product cards/items
                product_selectors = [
                    f'[class*="product"]:has-text("{search_term}")',
                    f'[class*="item"]:has-text("{search_term}")',
                    f'span:has-text("{search_term}")',
                    f'p:has-text("{search_term}")',
                ]

                for selector in product_selectors:
                    try:
                        product_el = await self.page.wait_for_selector(selector, timeout=3000)
                        if product_el:
                            # Try to find price near this element
                            parent = product_el

                            # Look for price patterns in nearby elements
                            price_text = await self.page.evaluate('''(el) => {
                                // Search in parent containers
                                let current = el;
                                for (let i = 0; i < 5; i++) {
                                    current = current.parentElement;
                                    if (!current) break;
                                    const text = current.innerText;
                                    const priceMatch = text.match(/\$\s*(\d+(?:[.,]\d{2})?)/);
                                    if (priceMatch) return priceMatch[0];
                                }
                                return null;
                            }''', product_el)

                            if price_text:
                                price = self._parse_price(price_text)
                                if price:
                                    result.product_price = price
                                    result.is_available = True
                                    return result
                    except:
                        continue

            # Fallback: search for price patterns in entire page
            prices = await self.page.evaluate('''() => {
                const elements = document.querySelectorAll('[class*="price"], [class*="Price"]');
                return Array.from(elements).map(el => el.innerText).slice(0, 10);
            }''')

            if prices:
                result.raw_data['visible_prices'] = prices
                result.errors.append("Found prices but couldn't match to specific product")
            else:
                result.is_available = False
                result.errors.append("Product not found on page")

        except Exception as e:
            result.errors.append(f"Error: {str(e)}")

        return result

    async def get_delivery_info(self) -> dict:
        """Extract delivery fee, service fee, and estimated time."""
        info = {}

        try:
            page_content = await self.page.content()

            # Look for delivery time
            time_patterns = [
                r'(\d+)\s*-\s*(\d+)\s*min',
                r'(\d+)\s*min',
            ]

            for pattern in time_patterns:
                match = re.search(pattern, page_content)
                if match:
                    groups = match.groups()
                    if len(groups) == 2:
                        info['time_min'] = int(groups[0])
                        info['time_max'] = int(groups[1])
                    else:
                        info['time_min'] = int(groups[0])
                        info['time_max'] = int(groups[0])
                    break

            # Look for delivery fee
            fee_elements = await self.page.evaluate('''() => {
                const results = {};
                const allText = document.body.innerText;

                // Delivery fee
                const deliveryMatch = allText.match(/(?:envío|delivery|Envío)[:\\s]*\\$\\s*(\\d+(?:[.,]\\d{2})?)/i);
                if (deliveryMatch) results.delivery_fee = deliveryMatch[1];

                // Free delivery
                if (/envío gratis|free delivery|gratis/i.test(allText)) {
                    results.delivery_fee = "0";
                    results.discount = "Envío gratis";
                }

                // Service fee
                const serviceMatch = allText.match(/(?:servicio|service)[:\\s]*\\$\\s*(\\d+(?:[.,]\\d{2})?)/i);
                if (serviceMatch) results.service_fee = serviceMatch[1];

                return results;
            }''')

            if fee_elements:
                if fee_elements.get('delivery_fee'):
                    info['delivery_fee'] = float(fee_elements['delivery_fee'].replace(',', '.'))
                if fee_elements.get('service_fee'):
                    info['service_fee'] = float(fee_elements['service_fee'].replace(',', '.'))
                if fee_elements.get('discount'):
                    info['discount'] = fee_elements['discount']

        except Exception as e:
            logger.warning(f"[{self.PLATFORM_NAME}] Error getting delivery info: {e}")

        return info

    @staticmethod
    def _parse_price(price_str):
        """Parse a price string like '\$99.00' to float."""
        if not price_str:
            return None
        try:
            cleaned = re.sub(r'[^\d.,]', '', price_str)
            cleaned = cleaned.replace(',', '.')
            return float(cleaned)
        except:
            return None

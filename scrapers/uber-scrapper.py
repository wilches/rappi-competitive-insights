# scrapers/ubereats_scraper.py
import asyncio
import re
from .base_scraper import BaseScraper, ScrapingResult, logger


class UberEatsScraper(BaseScraper):
    PLATFORM_NAME = "ubereats"
    BASE_URL = "https://www.ubereats.com/mx"

    async def set_address(self, address_data: dict) -> bool:
        """Set delivery address on Uber Eats."""
        try:
            # Navigate with address in URL or use the UI
            await self.page.goto(self.BASE_URL, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)

            # Handle cookie consent if present
            try:
                cookie_btn = await self.page.wait_for_selector(
                    'button:has-text("Aceptar"), button:has-text("Accept")', timeout=3000
                )
                if cookie_btn:
                    await cookie_btn.click()
                    await asyncio.sleep(1)
            except:
                pass

            # Find and click address input
            address_selectors = [
                '[data-testid="address-input"]',
                'input[placeholder*="Enter delivery address"]',
                'input[placeholder*="dirección"]',
                'input[placeholder*="Ingresa"]',
                'button:has-text("Deliver")',
                'button:has-text("Entregar")',
                '[id*="address"]',
                '[class*="AddressInput"]',
            ]

            for selector in address_selectors:
                try:
                    el = await self.page.wait_for_selector(selector, timeout=4000)
                    if el:
                        await el.click()
                        await asyncio.sleep(2)
                        break
                except:
                    continue

            # Type address
            input_selectors = [
                'input[placeholder*="address"]',
                'input[placeholder*="dirección"]',
                'input[placeholder*="Ingresa"]',
                'input[aria-label*="address"]',
                '#location-typeahead-home-input',
                'input[id*="location"]',
            ]

            for selector in input_selectors:
                try:
                    input_el = await self.page.wait_for_selector(selector, timeout=3000)
                    if input_el:
                        await input_el.fill('')
                        await input_el.type(address_data['address'], delay=60)
                        await asyncio.sleep(3)

                        # Select first suggestion
                        suggestion = await self.page.wait_for_selector(
                            '[id*="location-typeahead"] li, [class*="suggestion"], [role="option"]',
                            timeout=5000
                        )
                        if suggestion:
                            await suggestion.click()
                            await asyncio.sleep(2)

                        # Click "Done" or similar
                        done_selectors = [
                            'button:has-text("Done")',
                            'button:has-text("Listo")',
                            'button:has-text("Hecho")',
                            'button:has-text("Save")',
                            'button:has-text("Guardar")',
                            'button[data-testid*="save"]',
                        ]
                        for ds in done_selectors:
                            try:
                                done = await self.page.wait_for_selector(ds, timeout=3000)
                                if done:
                                    await done.click()
                                    await asyncio.sleep(2)
                                    break
                            except:
                                continue

                        return True
                except:
                    continue

            # Fallback: use URL with coordinates
            if address_data.get('lat') and address_data.get('lng'):
                url = f"{self.BASE_URL}?daddr={address_data['lat']},{address_data['lng']}"
                await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)
                return True

            return False

        except Exception as e:
            logger.error(f"[{self.PLATFORM_NAME}] Error setting address: {e}")
            return False

    async def search_restaurant(self, restaurant_name: str) -> bool:
        """Search for restaurant on Uber Eats."""
        try:
            # Try direct search URL
            search_url = f"{self.BASE_URL}/search?q={restaurant_name.replace(' ', '%20')}"
            await self.page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(4)

            # Click on restaurant result
            selectors = [
                f'a:has-text("{restaurant_name}")',
                '[data-testid*="store-card"] a',
                '[class*="StoreCard"] a',
                'a[href*="/store/"]',
            ]

            for selector in selectors:
                try:
                    link = await self.page.wait_for_selector(selector, timeout=5000)
                    if link:
                        await link.click()
                        await asyncio.sleep(3)
                        return True
                except:
                    continue

            # Try the search bar on the page
            try:
                search = await self.page.wait_for_selector(
                    'input[type="search"], input[placeholder*="Search"], input[placeholder*="Busca"]',
                    timeout=5000
                )
                if search:
                    await search.fill('')
                    await search.type(restaurant_name, delay=80)
                    await asyncio.sleep(3)

                    # Click first result
                    result = await self.page.wait_for_selector(
                        'a[href*="/store/"], [data-testid*="store"]',
                        timeout=5000
                    )
                    if result:
                        await result.click()
                        await asyncio.sleep(3)
                        return True
            except:
                pass

            return False

        except Exception as e:
            logger.error(f"[{self.PLATFORM_NAME}] Error searching restaurant: {e}")
            return False

    async def get_product_price(self, product_data: dict) -> ScrapingResult:
        """Get price for specific product on Uber Eats."""
        result = ScrapingResult()
        result.product_id = product_data['id']
        result.product_name = product_data['name']

        try:
            for search_term in product_data['search_terms']:
                # Uber Eats shows menu items in a list
                selectors = [
                    f'[data-testid*="menu-item"]:has-text("{search_term}")',
                    f'li:has-text("{search_term}")',
                    f'[class*="menuItem"]:has-text("{search_term}")',
                    f'span:has-text("{search_term}")',
                ]

                for selector in selectors:
                    try:
                        item = await self.page.wait_for_selector(selector, timeout=3000)
                        if item:
                            # Extract price from the item context
                            price_text = await self.page.evaluate('''(el) => {
                                let current = el;
                                for (let i = 0; i < 6; i++) {
                                    current = current.parentElement;
                                    if (!current) break;
                                    const spans = current.querySelectorAll('span');
                                    for (const span of spans) {
                                        const text = span.innerText;
                                        if (/^\\$\\s*\\d+/.test(text)) return text;
                                    }
                                }
                                return null;
                            }''', item)

                            if price_text:
                                price = self._parse_price(price_text)
                                if price:
                                    result.product_price = price
                                    result.is_available = True
                                    return result
                    except:
                        continue

            result.is_available = False
            result.errors.append("Product not found")

        except Exception as e:
            result.errors.append(f"Error: {str(e)}")

        return result

    async def get_delivery_info(self) -> dict:
        """Extract delivery info from Uber Eats."""
        info = {}

        try:
            page_text = await self.page.evaluate('() => document.body.innerText')

            # Delivery time
            time_match = re.search(r'(\d+)\s*[-–]\s*(\d+)\s*min', page_text)
            if time_match:
                info['time_min'] = int(time_match.group(1))
                info['time_max'] = int(time_match.group(2))

            # Delivery fee
            fee_match = re.search(r'(?:Delivery Fee|Envío|delivery fee)[:\s]*\$?\s*(\d+(?:[.,]\d{2})?)', page_text, re.IGNORECASE)
            if fee_match:
                info['delivery_fee'] = float(fee_match.group(1).replace(',', '.'))
            elif re.search(r'(?:free delivery|envío gratis)', page_text, re.IGNORECASE):
                info['delivery_fee'] = 0.0
                info['discount'] = 'Free delivery'

            # Service fee
            service_match = re.search(r'(?:Service Fee|Servicio|service fee)[:\s]*\$?\s*(\d+(?:[.,]\d{2})?)', page_text, re.IGNORECASE)
            if service_match:
                info['service_fee'] = float(service_match.group(1).replace(',', '.'))

        except Exception as e:
            logger.warning(f"[{self.PLATFORM_NAME}] Error getting delivery info: {e}")

        return info

    @staticmethod
    def _parse_price(price_str):
        if not price_str:
            return None
        try:
            cleaned = re.sub(r'[^\d.,]', '', price_str)
            cleaned = cleaned.replace(',', '.')
            return float(cleaned)
        except:
            return None

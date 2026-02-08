"""
Scraper for BeYcome.com - Uses Playwright for JavaScript rendering.
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import logging
import re
import asyncio

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class BeycomeScraper(BaseScraper):
    """
    Scraper for BeYcome.com listings.
    Uses Playwright for JavaScript rendering since the site is a React SPA.
    """

    def __init__(self, max_listings: int = 10, scrape_url: str = None):
        """
        Initialize BeYcome scraper.
        
        Args:
            max_listings: Maximum number of listings to scrape
            scrape_url: Custom URL to scrape from
        """
        super().__init__(
            source_name='BeYcome.com',
            base_url='https://www.beycome.com',
            min_delay=0.5,
            max_delay=1.0
        )
        self.max_listings = max_listings
        self.scrape_url = scrape_url or "https://www.beycome.com/for-sale/detroit-mi"
        self.browser = None
        self.context = None
        self.playwright_instance = None

    async def setup_browser(self):
        """Initialize Playwright browser."""
        try:
            from playwright.async_api import async_playwright
            
            self.playwright_instance = await async_playwright().start()
            self.browser = await self.playwright_instance.chromium.launch(headless=True)
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            logger.debug(f"Browser initialized for {self.source_name}")
        except ImportError:
            logger.error("Playwright not installed. Install with: pip install playwright && playwright install")
            raise

    async def cleanup_browser(self):
        """Close browser and cleanup."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright_instance:
            await self.playwright_instance.stop()
        logger.debug(f"Browser closed for {self.source_name}")

    async def get_page_content(self, url: str) -> str:
        """
        Get page content using Playwright browser.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content of the page
        """
        try:
            if not self.browser:
                await self.setup_browser()
            
            page = await self.context.new_page()
            
            try:
                # Use load event with reasonable timeout
                await page.goto(url, wait_until='load', timeout=15000)
            except Exception as e:
                logger.debug(f"Page load timeout: {str(e)[:50]}, continuing")
            
            # Wait for listings to load
            try:
                await page.wait_for_selector('a[href*="/listing/"], [class*="listing"], [class*="card"]', timeout=4000)
            except:
                logger.debug("Listing selectors not found immediately")
            
            # Scroll to trigger lazy loading
            for i in range(2):
                try:
                    await page.evaluate("window.scrollBy(0, 500)")
                    await page.wait_for_load_state("networkidle", timeout=1500)
                except:
                    pass
            
            # Get page content
            content = await page.content()
            await page.close()
            
            return content if content else ""
        except Exception as e:
            logger.warning(f"⚠️  Error fetching {url}: {str(e)[:100]}")
            try:
                await page.close()
            except:
                pass
            return ""

    def get_listing_urls(self) -> List[str]:
        """
        Get list of BeYcome listing URLs.
        
        Returns:
            List with scrape URL
        """
        return [self.scrape_url]

    def parse_listings(self, content: str) -> List[Dict]:
        """
        Parse BeYcome listing HTML from page.
        
        Args:
            content: HTML content
            
        Returns:
            List of extracted listings
        """
        listings = []
        soup = BeautifulSoup(content, 'html.parser')

        # Try multiple selectors for listings
        listing_selectors = [
            'a[href*="/listing/"]',
            'div[class*="listing"]',
            'article',
            '[class*="property-card"]'
        ]
        
        links = []
        for selector in listing_selectors:
            links = soup.select(selector)
            if links:
                logger.debug(f"Found {len(links)} potential listings with selector: {selector}")
                break
        
        for idx, link in enumerate(links[:self.max_listings]):
            try:
                # Get listing URL
                listing_url = link.get('href', '') if link.name == 'a' else ''
                if not listing_url:
                    link_elem = link.find('a', href=True)
                    if link_elem:
                        listing_url = link_elem['href']
                
                if not listing_url:
                    continue
                
                if not listing_url.startswith('http'):
                    listing_url = self.base_url + listing_url
                
                # Get card/container
                card = link if link.name in ['article', 'div'] else link.find_parent(['div', 'article', 'li'])
                if not card:
                    card = link.parent
                
                # Extract address text
                address_text = ""
                
                # Try to find address in common locations
                address_elem = (
                    card.find('h2') or
                    card.find('h3') or
                    card.find(['span', 'div'], class_=re.compile('address|street|title', re.I)) or
                    card.find(string=re.compile(r'\d+\s+\w+', re.I))
                )
                
                if address_elem:
                    address_text = address_elem.get_text(strip=True) if hasattr(address_elem, 'get_text') else str(address_elem)
                
                # Fallback: get card text
                if not address_text:
                    address_text = card.get_text(strip=True)[:150]
                
                if not address_text:
                    continue
                
                # Extract address components
                address_match = self._extract_address_components(address_text)
                
                if address_match:
                    listing = {
                        'street': address_match.get('street', ''),
                        'city': address_match.get('city', ''),
                        'state': address_match.get('state', ''),
                        'zip_code': address_match.get('zip_code', ''),
                        'listing_url': listing_url
                    }
                    
                    listings.append(listing)
                    logger.debug(f"Extracted listing {idx+1}: {address_match}")

            except Exception as e:
                logger.debug(f"Error parsing BeYcome listing: {str(e)[:100]}")
                continue

        logger.info(f"Parsed {len(listings)} listings from {self.source_name}")
        return listings

    @staticmethod
    def _extract_address_components(text: str) -> Optional[Dict[str, str]]:
        """
        Extract address components from text.
        
        Args:
            text: Text containing address information
            
        Returns:
            Dict with street, city, state, zip_code or None
        """
        try:
            # Pattern: "Street, City, State ZIP"
            pattern = r'^(.+?),\s+(.+?),\s+([A-Z]{2})\s+(\d{5})'
            match = re.search(pattern, text)
            
            if match:
                return {
                    'street': match.group(1).strip(),
                    'city': match.group(2).strip(),
                    'state': match.group(3).strip(),
                    'zip_code': match.group(4).strip()
                }
            
            # Try to find state and zip
            pattern2 = r'(.+?),\s+([A-Z]{2})\s+(\d{5})'
            match2 = re.search(pattern2, text)
            
            if match2:
                full_address = match2.group(1).strip()
                state = match2.group(2).strip()
                zip_code = match2.group(3).strip()
                
                # Split address into street and city
                parts = full_address.rsplit(',', 1)
                if len(parts) == 2:
                    return {
                        'street': parts[0].strip(),
                        'city': parts[1].strip(),
                        'state': state,
                        'zip_code': zip_code
                    }
            
            return None
        except Exception as e:
            logger.debug(f"Error extracting address: {str(e)[:100]}")
            return None

    def scrape(self) -> List[Dict]:
        """
        Execute scraping using async Playwright.
        
        Returns:
            List of normalized listings
        """
        try:
            # Try to run async scrape in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._scrape_async())
            loop.close()
            return result
        except RuntimeError:
            logger.warning(f"Could not run Playwright for {self.source_name} - event loop already active")
            return []
        except Exception as e:
            logger.error(f"Error in {self.source_name}: {str(e)[:100]}")
            return []

    async def _scrape_async(self) -> List[Dict]:
        """Async version of scrape."""
        all_listings = []
        
        logger.info(f"Starting scrape of {self.source_name}")
        
        try:
            await self.setup_browser()
            
            listing_urls = self.get_listing_urls()
            logger.info(f"Found {len(listing_urls)} pages to scrape from {self.source_name}")
            
            for url in listing_urls:
                try:
                    logger.debug(f"Fetching {url} with Playwright...")
                    content = await self.get_page_content(url)
                    
                    if not content:
                        logger.warning(f"No content retrieved from {url}")
                        continue
                    
                    listings = self.parse_listings(content)
                    all_listings.extend(listings)
                    logger.debug(f"Scraped {len(listings)} listings from {url}")
                except Exception as e:
                    logger.warning(f"Error scraping {url}: {str(e)[:100]}")
                    continue
            
            if all_listings:
                # Normalize addresses
                normalized = [self._normalize_listing(listing) for listing in all_listings]
                normalized = [l for l in normalized if l is not None]
                
                logger.info(f"Completed scrape of {self.source_name}: {len(normalized)} valid listings")
                return normalized
            else:
                logger.warning(f"No listings found on {self.source_name}")
                return []
            
        except Exception as e:
            logger.warning(f"Error in {self.source_name} scraper: {str(e)[:100]}")
            return []
        
        finally:
            await self.cleanup_browser()

    def close(self) -> None:
        """Close session and cleanup."""
        super().close()
        logger.debug(f"Closed scraper for {self.source_name}")

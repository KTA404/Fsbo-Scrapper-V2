"""
Scraper for Craigslist housing classifieds (by-owner listings).
Uses Playwright for JavaScript rendering since Craigslist moved to dynamic content.
"""

from typing import List, Dict
from bs4 import BeautifulSoup
import logging
import re
import asyncio

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class CraigslistHousingScraper(BaseScraper):
    """
    Scraper for Craigslist housing classifieds.
    Focuses on "by owner" (private seller) listings.
    Uses Playwright for JavaScript rendering.
    """

    def __init__(self):
        """Initialize Craigslist housing scraper."""
        super().__init__(
            source_name='Craigslist Housing',
            base_url='https://craigslist.org',
            min_delay=2.0,
            max_delay=5.0
        )
        self.browser = None
        self.context = None
        self.playwright_instance = None

    async def setup_browser(self):
        """Initialize Playwright browser."""
        try:
            from playwright.async_api import async_playwright
            
            self.playwright_instance = await async_playwright().start()
            self.browser = await self.playwright_instance.chromium.launch(headless=True)
            self.context = await self.browser.new_context()
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

    def get_listing_urls(self) -> List[str]:
        """
        Get Craigslist housing URLs.
        
        Returns:
            List of search page URLs
        """
        # Major US metropolitan areas on Craigslist
        metros = [
            'newyork',      # New York
            'losangeles',   # Los Angeles
            'chicago',      # Chicago
            'dallas',       # Dallas
            'houston',      # Houston
            'sfbay',        # San Francisco Bay Area
            'seattle',      # Seattle
            'boston',       # Boston
            'miami',        # Miami
            'phoenix',      # Phoenix
        ]

        urls = []
        for metro in metros:
            # Housing for sale by owner search - use /sss for all housing
            url = f"https://{metro}.craigslist.org/search/sss?query=house"
            urls.append(url)

        return urls[:2]  # Demo limit - 2 metros

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
                # Use load event instead of domcontentloaded for faster loading
                await page.goto(url, wait_until='load', timeout=20000)
            except Exception as e:
                logger.debug(f"Initial load took time, continuing: {str(e)[:50]}")
                # Continue even if it times out
                pass
            
            # Wait for any listing elements
            try:
                await page.wait_for_function("document.querySelectorAll('[data-pid], [href*=\"/\"]').length > 0", timeout=3000)
            except:
                logger.debug("Waiting for listings...")
            
            # Scroll down to load more content
            try:
                for _ in range(2):
                    await page.evaluate("window.scrollBy(0, 500)")
                    await page.wait_for_load_state("networkidle", timeout=1500)
            except:
                pass
            
            # Get page content
            content = await page.content()
            await page.close()
            
            return content if content else ""
        except Exception as e:
            logger.warning(f"Error fetching {url}: {str(e)[:100]}")
            try:
                await page.close()
            except:
                pass
            return ""

    def parse_listings(self, content: str) -> List[Dict]:
        """
        Parse Craigslist listing HTML.
        
        Args:
            content: HTML content
            
        Returns:
            List of extracted listings
        """
        listings = []
        soup = BeautifulSoup(content, 'html.parser')

        # Try multiple selectors for modern Craigslist structure
        listing_selectors = [
            'li.result-row',
            '[data-pid]',
            'article',
            'div[role="article"]',
            '.cl-search-result'
        ]
        
        results = []
        for selector in listing_selectors:
            results = soup.select(selector)
            if results:
                logger.debug(f"Found {len(results)} listings with selector: {selector}")
                break
        
        # Process each listing
        for idx, result in enumerate(results):
            try:
                # Try to get address/title
                title_elem = (
                    result.find('span', class_='result-title') or
                    result.find('a', class_='result-title') or
                    result.find('a') or
                    result.find('h2') or
                    result.find('h3')
                )
                
                if not title_elem:
                    continue

                address_text = title_elem.get_text(strip=True)
                
                # Get listing URL
                link = result.find('a', href=True)
                listing_url = link['href'] if link else ''
                if listing_url and not listing_url.startswith('http'):
                    listing_url = f"https://craigslist.org{listing_url}"

                # Try to extract address components from title
                address_parts = self._parse_craigslist_address(address_text)
                
                if address_parts['street']:
                    listing = {
                        'street': address_parts['street'],
                        'city': address_parts['city'],
                        'state': address_parts['state'],
                        'zip_code': address_parts['zip_code'],
                        'listing_url': listing_url
                    }
                    listings.append(listing)
                    logger.debug(f"Extracted listing {idx+1}: {address_parts}")

            except Exception as e:
                logger.debug(f"Error parsing Craigslist listing: {str(e)[:100]}")
                continue

        logger.info(f"Parsed {len(listings)} listings from Craigslist")
        return listings

    def _parse_craigslist_address(self, text: str) -> Dict[str, str]:
        """
        Parse address from Craigslist listing title.
        
        Args:
            text: Listing title text
            
        Returns:
            Dictionary with address components
        """
        result = {
            'street': '',
            'city': '',
            'state': '',
            'zip_code': ''
        }

        # Look for ZIP code
        zip_match = re.search(r'\b(\d{5})\b', text)
        if zip_match:
            result['zip_code'] = zip_match.group(1)

        # Try to split address - often format is "Street, City" or just "Street"
        parts = [p.strip() for p in text.split(',')]
        
        if len(parts) >= 2:
            result['street'] = parts[0]
            result['city'] = parts[1]
        elif len(parts) == 1:
            result['street'] = parts[0]

        # Try to extract state if present
        state_match = re.search(r'\b([A-Z]{2})\b', text)
        if state_match:
            result['state'] = state_match.group(1)

        return result

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
                logger.info(f"No listings found on {self.source_name}")
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

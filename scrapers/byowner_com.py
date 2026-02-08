"""
Scraper for ByOwner.com - Uses Playwright for JavaScript rendering.
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import logging
import re
import asyncio

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ByOwnerComScraper(BaseScraper):
    """
    Scraper for ByOwner.com listings.
    Uses Playwright for JavaScript rendering since the site is heavily JS-based.
    """

    def __init__(self, max_listings: int = 10, scrape_url: str = None):
        """
        Initialize ByOwner.com scraper.
        
        Args:
            max_listings: Maximum number of listings to scrape
            scrape_url: Custom URL to scrape from
        """
        super().__init__(
            source_name='ByOwner.com',
            base_url='https://www.byowner.com',
            min_delay=0.5,
            max_delay=1.0
        )
        self.max_listings = max_listings
        self.scrape_url = scrape_url or f"{self.base_url}/miami/florida"
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
            
            # Navigate to page
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Get page content first to check for Cloudflare
            content = await page.content()
            
            if 'Cloudflare' in content or 'blocked' in content.lower():
                logger.warning(f"⚠️  Cloudflare protection detected on {url}. Site may be blocking automated requests.")
                logger.warning("    Install: pip install undetected-chromedriver")
                logger.warning("    Or configure proxy rotation in site settings")
                await page.close()
                return ""
            
            # Try to wait for listings to load
            try:
                await page.wait_for_selector('[data-test*="listing"], .listing-card, [class*="property"]', timeout=5000)
            except:
                logger.debug("Listing selectors not found, checking for any content...")
                # Try to find any listings even without specific selectors
                pass
            
            content = await page.content()
            await page.close()
            
            return content
        except Exception as e:
            logger.warning(f"⚠️  Error fetching {url}: {str(e)[:100]}")
            return ""

    def get_listing_urls(self) -> List[str]:
        """
        Get list of ByOwner.com listing URLs.
        For now, returns the scrape_url as a single item.
        The actual listings will be extracted from the page content.
        
        Returns:
            List with single scrape URL
        """
        return [self.scrape_url]

    def parse_listings(self, content: str) -> List[Dict]:
        """
        Parse ByOwner.com listing HTML from page.
        
        Args:
            content: HTML content
            
        Returns:
            List of extracted listings
        """
        listings = []
        soup = BeautifulSoup(content, 'html.parser')

        # Look for property listings - various selectors for flexibility
        property_selectors = [
            'div[data-test*="listing"]',
            'div.listing-card',
            'article[data-test*="property"]',
            'li[data-test*="property"]'
        ]
        
        # Try multiple selectors
        property_cards = None
        for selector in property_selectors:
            property_cards = soup.select(selector)
            if property_cards:
                logger.debug(f"Found {len(property_cards)} listings using selector: {selector}")
                break
        
        if not property_cards:
            # Fallback: look for any div with property information
            property_cards = soup.find_all('div', class_=re.compile('property|listing|card', re.I))
            logger.debug(f"Using fallback selector, found {len(property_cards)} potential cards")

        for idx, card in enumerate(property_cards[:self.max_listings]):
            try:
                # Extract address from various possible locations
                address_text = ""
                
                # Try common address locations
                address_elem = (
                    card.find('span', class_=re.compile('address|street', re.I)) or
                    card.find('div', class_=re.compile('address|location', re.I)) or
                    card.find('h2') or
                    card.find('h3')
                )
                
                if address_elem:
                    address_text = address_elem.get_text(strip=True)
                else:
                    # Try to extract from text content
                    address_text = card.get_text(strip=True)[:200]
                
                if not address_text:
                    continue
                
                # Extract address components using regex
                address_match = self._extract_address_components(address_text)
                
                if address_match:
                    listing = {
                        'street': address_match.get('street', ''),
                        'city': address_match.get('city', ''),
                        'state': address_match.get('state', ''),
                        'zip_code': address_match.get('zip_code', ''),
                        'listing_url': ''
                    }
                    
                    # Try to find listing URL
                    link = card.find('a', href=re.compile(r'/\d+/|/property/'))
                    if link:
                        listing['listing_url'] = link.get('href', '')
                        if not listing['listing_url'].startswith('http'):
                            listing['listing_url'] = self.base_url + listing['listing_url']
                    
                    listings.append(listing)
                    logger.debug(f"Extracted listing {idx+1}: {address_match}")

            except Exception as e:
                logger.debug(f"Error parsing listing card: {e}")
                continue

        logger.info(f"Parsed {len(listings)} listings from ByOwner.com")
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
            
            # Alternative pattern: Street | City, State ZIP
            pattern2 = r'^([^|]+)\|\s*(.+?),\s+([A-Z]{2})\s+(\d{5})'
            match2 = re.search(pattern2, text)
            
            if match2:
                return {
                    'street': match2.group(1).strip(),
                    'city': match2.group(2).strip(),
                    'state': match2.group(3).strip(),
                    'zip_code': match2.group(4).strip()
                }
            
            return None
        except Exception as e:
            logger.debug(f"Error extracting address: {e}")
            return None

    def scrape(self) -> List[Dict]:
        """
        Execute scraping using async Playwright.
        Note: This scraper is disabled by default due to Cloudflare protection.
        
        Returns:
            List of normalized listings (empty until Cloudflare bypass is implemented)
        """
        try:
            # Try to run async scrape in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._scrape_async())
            loop.close()
            return result
        except RuntimeError:
            # If event loop is already running, return empty
            logger.warning(f"Could not run Playwright for {self.source_name} - event loop already active")
            logger.warning("This is a known limitation. Consider using undetected-chromedriver or proxy rotation.")
            return []
        except Exception as e:
            logger.error(f"Error in {self.source_name}: {str(e)[:100]}")
            return []

    async def _scrape_async(self) -> List[Dict]:
        """Async version of scrape."""
        all_listings = []
        
        logger.info(f"Starting scrape of {self.source_name}")
        logger.warning(f"⚠️  Note: {self.source_name} uses Cloudflare protection")
        logger.warning(f"    This scraper may not work without additional bypass measures")
        
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

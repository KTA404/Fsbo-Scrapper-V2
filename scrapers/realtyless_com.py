"""
Scraper for RealtyLess.com - Uses Playwright for JavaScript rendering.
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import logging
import re
import asyncio
import json

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class RealtyLessComScraper(BaseScraper):
    """
    Scraper for RealtyLess.com listings.
    Uses Playwright for JavaScript rendering since the site is a React SPA.
    """

    def __init__(self, max_listings: int = 10, scrape_url: str = None):
        """
        Initialize RealtyLess.com scraper.
        
        Args:
            max_listings: Maximum number of listings to scrape
            scrape_url: Custom URL to scrape from (with lat/lng parameters)
        """
        super().__init__(
            source_name='RealtyLess.com',
            base_url='https://realtyless.com',
            min_delay=0.5,
            max_delay=1.0
        )
        self.max_listings = max_listings
        # Default to Tampa Bay area if no URL provided
        self.scrape_url = scrape_url or "https://realtyless.com/postings?lat=28.0035328&lng=-82.7686912"
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
                # Use load event with shorter timeout first
                await page.goto(url, wait_until='load', timeout=12000)
            except Exception as e:
                logger.debug(f"Page load timeout after 12s, continuing: {str(e)[:50]}")
                # Try to get content anyway even if timeout
                pass
            
            # Wait for listings to load - use shorter timeout
            try:
                await page.wait_for_selector('a[href*="/listing"]', timeout=3000)
            except:
                logger.debug("Listing selectors not immediately visible, proceeding")
            
            # Try scrolling with very short waits
            for i in range(2):
                try:
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    # Use very short timeout for scroll loads
                    await page.wait_for_load_state("networkidle", timeout=1000)
                except:
                    pass
            
            # Get page content
            content = await page.content()
            await page.close()
            
            if content and len(content) > 1000:
                logger.debug(f"Retrieved {len(content)} bytes of content")
                return content
            else:
                logger.warning(f"Page content is too small ({len(content) if content else 0} bytes)")
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
        Get list of RealtyLess.com listing URLs.
        
        Returns:
            List with scrape URL
        """
        return [self.scrape_url]

    def parse_listings(self, content: str) -> List[Dict]:
        """
        Parse RealtyLess.com listing HTML from page.
        
        Args:
            content: HTML content
            
        Returns:
            List of extracted listings
        """
        listings = []
        soup = BeautifulSoup(content, 'html.parser')

        # Look for listing links - RealtyLess uses /listing/ID pattern
        listing_links = soup.find_all('a', href=re.compile(r'/listing/\d+'))
        
        logger.debug(f"Found {len(listing_links)} listing links")
        
        for idx, link in enumerate(listing_links[:self.max_listings]):
            try:
                listing_url = link.get('href', '')
                if not listing_url.startswith('http'):
                    listing_url = self.base_url + listing_url
                
                # Get the listing card/container
                card = link.find_parent(['div', 'article', 'li'])
                if not card:
                    card = link.parent
                
                # Extract address - typically in the card heading or near the link
                address_text = ""
                
                # Try various selectors for address
                address_elem = (
                    card.find('h2') or
                    card.find('h3') or
                    card.find(['span', 'div'], class_=re.compile('address|street|title', re.I)) or
                    link.find_parent().find('h2') or
                    link.find_parent().find('h3')
                )
                
                if address_elem:
                    address_text = address_elem.get_text(strip=True)
                
                # Alternative: get text near the link
                if not address_text:
                    # Get parent text and extract first meaningful part
                    parent_text = card.get_text(strip=True)
                    address_text = parent_text[:150]  # Take first 150 chars
                
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
                else:
                    # Try to extract from full text even without standard format
                    logger.debug(f"Could not parse address from: {address_text[:100]}")

            except Exception as e:
                logger.debug(f"Error parsing listing: {str(e)[:100]}")
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
            
            # Fallback: try to find pattern with just state and zip
            pattern3 = r'(.+?),\s+([A-Z]{2})\s+(\d{5})'
            match3 = re.search(pattern3, text)
            
            if match3:
                full_address = match3.group(1).strip()
                state = match3.group(2).strip()
                zip_code = match3.group(3).strip()
                
                # Try to split address into street and city
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
            # If event loop is already running, return empty
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

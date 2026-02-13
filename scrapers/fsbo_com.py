"""
Scraper for FSBO.com - the largest FSBO marketplace.
"""

from typing import List, Dict
from bs4 import BeautifulSoup
import logging
import re
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class FSBOComScraper(BaseScraper):
    """
    Scraper for FSBO.com listings.
    
    Note: FSBO.com may have terms of service restrictions.
    Always check robots.txt and terms before scraping.
    """

    def __init__(self, max_listings: int = 10, scrape_url = None, allowed_states: List[str] = None):
        """
        Initialize FSBO.com scraper.
        
        Args:
            max_listings: Maximum number of listings to scrape (default: 10)
            scrape_url: URL or list of URLs to scrape listing IDs from (default: FSBO homepage)
        """
        super().__init__(
            source_name='FSBO.com',
            base_url='https://fsbo.com',
            min_delay=0.5,
            max_delay=1.0
        )
        self.max_listings = max_listings
        self.allowed_states = [s.strip().upper() for s in (allowed_states or []) if s.strip()]
        # Handle both single URL string and list of URLs
        if scrape_url is None:
            self.scrape_urls = [self.base_url]
        elif isinstance(scrape_url, list):
            self.scrape_urls = scrape_url
        else:
            self.scrape_urls = [scrape_url]

    async def get_listing_urls_with_js(self, scrape_url: str, max_listings_from_url: int) -> List[str]:
        """
        Get listing URLs using Playwright to handle JavaScript-based pagination.
        
        Args:
            scrape_url: URL to scrape
            max_listings_from_url: Max listings to get from this URL
            
        Returns:
            List of unique listing IDs
        """
        listing_ids = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto(scrape_url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)  # Wait for JS to load
                
                page_num = 1
                max_pages = 20  # Limit to prevent infinite loops
                
                while len(listing_ids) < max_listings_from_url and page_num <= max_pages:
                    logger.info(f"Processing page {page_num} of {scrape_url}")
                    
                    # Get page content
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Extract listing IDs
                    links = soup.find_all('a', href=re.compile(r'/listings/listings/show/id/\d+/'))
                    listings_found = 0
                    
                    for link in links:
                        href = link.get('href', '')
                        match = re.search(r'/listings/listings/show/id/(\d+)/', href)
                        if match:
                            listing_id = match.group(1)
                            if listing_id not in listing_ids:
                                listing_ids.append(listing_id)
                                listings_found += 1
                                if len(listing_ids) >= max_listings_from_url:
                                    break
                    
                    logger.info(f"Found {listings_found} new listings on page {page_num}")
                    
                    if listings_found == 0:
                        break
                    
                    # Try to click the "Next" button
                    try:
                        # Look for next button with various selectors
                        next_button = await page.query_selector('a.action.next')
                        if not next_button:
                            next_button = await page.query_selector('a:has-text("next")')
                        if not next_button:
                            next_button = await page.query_selector('a:has-text(">")')
                        
                        if next_button:
                            # Check if button is disabled
                            classes = await next_button.get_attribute('class')
                            if classes and 'disabled' in classes:
                                logger.info("Next button is disabled, reached last page")
                                break
                            
                            logger.info("Clicking next button...")
                            await next_button.click()
                            await page.wait_for_timeout(2000)  # Wait for new content
                            page_num += 1
                        else:
                            logger.info("No next button found, stopping pagination")
                            break
                    except Exception as e:
                        logger.warning(f"Could not click next button: {e}")
                        break
                
            except Exception as e:
                logger.error(f"Error with Playwright pagination: {e}")
            finally:
                await browser.close()
        
        return listing_ids

    def get_listing_urls(self) -> List[str]:
        """
        Get list of FSBO.com listing URLs to scrape.
        Uses Playwright for JavaScript-based pagination on search results.
        
        Returns:
            List of listing page URLs
        """
        listing_ids = []
        
        try:
            # Iterate through all scrape URLs
            for scrape_url in self.scrape_urls:
                if len(listing_ids) >= self.max_listings:
                    break
                
                max_from_this_url = self.max_listings - len(listing_ids)
                
                # Use Playwright for search results pages (they have JS pagination)
                if 'search/results' in scrape_url:
                    logger.info(f"Using Playwright for JS pagination on {scrape_url}")
                    new_ids = asyncio.run(self.get_listing_urls_with_js(scrape_url, max_from_this_url))
                    listing_ids.extend(new_ids)
                else:
                    # Use simple HTTP request for other pages
                    logger.info(f"Using HTTP request for {scrape_url}")
                    response = self.get_page(scrape_url)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    links = soup.find_all('a', href=re.compile(r'/listings/listings/show/id/\d+/'))
                    
                    for link in links:
                        if len(listing_ids) >= self.max_listings:
                            break
                        href = link.get('href', '')
                        match = re.search(r'/listings/listings/show/id/(\d+)/', href)
                        if match:
                            listing_id = match.group(1)
                            if listing_id not in listing_ids:
                                listing_ids.append(listing_id)
            
            logger.info(f"Found {len(listing_ids)} total unique listing IDs")
            
        except Exception as e:
            logger.error(f"Error fetching listing IDs: {e}")
            logger.warning("Using fallback listing IDs")
            listing_ids = ['546971', '546964', '546957', '546954'][:self.max_listings]
        
        # Build full URLs
        urls = []
        for listing_id in listing_ids:
            url = f"{self.base_url}/listings/listings/show/id/{listing_id}/"
            urls.append(url)
        
        return urls

    def parse_listings(self, content: str) -> List[Dict]:
        """
        Parse FSBO.com listing HTML from individual listing pages.
        
        Args:
            content: HTML content
            
        Returns:
            List of extracted listings
        """
        listings = []
        soup = BeautifulSoup(content, 'html.parser')

        # Require bed and bath indicators to keep only home listings
        page_text = soup.get_text(" ", strip=True).lower()
        has_bed = re.search(r'\b\d+(?:\.\d+)?\s*(bd|bed|beds)\b', page_text)
        has_bath = re.search(r'\b\d+(?:\.\d+)?\s*(ba|bath|baths)\b', page_text)
        if not (has_bed and has_bath):
            return listings

        try:
            # Look for the address span which has format: "700 NE 26th Terr #804Miami, FL 33137"
            address_span = soup.find('span', class_='address')
            
            if address_span:
                address_text = address_span.get_text(strip=True)
                logger.info(f"Found address span: {address_text}")
                
                # Parse format: "700 NE 26th Terr #804Miami, FL 33137"
                # This needs to split street from "City, State ZIP"
                match = re.search(
                    r'(.*?)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})\s*(\d{5})',
                    address_text
                )
                
                if match:
                    street = match.group(1).strip()
                    city = match.group(2).strip()
                    state = match.group(3).strip()
                    zip_code = match.group(4).strip()

                    if self.allowed_states and state.upper() not in self.allowed_states:
                        return listings
                    
                    listing = {
                        'street': street,
                        'city': city,
                        'state': state,
                        'zip_code': zip_code,
                        'listing_url': ''
                    }
                    listings.append(listing)
                    logger.info(f"Extracted listing: {street}, {city}, {state} {zip_code}")
                    return listings
            
            # Fallback: Try breadcrumb format "Home>FL>Miami>700 NE 26th Terr #804"
            breadcrumb_div = soup.find('div', class_=lambda x: x and 'row' in x if x else False)
            if breadcrumb_div:
                breadcrumb_text = breadcrumb_div.get_text(strip=True)
                if '>' in breadcrumb_text:
                    logger.info(f"Found breadcrumb: {breadcrumb_text}")
                    parts = [p.strip() for p in breadcrumb_text.split('>')]
                    if len(parts) >= 4:
                        street = parts[-1].strip()
                        city = parts[-2].strip()
                        state = parts[-3].strip()
                        
                        # Look for zip code in the page
                        zip_code = self._extract_zip_from_page(soup)
                        
                        listing = {
                            'street': street,
                            'city': city,
                            'state': state,
                            'zip_code': zip_code,
                            'listing_url': ''
                        }
                        listings.append(listing)
                        logger.info(f"Extracted from breadcrumb: {street}, {city}, {state} {zip_code}")
                        return listings
            
            logger.warning(f"No address found in page. First 200 chars: {soup.get_text()[:200]}")

        except Exception as e:
            logger.error(f"Error parsing FSBO.com listing: {e}", exc_info=True)

        return listings

    def _extract_zip_from_page(self, soup: BeautifulSoup) -> str:
        """Extract ZIP code from page content."""
        # Look for zip code patterns in the page text
        text = soup.get_text()
        match = re.search(r'\b(\d{5})\b', text)
        return match.group(1) if match else ''

    @staticmethod
    def _extract_zip(text: str) -> str:
        """Extract ZIP code from address text."""
        match = re.search(r'\b(\d{5})\b', text)
        return match.group(1) if match else ''

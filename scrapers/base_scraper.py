"""
Base scraper class with common functionality for all FSBO scrapers.
"""

import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import logging
from urllib.parse import urljoin, urlparse

from utils.rate_limiter import RateLimiter, RetryConfig, retry_with_backoff
from utils.user_agents import UserAgentRotator
from utils.address_normalizer import AddressNormalizer

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Base class for all FSBO scrapers.
    Provides common functionality like rate limiting, retries, and user-agent rotation.
    """

    def __init__(self, source_name: str, base_url: str, min_delay: float = 2.0,
                 max_delay: float = 5.0):
        """
        Initialize base scraper.
        
        Args:
            source_name: Name of the source website
            base_url: Base URL of the website
            min_delay: Minimum delay between requests
            max_delay: Maximum delay between requests
        """
        self.source_name = source_name
        self.base_url = base_url
        self.rate_limiter = RateLimiter(min_delay=min_delay, max_delay=max_delay)
        self.user_agent_rotator = UserAgentRotator()
        self.address_normalizer = AddressNormalizer()
        self.retry_config = RetryConfig(max_retries=3, backoff_factor=2.0)
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create configured requests session."""
        session = requests.Session()
        session.headers.update(self.user_agent_rotator.get_headers())
        return session

    @retry_with_backoff(RetryConfig())
    def get_page(self, url: str, **kwargs) -> requests.Response:
        """
        Make GET request with rate limiting and retries.
        
        Args:
            url: URL to fetch
            **kwargs: Additional arguments for requests.get()
            
        Returns:
            Response object
        """
        self.rate_limiter.wait()
        
        headers = self.user_agent_rotator.get_headers()
        
        try:
            response = self.session.get(
                url,
                headers=headers,
                timeout=10,
                **kwargs
            )
            response.raise_for_status()
            logger.debug(f"Successfully fetched {url}")
            return response
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            raise

    def parse_listings(self, content: str) -> List[Dict]:
        """
        Parse listings from page content.
        Must be implemented by subclasses.
        
        Args:
            content: HTML content of page
            
        Returns:
            List of listing dictionaries
        """
        raise NotImplementedError("Subclasses must implement parse_listings()")

    def get_listing_urls(self) -> List[str]:
        """
        Get list of URLs to scrape for listings.
        Must be implemented by subclasses.
        
        Returns:
            List of listing page URLs
        """
        raise NotImplementedError("Subclasses must implement get_listing_urls()")

    def scrape(self) -> List[Dict]:
        """
        Execute full scraping workflow.
        
        Returns:
            List of normalized listings
        """
        all_listings = []
        
        logger.info(f"Starting scrape of {self.source_name}")
        
        try:
            listing_urls = self.get_listing_urls()
            logger.info(f"Found {len(listing_urls)} pages to scrape from {self.source_name}")
            
            for url in listing_urls:
                try:
                    response = self.get_page(url)
                    listings = self.parse_listings(response.text)
                    all_listings.extend(listings)
                    logger.debug(f"Scraped {len(listings)} listings from {url}")
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
                    continue
            
            # Normalize addresses
            normalized = [self._normalize_listing(listing) for listing in all_listings]
            normalized = [l for l in normalized if l is not None]
            
            logger.info(f"Completed scrape of {self.source_name}: {len(normalized)} valid listings")
            return normalized
            
        except Exception as e:
            logger.error(f"Fatal error scraping {self.source_name}: {e}")
            raise

    def _normalize_listing(self, listing: Dict) -> Optional[Dict]:
        """
        Normalize listing to standard format.
        
        Args:
            listing: Raw listing data
            
        Returns:
            Normalized listing or None if invalid
        """
        try:
            normalized = self.address_normalizer.normalize_address(
                street=listing.get('street', ''),
                city=listing.get('city', ''),
                state=listing.get('state', ''),
                zip_code=listing.get('zip_code', '')
            )
            
            if not self.address_normalizer.is_valid_address(
                normalized['street'],
                normalized['city'],
                normalized['state'],
                normalized['zip_code']
            ):
                logger.debug(f"Skipping invalid address: {listing}")
                return None
            
            normalized['listing_url'] = listing.get('listing_url', '')
            normalized['source_website'] = self.source_name
            
            return normalized
            
        except Exception as e:
            logger.debug(f"Error normalizing listing {listing}: {e}")
            return None

    def close(self) -> None:
        """Close session and cleanup."""
        self.session.close()
        logger.debug(f"Closed scraper for {self.source_name}")


class BrowserBasedScraper(BaseScraper):
    """
    Base class for scrapers that require JavaScript rendering.
    Uses Playwright for browser automation.
    """

    def __init__(self, source_name: str, base_url: str, headless: bool = True):
        """
        Initialize browser-based scraper.
        
        Args:
            source_name: Name of the source website
            base_url: Base URL of the website
            headless: Whether to run browser in headless mode
        """
        super().__init__(source_name, base_url)
        self.headless = headless
        self.browser = None
        self.context = None

    async def setup_browser(self):
        """Initialize Playwright browser."""
        try:
            from playwright.async_api import async_playwright
            
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
            self.context = await self.browser.new_context()
            logger.debug(f"Browser initialized for {self.source_name}")
        except ImportError:
            logger.error("Playwright not installed. Install with: pip install playwright")
            raise

    async def cleanup_browser(self):
        """Close browser and cleanup."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.debug(f"Browser closed for {self.source_name}")

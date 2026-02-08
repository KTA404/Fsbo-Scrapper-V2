"""
Scraper for Zillow FSBO listings.
Handles both static and JavaScript-rendered content.
"""

from typing import List, Dict
from bs4 import BeautifulSoup
import logging
import re

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ZillowFSBOScraper(BaseScraper):
    """
    Scraper for Zillow FSBO (For Sale By Owner) listings.
    
    Note: Check Zillow's robots.txt and terms of service.
    Zillow has restrictions on automated scraping.
    """

    def __init__(self):
        """Initialize Zillow FSBO scraper."""
        super().__init__(
            source_name='Zillow FSBO',
            base_url='https://www.zillow.com',
            min_delay=4.0,
            max_delay=10.0
        )

    def get_listing_urls(self) -> List[str]:
        """
        Get Zillow FSBO listing URLs.
        
        Returns:
            List of search page URLs
        """
        # Note: Zillow heavily restricts scraping
        # This is a template - actual implementation would need updates
        
        urls = []
        # Major metro areas
        metros = [
            'new-york-ny',
            'los-angeles-ca',
            'chicago-il',
            'houston-tx',
            'phoenix-az'
        ]
        
        for metro in metros:
            # Template URL structure
            url = f"{self.base_url}/homes/for_sale/{metro}/?fsba=true"
            urls.append(url)
        
        return urls[:2]  # Limit for demo

    def parse_listings(self, content: str) -> List[Dict]:
        """
        Parse Zillow listing HTML.
        
        Args:
            content: HTML content
            
        Returns:
            List of extracted listings
        """
        listings = []
        soup = BeautifulSoup(content, 'html.parser')

        # Template structure - adapt to actual Zillow HTML
        listing_cards = soup.find_all('div', class_='property-card')

        for card in listing_cards:
            try:
                # Extract address
                address_element = card.find('address')
                if not address_element:
                    continue

                address_text = address_element.get_text(strip=True)
                
                # Extract listing URL
                link = card.find('a', class_='property-link')
                listing_url = link['href'] if link else ''

                # Parse address
                parts = [p.strip() for p in address_text.split(',')]
                
                if len(parts) >= 2:
                    listing = {
                        'street': parts[0],
                        'city': parts[1] if len(parts) > 1 else '',
                        'state': self._extract_state(address_text),
                        'zip_code': self.address_normalizer.extract_zip_from_string(address_text) or '',
                        'listing_url': listing_url
                    }
                    listings.append(listing)

            except Exception as e:
                logger.debug(f"Error parsing Zillow listing: {e}")
                continue

        return listings

    @staticmethod
    def _extract_state(address_text: str) -> str:
        """Extract state abbreviation from address."""
        # Look for state pattern at end of address
        match = re.search(r'(\w+),\s*(\w+)\s*(\d{5})', address_text)
        if match:
            return match.group(2)[:2].upper()
        return ''

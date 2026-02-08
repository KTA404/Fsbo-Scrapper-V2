"""
HTML parser utilities for extracting listing data.
"""

from typing import Dict, Optional, List
from bs4 import BeautifulSoup
import re
import logging

logger = logging.getLogger(__name__)


class HTMLParser:
    """Utilities for parsing HTML listing pages."""

    @staticmethod
    def extract_text_by_css(html: str, selector: str) -> Optional[str]:
        """
        Extract text from element matching CSS selector.
        
        Args:
            html: HTML content
            selector: CSS selector
            
        Returns:
            Extracted text or None
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            element = soup.select_one(selector)
            return element.get_text(strip=True) if element else None
        except Exception as e:
            logger.debug(f"Error extracting with selector {selector}: {e}")
            return None

    @staticmethod
    def extract_multiple_by_css(html: str, selector: str) -> List[str]:
        """
        Extract text from all elements matching CSS selector.
        
        Args:
            html: HTML content
            selector: CSS selector
            
        Returns:
            List of extracted texts
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            elements = soup.select(selector)
            return [elem.get_text(strip=True) for elem in elements]
        except Exception as e:
            logger.debug(f"Error extracting multiple with selector {selector}: {e}")
            return []

    @staticmethod
    def extract_attribute(html: str, selector: str, attribute: str) -> Optional[str]:
        """
        Extract attribute from element.
        
        Args:
            html: HTML content
            selector: CSS selector
            attribute: Attribute name (e.g., 'href', 'src')
            
        Returns:
            Attribute value or None
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            element = soup.select_one(selector)
            return element.get(attribute) if element else None
        except Exception as e:
            logger.debug(f"Error extracting attribute {attribute}: {e}")
            return None

    @staticmethod
    def extract_json_ld(html: str) -> Optional[Dict]:
        """
        Extract JSON-LD structured data from HTML.
        
        Args:
            html: HTML content
            
        Returns:
            Parsed JSON-LD data or None
        """
        try:
            import json
            soup = BeautifulSoup(html, 'html.parser')
            script = soup.find('script', {'type': 'application/ld+json'})
            
            if script:
                return json.loads(script.string)
            return None
        except Exception as e:
            logger.debug(f"Error extracting JSON-LD: {e}")
            return None

    @staticmethod
    def extract_by_regex(text: str, pattern: str) -> Optional[str]:
        """
        Extract text using regex pattern.
        
        Args:
            text: Text to search
            pattern: Regex pattern
            
        Returns:
            First match or None
        """
        try:
            match = re.search(pattern, text)
            return match.group(1) if match and match.groups() else (match.group(0) if match else None)
        except Exception as e:
            logger.debug(f"Error extracting with regex {pattern}: {e}")
            return None


class AddressParser:
    """Utilities for parsing address strings."""

    @staticmethod
    def parse_address_line(line: str) -> Dict[str, str]:
        """
        Parse a single line of address into components.
        
        Format variations:
        - "123 Main St, Springfield, IL 62701"
        - "123 Main St\nSpringfield, IL 62701"
        - "123 Main St / Springfield / IL / 62701"
        
        Args:
            line: Address line
            
        Returns:
            Dictionary with address components
        """
        result = {
            'street': '',
            'city': '',
            'state': '',
            'zip_code': ''
        }

        # Extract ZIP code (must have)
        zip_match = re.search(r'\b(\d{5})(?:-(\d{4}))?\b', line)
        if zip_match:
            result['zip_code'] = zip_match.group(1)

        # Split by common delimiters
        parts = re.split(r'[,/\n]', line)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) >= 1:
            # First part is usually street
            result['street'] = parts[0]

        if len(parts) >= 2:
            # Find city (before state/zip)
            for i, part in enumerate(parts[1:], 1):
                # Check if this part contains state abbreviation
                state_match = re.search(r'\b([A-Z]{2})\b', part)
                if state_match:
                    result['state'] = state_match.group(1)
                    if i > 1:
                        result['city'] = parts[1]
                    break
            else:
                # No state found, assume second part is city
                result['city'] = parts[1]

        return result

    @staticmethod
    def parse_address_multiline(street: str, city: str, state: str, 
                               zip_code: str) -> Dict[str, str]:
        """
        Parse address from separate lines.
        
        Args:
            street: Street address
            city: City name
            state: State
            zip_code: ZIP code
            
        Returns:
            Parsed address components
        """
        return {
            'street': street.strip(),
            'city': city.strip(),
            'state': state.strip(),
            'zip_code': zip_code.strip()
        }

    @staticmethod
    def is_likely_address(text: str) -> bool:
        """
        Check if text looks like an address.
        
        Args:
            text: Text to check
            
        Returns:
            True if looks like address
        """
        # Must have street number and ZIP code
        has_number = re.search(r'\b\d{1,5}\b', text)
        has_zip = re.search(r'\b\d{5}\b', text)
        
        return bool(has_number and has_zip)

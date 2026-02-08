"""
Address normalization utilities for USPS-friendly formatting.
Handles standardization of addresses to meet Thanks.io requirements.
"""

import re
from typing import Dict, Optional, Tuple


class AddressNormalizer:
    """Normalizes and standardizes addresses for USPS compatibility."""

    # State abbreviations mapping
    STATE_ABBREV = {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
        'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
        'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
        'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
        'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
        'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
        'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
        'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
        'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
        'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
        'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC'
    }

    # Common street type abbreviations
    STREET_TYPES = {
        'street': 'St', 'st': 'St', 'avenue': 'Ave', 'ave': 'Ave',
        'road': 'Rd', 'rd': 'Rd', 'drive': 'Dr', 'dr': 'Dr',
        'boulevard': 'Blvd', 'blvd': 'Blvd', 'court': 'Ct', 'ct': 'Ct',
        'lane': 'Ln', 'ln': 'Ln', 'way': 'Way', 'way': 'Way',
        'circle': 'Cir', 'cir': 'Cir', 'trail': 'Trl', 'trl': 'Trl',
        'parkway': 'Pkwy', 'pkwy': 'Pkwy', 'plaza': 'Plz', 'plz': 'Plz',
        'terrace': 'Ter', 'ter': 'Ter', 'highway': 'Hwy', 'hwy': 'Hwy',
    }

    @classmethod
    def normalize_address(cls, street: str, city: str, state: str, 
                         zip_code: str) -> Dict[str, str]:
        """
        Normalize address components to USPS standard format.
        
        Args:
            street: Street address
            city: City name
            state: State name or abbreviation
            zip_code: ZIP code (5 or 9 digits)
            
        Returns:
            Dictionary with normalized address components
        """
        return {
            'street': cls.normalize_street(street),
            'city': cls.normalize_city(city),
            'state': cls.normalize_state(state),
            'zip_code': cls.normalize_zip(zip_code)
        }

    @classmethod
    def normalize_street(cls, street: str) -> str:
        """Normalize street address format."""
        if not street:
            return ""
        
        # Clean whitespace
        street = ' '.join(street.split())
        
        # Capitalize words
        street = street.title()
        
        # Standardize direction prefixes
        street = re.sub(r'\b(North|South|East|West|Northeast|Northwest|Southeast|Southwest)\b',
                       lambda m: m.group(1)[:1], street)
        
        # Standardize street types
        for full, abbrev in cls.STREET_TYPES.items():
            pattern = rf'\b{full}\b'
            street = re.sub(pattern, abbrev, street, flags=re.IGNORECASE)
        
        return street.strip()

    @classmethod
    def normalize_city(cls, city: str) -> str:
        """Normalize city name."""
        if not city:
            return ""
        
        # Clean and title case
        city = ' '.join(city.split())
        return city.title().strip()

    @classmethod
    def normalize_state(cls, state: str) -> str:
        """Convert state to 2-letter abbreviation."""
        if not state:
            return ""
        
        state = state.strip().lower()
        
        # Already abbreviated
        if len(state) == 2 and state.isupper():
            return state.upper()
        
        # Look up in mapping
        if state in cls.STATE_ABBREV:
            return cls.STATE_ABBREV[state]
        
        return state.upper()

    @classmethod
    def normalize_zip(cls, zip_code: str) -> str:
        """Normalize ZIP code (format as 5 or 9 digits)."""
        if not zip_code:
            return ""
        
        # Remove non-digits
        digits = re.sub(r'\D', '', zip_code)
        
        # Return 5 or 9 digit format
        if len(digits) >= 9:
            return f"{digits[:5]}-{digits[5:9]}"
        elif len(digits) == 5:
            return digits
        else:
            return ""

    @classmethod
    def format_mailing_label(cls, address_dict: Dict[str, str]) -> str:
        """
        Format address for postcard mailing label format.
        
        Returns:
            Multi-line string ready for Thanks.io import
        """
        return f"{address_dict['street']}\n{address_dict['city']}, {address_dict['state']} {address_dict['zip_code']}"

    @classmethod
    def is_valid_address(cls, street: str, city: str, state: str, zip_code: str) -> bool:
        """Check if address has minimum required components."""
        return bool(street) and bool(city) and bool(state) and bool(zip_code)

    @classmethod
    def extract_zip_from_string(cls, text: str) -> Optional[str]:
        """Extract ZIP code from text."""
        match = re.search(r'\b(\d{5})(?:-(\d{4}))?\b', text)
        return match.group(0) if match else None

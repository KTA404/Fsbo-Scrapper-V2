"""
Unit tests for FSBO Scraper components.
"""

import unittest
from utils.address_normalizer import AddressNormalizer
from utils.rate_limiter import RateLimiter
from utils.user_agents import UserAgentRotator


class TestAddressNormalizer(unittest.TestCase):
    """Test address normalization."""

    def test_normalize_street(self):
        """Test street normalization."""
        result = AddressNormalizer.normalize_street("123 main street")
        self.assertEqual(result, "123 Main Street")

    def test_normalize_street_types(self):
        """Test street type abbreviation."""
        result = AddressNormalizer.normalize_street("123 Main Street")
        self.assertIn("St", result)

        result = AddressNormalizer.normalize_street("456 Oak Avenue")
        self.assertIn("Ave", result)

    def test_normalize_state(self):
        """Test state normalization."""
        result = AddressNormalizer.normalize_state("illinois")
        self.assertEqual(result, "IL")

        result = AddressNormalizer.normalize_state("ca")
        self.assertEqual(result, "CA")

        result = AddressNormalizer.normalize_state("TX")
        self.assertEqual(result, "TX")

    def test_normalize_zip(self):
        """Test ZIP code normalization."""
        result = AddressNormalizer.normalize_zip("62701")
        self.assertEqual(result, "62701")

        result = AddressNormalizer.normalize_zip("62701-1234")
        self.assertEqual(result, "62701-1234")

        # Remove non-digits
        result = AddressNormalizer.normalize_zip("62701 ")
        self.assertEqual(result, "62701")

    def test_is_valid_address(self):
        """Test address validation."""
        valid = AddressNormalizer.is_valid_address(
            "123 Main St", "Springfield", "IL", "62701"
        )
        self.assertTrue(valid)

        invalid = AddressNormalizer.is_valid_address(
            "", "Springfield", "IL", "62701"
        )
        self.assertFalse(invalid)

    def test_extract_zip(self):
        """Test ZIP code extraction."""
        result = AddressNormalizer.extract_zip_from_string(
            "123 Main St, Springfield IL 62701"
        )
        self.assertEqual(result, "62701")

    def test_format_mailing_label(self):
        """Test mailing label formatting."""
        addr = {
            'street': '123 Main St',
            'city': 'Springfield',
            'state': 'IL',
            'zip_code': '62701'
        }
        result = AddressNormalizer.format_mailing_label(addr)
        self.assertIn('123 Main St', result)
        self.assertIn('Springfield', result)
        self.assertIn('IL', result)
        self.assertIn('62701', result)


class TestRateLimiter(unittest.TestCase):
    """Test rate limiting."""

    def test_rate_limiter_creation(self):
        """Test creating rate limiter."""
        limiter = RateLimiter(min_delay=1.0, max_delay=3.0)
        self.assertEqual(limiter.min_delay, 1.0)
        self.assertEqual(limiter.max_delay, 3.0)

    def test_rate_limiter_wait(self):
        """Test rate limiter wait."""
        import time
        limiter = RateLimiter(min_delay=0.1, max_delay=0.2, jitter=False)
        
        start = time.time()
        limiter.wait()
        elapsed = time.time() - start
        
        self.assertGreaterEqual(elapsed, 0.09)


class TestUserAgentRotator(unittest.TestCase):
    """Test user agent rotation."""

    def test_get_random_user_agent(self):
        """Test getting random user agent."""
        rotator = UserAgentRotator()
        ua = rotator.get_random_user_agent()
        
        self.assertIsNotNone(ua)
        self.assertIn('Mozilla', ua)

    def test_get_headers(self):
        """Test getting complete headers."""
        rotator = UserAgentRotator()
        headers = rotator.get_headers()
        
        self.assertIn('User-Agent', headers)
        self.assertIn('Accept', headers)
        self.assertIn('Accept-Language', headers)

    def test_current_user_agent(self):
        """Test tracking current user agent."""
        rotator = UserAgentRotator()
        ua1 = rotator.get_current_user_agent()
        ua2 = rotator.get_current_user_agent()
        
        # Should be same until explicitly rotated
        self.assertEqual(ua1, ua2)


if __name__ == '__main__':
    unittest.main()

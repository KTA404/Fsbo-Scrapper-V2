# Adding New FSBO Sites - Developer Guide

This guide explains how to add support for new FSBO (For Sale By Owner) property listing websites to the scraper.

## Understanding the Architecture

### Scraper Hierarchy

```
BaseScraper (base_scraper.py)
├── HTTPScraper (for static HTML pages)
└── BrowserBasedScraper (for JavaScript-rendered pages)
```

All scrapers inherit from `BaseScraper` which provides:

- Rate limiting
- User-Agent rotation
- Request retries with exponential backoff
- Address normalization
- Error handling and logging

## Adding a Static HTML Site

### Step 1: Analyze the Target Website

1. Open the website in a browser
2. Use Developer Tools (F12) to inspect the HTML structure
3. Identify:
   - URL patterns for listing pages
   - CSS selectors for listing containers
   - CSS selectors for address components
   - URL pattern for individual listings

**Example HTML structure:**

```html
<div class="listing-item">
  <h2 class="address">123 Main Street</h2>
  <span class="city">Springfield</span>
  <span class="state">IL</span>
  <span class="zip">62701</span>
  <a href="/listing/123" class="listing-link">View Listing</a>
</div>
```

### Step 2: Create Scraper File

Create `scrapers/my_site.py`:

```python
"""
Scraper for MyFSBO.com - Example static site scraper.
"""

from typing import List, Dict
from bs4 import BeautifulSoup
import logging
import re

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class MyFSBOScraper(BaseScraper):
    """Scraper for MyFSBO.com listings."""

    def __init__(self):
        """Initialize MyFSBO scraper."""
        super().__init__(
            source_name='MyFSBO.com',
            base_url='https://www.myfsbo.com',
            min_delay=2.0,      # Minimum delay between requests
            max_delay=5.0       # Maximum delay between requests
        )

    def get_listing_urls(self) -> List[str]:
        """
        Get list of URLs to scrape.

        Returns:
            List of search page URLs to scrape
        """
        urls = []

        # Example 1: Paginated search results
        for page in range(1, 6):
            url = f"{self.base_url}/search?page={page}"
            urls.append(url)

        # Example 2: State-based URLs
        states = ['AL', 'CA', 'IL', 'NY', 'TX']
        for state in states:
            url = f"{self.base_url}/listings/{state}"
            urls.append(url)

        # Example 3: Metro area URLs
        metros = ['new-york', 'los-angeles', 'chicago']
        for metro in metros:
            url = f"{self.base_url}/metro/{metro}/listings"
            urls.append(url)

        return urls

    def parse_listings(self, content: str) -> List[Dict]:
        """
        Parse HTML and extract listings.

        Args:
            content: HTML content of page

        Returns:
            List of listing dictionaries
        """
        listings = []
        soup = BeautifulSoup(content, 'html.parser')

        # Find all listing containers
        for item in soup.find_all('div', class_='listing-item'):
            try:
                # Extract address components
                address = item.find('h2', class_='address')
                city_elem = item.find('span', class_='city')
                state_elem = item.find('span', class_='state')
                zip_elem = item.find('span', class_='zip')
                link = item.find('a', class_='listing-link')

                # Validate required fields
                if not all([address, city_elem, state_elem, zip_elem]):
                    logger.debug("Missing required address fields")
                    continue

                street = address.get_text(strip=True)
                city = city_elem.get_text(strip=True)
                state = state_elem.get_text(strip=True)
                zip_code = zip_elem.get_text(strip=True)

                # Get listing URL
                listing_url = ''
                if link:
                    href = link.get('href', '')
                    # Convert relative URLs to absolute
                    if href:
                        listing_url = href if href.startswith('http') else f"{self.base_url}{href}"

                # Create listing dictionary
                listing = {
                    'street': street,
                    'city': city,
                    'state': state,
                    'zip_code': zip_code,
                    'listing_url': listing_url
                }

                listings.append(listing)

            except Exception as e:
                logger.debug(f"Error parsing listing item: {e}")
                continue

        logger.debug(f"Extracted {len(listings)} listings from page")
        return listings
```

### Step 3: Test the Scraper

Create `test_my_site.py`:

```python
from scrapers.my_site import MyFSBOScraper

def test_scraper():
    scraper = MyFSBOScraper()

    # Test getting URLs
    urls = scraper.get_listing_urls()
    print(f"Found {len(urls)} pages to scrape")

    # Test parsing a sample page
    if urls:
        try:
            response = scraper.get_page(urls[0])
            listings = scraper.parse_listings(response.text)
            print(f"Parsed {len(listings)} listings")

            if listings:
                print(f"Sample: {listings[0]}")
        except Exception as e:
            print(f"Error: {e}")

    scraper.close()

if __name__ == '__main__':
    test_scraper()
```

Run the test:

```bash
python test_my_site.py
```

## Adding a JavaScript-Rendered Site

For sites that load content dynamically with JavaScript:

```python
"""
Scraper for JavaScriptFSBO.com - Browser-based scraper example.
"""

import asyncio
from typing import List, Dict
from bs4 import BeautifulSoup
import logging

from .base_scraper import BrowserBasedScraper

logger = logging.getLogger(__name__)


class JavaScriptFSBOScraper(BrowserBasedScraper):
    """Scraper for JavaScriptFSBO.com (JS-rendered listings)."""

    def __init__(self):
        """Initialize JS-based scraper."""
        super().__init__(
            source_name='JavaScriptFSBO.com',
            base_url='https://www.jsfsbo.com',
            headless=True  # Run browser in headless mode
        )

    def get_listing_urls(self) -> List[str]:
        """Get URLs to scrape."""
        return [
            f"{self.base_url}/listings",
            f"{self.base_url}/listings?state=CA",
            f"{self.base_url}/listings?state=NY",
        ]

    async def parse_listings_async(self, page) -> List[Dict]:
        """
        Parse listings from Playwright page.

        Args:
            page: Playwright page object

        Returns:
            List of listings
        """
        listings = []

        # Wait for content to load
        await page.wait_for_selector('.listing-item', timeout=5000)

        # Get page content
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')

        # Parse listings
        for item in soup.find_all('div', class_='listing-item'):
            try:
                street = item.find('span', class_='street').text
                city = item.find('span', class_='city').text
                state = item.find('span', class_='state').text
                zip_code = item.find('span', class_='zip').text

                listings.append({
                    'street': street,
                    'city': city,
                    'state': state,
                    'zip_code': zip_code,
                    'listing_url': page.url
                })
            except Exception as e:
                logger.debug(f"Error parsing listing: {e}")

        return listings

    def parse_listings(self, content: str) -> List[Dict]:
        """
        Placeholder for sync interface.
        Use async version with Playwright.
        """
        # This would be called by async scraper
        raise NotImplementedError("Use async version with Playwright")
```

## Registering Your New Scraper

### 1. Add to Scrapers Package

Edit `scrapers/__init__.py`:

```python
from .my_site import MyFSBOScraper

__all__ = [
    'BaseScraper',
    'BrowserBasedScraper',
    'FSBOComScraper',
    'ZillowFSBOScraper',
    'CraigslistHousingScraper',
    'MyFSBOScraper',  # Add your scraper
]
```

### 2. Register in CLI

Edit `main.py` in `ScraperContext.__init__`:

```python
from scrapers.my_site import MyFSBOScraper

class ScraperContext:
    def __init__(self):
        self.scrapers = {
            'fsbo_com': FSBOComScraper,
            'zillow_fsbo': ZillowFSBOScraper,
            'craigslist_housing': CraigslistHousingScraper,
            'my_fsbo': MyFSBOScraper,  # Add this
        }
```

### 3. Add to Configuration

Edit `config/sites.json`:

```json
{
  "sites": [
    {
      "name": "MyFSBO.com",
      "scraper": "my_fsbo",
      "enabled": true,
      "description": "My FSBO marketplace",
      "min_delay": 2.0,
      "max_delay": 5.0
    }
  ]
}
```

## Best Practices

### 1. Respect robots.txt

```python
from urllib.robotparser import RobotFileParser

def can_scrape(self, url: str) -> bool:
    """Check if URL can be scraped per robots.txt."""
    rp = RobotFileParser()
    rp.set_url(f"{self.base_url}/robots.txt")
    rp.read()
    return rp.can_fetch("*", url)
```

### 2. Handle Rate Limiting

```python
# Built-in with BaseScraper:
self.rate_limiter.wait()  # Automatic delay
```

### 3. Proper Error Handling

```python
try:
    response = self.get_page(url)
    listings = self.parse_listings(response.text)
except requests.RequestException as e:
    logger.error(f"Network error: {e}")
except Exception as e:
    logger.error(f"Parsing error: {e}")
```

### 4. Log Effectively

```python
logger.debug(f"Extracted {len(listings)} listings")
logger.warning(f"Missing fields in listing")
logger.error(f"Failed to scrape: {error}")
```

### 5. Validate Data

```python
def _normalize_listing(self, listing: Dict) -> Optional[Dict]:
    """Validate and normalize listing."""
    if not self.address_normalizer.is_valid_address(
        listing['street'],
        listing['city'],
        listing['state'],
        listing['zip_code']
    ):
        logger.debug("Invalid address")
        return None

    return listing
```

## Testing Your Scraper

### Unit Tests

Create `tests/test_my_scraper.py`:

```python
import unittest
from scrapers.my_site import MyFSBOScraper


class TestMyFSBOScraper(unittest.TestCase):

    def setUp(self):
        self.scraper = MyFSBOScraper()

    def test_get_listing_urls(self):
        urls = self.scraper.get_listing_urls()
        self.assertGreater(len(urls), 0)
        self.assertTrue(all(url.startswith('http') for url in urls))

    def test_parse_listings(self):
        html = '''
        <div class="listing-item">
            <h2 class="address">123 Main St</h2>
            <span class="city">Springfield</span>
            <span class="state">IL</span>
            <span class="zip">62701</span>
            <a href="/listing/1" class="listing-link">View</a>
        </div>
        '''

        listings = self.scraper.parse_listings(html)
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0]['street'], '123 Main St')
        self.assertEqual(listings[0]['city'], 'Springfield')

    def tearDown(self):
        self.scraper.close()


if __name__ == '__main__':
    unittest.main()
```

Run tests:

```bash
python -m pytest tests/
```

## Troubleshooting

### Issue: "No listings found"

1. Check CSS selectors match actual HTML
2. Verify with browser developer tools
3. Enable debug logging: `export LOG_LEVEL=DEBUG`

### Issue: "Connection timeout"

1. Increase request timeout in scraper
2. Reduce requests per minute
3. Check if site blocks automated requests

### Issue: "Invalid address extracted"

1. Verify parsing logic extracts all fields
2. Check address normalization
3. Review example output

## Performance Optimization

### Concurrent Scraping

```python
from concurrent.futures import ThreadPoolExecutor

def scrape_multiple_urls(urls: List[str], max_workers: int = 3):
    listings = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(self.scrape_url, url) for url in urls]

        for future in futures:
            try:
                listings.extend(future.result())
            except Exception as e:
                logger.error(f"Error in concurrent scrape: {e}")

    return listings
```

### Caching

```python
import functools
import time

@functools.lru_cache(maxsize=128)
def get_state_listings(state: str, max_age: int = 3600):
    """Cache listings for 1 hour."""
    # Implementation
    pass
```

## Legal Considerations

Always:

- ✅ Check `robots.txt`
- ✅ Review Terms of Service
- ✅ Respect rate limits
- ✅ Use appropriate User-Agent
- ❌ Never bypass authentication
- ❌ Never scrape paywalled content

## Submitting New Scrapers

To contribute a new scraper:

1. Follow the guidelines above
2. Add unit tests
3. Document the scraper
4. Submit a pull request

## Support

For issues or questions:

1. Check the main README
2. Review similar scrapers for patterns
3. Check application logs
4. Test with `--log-level DEBUG`

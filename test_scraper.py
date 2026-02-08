#!/usr/bin/env python
"""Quick test of the FSBO scraper."""

from scrapers import FSBOComScraper
import logging

# Enable debug logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Create scraper
scraper = FSBOComScraper()

# Override rate limiter for testing
scraper.rate_limiter.min_delay = 0.5
scraper.rate_limiter.max_delay = 1.0

print("Testing FSBO.com scraper...")
urls = scraper.get_listing_urls()
print(f"Will scrape {len(urls)} URLs")
for url in urls:
    print(f"  - {url}")
print()

# Run scraper
print("Starting scrape...")
listings = scraper.scrape()

print(f"\n✅ Scraping complete!")
print(f"Found {len(listings)} listings\n")

# Print results
for i, listing in enumerate(listings, 1):
    print(f"{i}. {listing.get('street', 'N/A')}")
    print(f"   {listing.get('city', 'N/A')}, {listing.get('state', 'N/A')} {listing.get('zip_code', 'N/A')}")
    print(f"   URL: {listing.get('listing_url', 'N/A')}")
    print()

scraper.close()

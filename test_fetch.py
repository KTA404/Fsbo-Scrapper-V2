#!/usr/bin/env python
"""Test the actual scraper fetch."""

from scrapers import FSBOComScraper

scraper = FSBOComScraper()
url = "https://fsbo.com/listings/listings/show/id/546971/"

print(f"Fetching: {url}")
response = scraper.get_page(url)

print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type')}")
print(f"Content-Encoding: {response.headers.get('Content-Encoding')}")
print(f"Response encoding: {response.encoding}")
print(f"\nFirst 200 chars of text:")
print(repr(response.text[:200]))

scraper.close()

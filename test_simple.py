#!/usr/bin/env python
"""Direct test of fetching and parsing one page."""

import requests
from bs4 import BeautifulSoup
import re

url = "https://fsbo.com/listings/listings/show/id/546971/"

print(f"Fetching: {url}")
response = requests.get(url, timeout=10)
print(f"Status: {response.status_code}\n")

soup = BeautifulSoup(response.text, 'html.parser')

# Look for breadcrumb
breadcrumb = soup.find('div', class_='breadcrumbs')
if breadcrumb:
    print("Found breadcrumb:")
    print(f"  {breadcrumb.get_text(strip=True)[:200]}")
    print()

# Look for address patterns
body_text = soup.get_text()
address_match = re.search(
    r'(\d+\s+[A-Za-z0-9\s\.\#\-]+?)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*([A-Z]{2})\s*(\d{5})',
    body_text
)

if address_match:
    print("Found address via regex:")
    print(f"  Street: {address_match.group(1).strip()}")
    print(f"  City: {address_match.group(2).strip()}")
    print(f"  State: {address_match.group(3).strip()}")
    print(f"  ZIP: {address_match.group(4).strip()}")
else:
    print("No address match found")
    print("\nFirst 500 chars of body text:")
    print(body_text[:500])

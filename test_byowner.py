#!/usr/bin/env python
"""Test fetching from byowner.com"""

import requests
from bs4 import BeautifulSoup
import re

url = "https://www.byowner.com/miami/florida"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print(f"Fetching: {url}")
response = requests.get(url, headers=headers, timeout=10)

print(f"Status: {response.status_code}")
print(f"URL: {response.url}")

soup = BeautifulSoup(response.text, 'html.parser')

# Look for property cards or listings
cards = soup.find_all(['article', 'div'], class_=re.compile('card|listing|property', re.I))

print(f"\nFound {len(cards)} property cards")

# Look for links to individual properties
import re
property_links = soup.find_all('a', href=re.compile(r'/property/', re.I))

print(f"Found {len(property_links)} property links")
for link in property_links[:10]:
    href = link.get('href', '')
    text = link.get_text(strip=True)
    print(f"  {href[:80]}")
    print(f"    Text: {text[:60]}")

# Print first 2000 chars
print(f"\nFirst 1500 chars of body:")
print(soup.get_text()[:1500])

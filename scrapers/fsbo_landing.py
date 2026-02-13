"""
Scraper for generic FSBO landing pages on the web.
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import logging
import re
from urllib.parse import urljoin, urlparse, parse_qs, unquote

from .base_scraper import BaseScraper
from parsers.html_parser import AddressParser, HTMLParser

logger = logging.getLogger(__name__)


class FSBOLandingPageScraper(BaseScraper):
    """
    Scrape generic FSBO landing pages and extract addresses.

    This scraper is intended for static landing pages that list multiple
    FSBO properties on a single page.
    """

    def __init__(
        self,
        landing_urls: Optional[List[str]] = None,
        max_listings: int = 50,
        search_queries: Optional[List[str]] = None,
        max_search_results: int = 20,
        allowlist_domains: Optional[List[str]] = None,
        allowed_states: Optional[List[str]] = None,
        blacklist_domains: Optional[List[str]] = None
    ):
        """
        Initialize landing page scraper.

        Args:
            landing_urls: List of landing page URLs to scan
            max_listings: Maximum listings to extract across all pages
        """
        super().__init__(
            source_name='FSBO Landing Pages',
            base_url='',
            min_delay=1.0,
            max_delay=3.0
        )
        self.landing_urls = landing_urls or []
        self.max_listings = max_listings
        self.search_queries = search_queries or []
        self.max_search_results = max_search_results
        self.allowlist_domains = [d.lower().strip() for d in (allowlist_domains or []) if d.strip()]
        self.allowed_states = [s.strip().upper() for s in (allowed_states or []) if s.strip()]
        self.blacklist_domains = [d.lower().strip() for d in (blacklist_domains or []) if d.strip()]

    def get_listing_urls(self) -> List[str]:
        """
        Return landing pages to scan.
        """
        urls: List[str] = []
        if self.landing_urls:
            urls = self.landing_urls
        elif self.search_queries:
            urls = self._discover_landing_urls(self.search_queries, self.max_search_results)

        return [u for u in urls if self._is_allowed_domain(u)]

    def parse_listings(self, content: str) -> List[Dict]:
        """
        Parse landing page HTML and extract addresses.
        """
        listings: List[Dict] = []
        seen = set()

        soup = BeautifulSoup(content, 'html.parser')

        # 1) Try JSON-LD structured data first
        json_ld = HTMLParser.extract_json_ld(content)
        if json_ld:
            self._extract_from_json_ld(json_ld, listings, seen)

        # 2) Extract addresses from visible text blocks
        text_candidates = self._collect_text_candidates(soup)
        for text in text_candidates:
            if len(listings) >= self.max_listings:
                break
            if not AddressParser.is_likely_address(text):
                continue
            if not self._is_plausible_address_text(text):
                continue
            parsed = AddressParser.parse_address_line(text)
            if not self._is_allowed_state(parsed):
                continue
            listing = self._to_listing(parsed, listing_url='')
            if listing and self._add_unique(listings, seen, listing):
                continue

        return listings

    def _discover_landing_urls(self, queries: List[str], max_results: int) -> List[str]:
        """
        Discover landing pages via web search.

        Uses DuckDuckGo HTML results (no API key required).
        """
        discovered = []

        for query in queries:
            if len(discovered) >= max_results:
                break
            try:
                search_url = "https://duckduckgo.com/html/"
                response = self.get_page(search_url, params={"q": query})
                soup = BeautifulSoup(response.text, 'html.parser')

                for link in soup.select('a.result__a'):
                    href = link.get('href', '')
                    if not href:
                        continue
                    href = href.strip()
                    if href.startswith('javascript:'):
                        continue
                    if 'duckduckgo.com/y.js' in href or 'ad_domain=' in href or 'ad_provider=' in href:
                        continue

                    # Normalize scheme-relative and relative links
                    if href.startswith('//'):
                        href = 'https:' + href
                    href = urljoin(search_url, href)

                    # Unwrap DuckDuckGo redirect links
                    parsed = urlparse(href)
                    if 'duckduckgo.com' in parsed.netloc and parsed.path.startswith('/l/'):
                        qs = parse_qs(parsed.query)
                        if 'uddg' in qs and qs['uddg']:
                            href = unquote(qs['uddg'][0])
                            if 'duckduckgo.com/y.js' in href:
                                continue

                    # Skip DuckDuckGo scripts/ads and non-http(s)
                    parsed = urlparse(href)
                    if 'duckduckgo.com' in parsed.netloc:
                        continue
                    if parsed.scheme not in ('http', 'https'):
                        continue
                    if 'ad_domain=' in href or 'ad_provider=' in href:
                        continue

                    if not self._is_allowed_domain(href):
                        continue
                    if href not in discovered:
                        discovered.append(href)
                    if len(discovered) >= max_results:
                        break
            except Exception as e:
                logger.debug(f"Search failed for query '{query}': {str(e)[:100]}")

        logger.info(f"Discovered {len(discovered)} landing page URLs from search")
        return discovered

    def _is_allowed_domain(self, url: str) -> bool:
        """
        Check if URL is within allowlist domains (if provided).
        """
        try:
            host = urlparse(url).netloc.lower()
            if not host:
                return False
            if self.blacklist_domains:
                if any(host == domain or host.endswith(f".{domain}") for domain in self.blacklist_domains):
                    return False
            if not self.allowlist_domains:
                return True
            return any(host == domain or host.endswith(f".{domain}") for domain in self.allowlist_domains)
        except Exception:
            return False

    def scrape(self) -> List[Dict]:
        """
        Execute full scraping workflow, preserving landing page URL.
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
                    for listing in listings:
                        if not listing.get('listing_url'):
                            listing['listing_url'] = url
                    all_listings.extend(listings)
                    logger.debug(f"Scraped {len(listings)} listings from {url}")
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
                    continue

            normalized = [self._normalize_listing(listing) for listing in all_listings]
            normalized = [l for l in normalized if l is not None]

            logger.info(f"Completed scrape of {self.source_name}: {len(normalized)} valid listings")
            return normalized

        except Exception as e:
            logger.error(f"Fatal error scraping {self.source_name}: {e}")
            raise

    def _collect_text_candidates(self, soup: BeautifulSoup) -> List[str]:
        """
        Collect candidate address strings from common elements.
        """
        candidates = []

        # Common selectors where addresses appear
        selectors = [
            'address',
            '[class*="address"]',
            '[class*="location"]',
            '[class*="listing"]',
            '[class*="property"]'
        ]

        for selector in selectors:
            for elem in soup.select(selector):
                text = elem.get_text(" ", strip=True)
                if text:
                    candidates.append(text)

        # Fallback: scan text nodes for ZIP patterns
        body_text = soup.get_text("\n", strip=True)
        for line in body_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if re.search(r'\b\d{5}\b', line):
                candidates.append(line)

        # De-duplicate while preserving order
        seen = set()
        unique = []
        for c in candidates:
            if c in seen:
                continue
            seen.add(c)
            unique.append(c)
        return unique

    @staticmethod
    def _is_plausible_address_text(text: str) -> bool:
        """
        Heuristic filter to drop non-address UI text blocks.
        """
        cleaned = re.sub(r'\s+', ' ', text).strip()

        # Too long or too many words usually indicates page chrome
        if len(cleaned) > 240:
            return False
        if len(cleaned.split()) > 28:
            return False

        # Must have a street number
        if not re.search(r'\b\d{1,5}\b', cleaned):
            return False

        # Block common UI/auth text
        blocked_phrases = [
            'sign in', 'sign up', 'login', 'continue with', 'get started',
            'forgot password', 'mortgage', 'payment calculator',
            'home affordability', 'welcome', 'by clicking', 'privacy',
            'terms', 'list my property'
        ]
        lower = cleaned.lower()
        if any(p in lower for p in blocked_phrases):
            return False

        return True



    def _extract_from_json_ld(self, json_ld: Dict, listings: List[Dict], seen: set) -> None:
        """
        Extract addresses from JSON-LD structures.
        """
        try:
            items = json_ld if isinstance(json_ld, list) else [json_ld]
            for item in items:
                if len(listings) >= self.max_listings:
                    break
                address = None

                if isinstance(item, dict):
                    address = item.get('address')

                    # ItemList with itemListElement
                    if not address and 'itemListElement' in item:
                        for elem in item.get('itemListElement', []):
                            if isinstance(elem, dict):
                                addr = elem.get('address') or (elem.get('item') or {}).get('address')
                                if addr:
                                    self._add_from_json_ld_address(addr, listings, seen)
                        continue

                    if address:
                        self._add_from_json_ld_address(address, listings, seen)
        except Exception as e:
            logger.debug(f"JSON-LD parsing failed: {str(e)[:100]}")

    def _add_from_json_ld_address(self, address: Dict, listings: List[Dict], seen: set) -> None:
        """
        Add listing from JSON-LD address block.
        """
        if not isinstance(address, dict):
            return

        listing = self._to_listing(
            {
                'street': address.get('streetAddress', ''),
                'city': address.get('addressLocality', ''),
                'state': address.get('addressRegion', ''),
                'zip_code': address.get('postalCode', '')
            },
            listing_url=''
        )
        if listing:
            self._add_unique(listings, seen, listing)

    @staticmethod
    def _to_listing(parsed: Dict[str, str], listing_url: str) -> Optional[Dict]:
        """
        Convert parsed address to listing dict.
        """
        if not parsed:
            return None

        street = parsed.get('street', '').strip()
        city = parsed.get('city', '').strip()
        state = parsed.get('state', '').strip()
        zip_code = parsed.get('zip_code', '').strip()

        if not (street and city and state and zip_code):
            return None

        # Reject price-like or incomplete street lines
        if street.startswith('$'):
            return None
        if not re.search(r'\b\d{1,5}\b', street):
            return None

        return {
            'street': street,
            'city': city,
            'state': state,
            'zip_code': zip_code,
            'listing_url': listing_url
        }

    def _is_allowed_state(self, parsed: Dict[str, str]) -> bool:
        """
        Check if parsed state is within allowed states (if provided).
        """
        if not self.allowed_states:
            return True
        state = (parsed.get('state') or '').strip().upper()
        return state in self.allowed_states

    @staticmethod
    def _add_unique(listings: List[Dict], seen: set, listing: Dict) -> bool:
        key = (listing['street'], listing['city'], listing['state'], listing['zip_code'])
        if key in seen:
            return False
        seen.add(key)
        listings.append(listing)
        return True

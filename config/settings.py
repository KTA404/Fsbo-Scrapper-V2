"""
Application settings and configuration.
"""

import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Database
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'data/fsbo_listings.db')
EXPORT_DIR = os.environ.get('EXPORT_DIR', 'exports')

# Logging
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.environ.get('LOG_FILE', 'logs/scraper.log')

# Scraping
MIN_REQUEST_DELAY = float(os.environ.get('MIN_REQUEST_DELAY', '1.0'))
MAX_REQUEST_DELAY = float(os.environ.get('MAX_REQUEST_DELAY', '5.0'))
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '10'))
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '3'))
RETRY_BACKOFF = float(os.environ.get('RETRY_BACKOFF', '2.0'))

# Rate limiting
MAX_REQUESTS_PER_MINUTE = int(os.environ.get('MAX_REQUESTS_PER_MINUTE', '60'))

# Playwright (for JS-rendered pages)
HEADLESS = os.environ.get('HEADLESS', 'true').lower() == 'true'
PLAYWRIGHT_TIMEOUT = int(os.environ.get('PLAYWRIGHT_TIMEOUT', '30000'))

# Thanks.io integration
THANKS_IO_API_KEY = os.environ.get('THANKS_IO_API_KEY', '')
THANKS_IO_CAMPAIGN_ID = os.environ.get('THANKS_IO_CAMPAIGN_ID', '')

# Enabled scrapers (can be overridden in config/sites.json)
ENABLED_SCRAPERS = [
    'fsbo_com',
    'zillow_fsbo',
    'craigslist_housing'
]

# Create necessary directories
Path(EXPORT_DIR).mkdir(parents=True, exist_ok=True)
Path('logs').mkdir(parents=True, exist_ok=True)

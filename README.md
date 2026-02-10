# FSBO Scraper V2

A Python-based web scraping system that discovers and extracts For Sale By Owner (FSBO) property listings and stores mailing addresses for postcard marketing via Thanks.io.

## 🎯 Features

- **Multiple FSBO Sources**: Scrapes FSBO.com, Zillow FSBO, Craigslist, and easily extensible to more sources
- **Smart Address Normalization**: Converts addresses to USPS-friendly formatting
- **Duplicate Prevention**: Automatically prevents duplicate addresses across scraping runs
- **SQLite Database**: Local persistent storage of all listings
- **CSV Export**: Exports data in Thanks.io-compatible format
- **Rate Limiting**: Respectful scraping with configurable delays and retries
- **User-Agent Rotation**: Realistic browser headers to avoid detection
- **CLI Interface**: Easy-to-use command-line tool for all operations
- **Scrape History**: Tracks all scraping sessions with metrics

## 📋 Requirements

- Python 3.9+
- BeautifulSoup4 for HTML parsing
- Requests for HTTP calls
- Playwright/Selenium for JavaScript-rendered pages
- Click for CLI
- SQLite3 (included with Python)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone git@github.com:KTA404/Fsbo-Scrapper-V2.git

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (for JS-rendered pages)
python -m playwright install
```

### 2. Initialize Project

```bash
python main.py init
```

This creates:

- `data/` - Database directory
- `exports/` - CSV export directory
- `logs/` - Log files
- `config/sites.json` - Site configuration

### 3. Run First Scrape

```bash
python main.py scrape
```

This scrapes all enabled sources and automatically saves to database.

### 4. Export Results

```bash
python main.py export -o listings.csv
```

Exports all listings to CSV in Thanks.io-compatible format.

## 💻 CLI Commands

### Scraping

**Scrape all enabled sources:**

```bash
python main.py scrape
```

**Scrape a specific site:**

```bash
python main.py scrape --site fsbo_com
```

**Scrape and specify output file:**

```bash
python main.py scrape --output exports/my_listings.csv
```

### Exporting

**Export all listings:**

```bash
python main.py export -o exports/listings.csv
```

**Export from specific source:**

```bash
python main.py export -o exports/fsbo_listings.csv --site fsbo_com
```

**Export only marked listings:**

```bash
python main.py export -o exports/ready_to_mail.csv --export-only
```

### Database Management

**List stored listings:**

```bash
python main.py list --limit 20
```

**List from specific source:**

```bash
python main.py list --site craigslist_housing --limit 10
```

**Show statistics:**

```bash
python main.py stats
```

**Clear all data:**

```bash
python main.py clear -y
```

### Configuration

**View current configuration:**

```bash
python main.py config
```

## 🔧 Configuration

Edit `config/sites.json` to customize scraping behavior:

```json
{
  "sites": [
    {
      "name": "FSBO.com",
      "scraper": "fsbo_com",
      "enabled": true,
      "min_delay": 3.0,
      "max_delay": 8.0
    }
  ],
  "scraping": {
    "min_request_delay": 1.0,
    "max_request_delay": 5.0,
    "request_timeout": 10,
    "max_retries": 3,
    "respect_robots_txt": true
  }
}
```

### Environment Variables

```bash
# Database location
export DATABASE_PATH=data/fsbo_listings.db

# Export directory
export EXPORT_DIR=exports

# Logging
export LOG_LEVEL=INFO
export LOG_FILE=logs/scraper.log

# Scraping behavior
export MIN_REQUEST_DELAY=1.0
export MAX_REQUEST_DELAY=5.0
export MAX_RETRIES=3

# Thanks.io integration
export THANKS_IO_API_KEY=your_api_key
export THANKS_IO_CAMPAIGN_ID=your_campaign_id
```

## 📁 Project Structure

```
Fsbo-Scrapper-V2/
├── config/              # Configuration files
│   ├── settings.py      # Application settings
│   ├── __init__.py      # Config loader
│   └── sites.json       # Site configuration
├── scrapers/            # Scraper implementations
│   ├── base_scraper.py  # Base scraper class
│   ├── fsbo_com.py      # FSBO.com scraper
│   ├── zillow_fsbo.py   # Zillow FSBO scraper
│   └── craigslist_housing.py
├── storage/             # Data storage
│   ├── database.py      # SQLite database
│   └── __init__.py
├── utils/               # Utility modules
│   ├── address_normalizer.py   # Address formatting
│   ├── rate_limiter.py         # Rate limiting & retries
│   ├── user_agents.py          # User-Agent rotation
│   ├── logger.py               # Logging setup
│   └── __init__.py
├── data/                # Database files (auto-created)
├── exports/             # CSV exports (auto-created)
├── logs/                # Log files (auto-created)
├── main.py              # CLI entry point
├── requirements.txt     # Python dependencies
├── setup.py             # Package configuration
└── README.md            # This file
```

## 🎓 How to Add New FSBO Sites

### 1. Create a New Scraper

Create `scrapers/my_site.py`:

```python
from .base_scraper import BaseScraper
from typing import List, Dict
from bs4 import BeautifulSoup

class MySiteScraper(BaseScraper):
    def __init__(self):
        super().__init__(
            source_name='My FSBO Site',
            base_url='https://mysite.com',
            min_delay=2.0,
            max_delay=5.0
        )

    def get_listing_urls(self) -> List[str]:
        """Return list of URLs to scrape."""
        return [
            'https://mysite.com/listings/page/1',
            'https://mysite.com/listings/page/2',
        ]

    def parse_listings(self, content: str) -> List[Dict]:
        """Parse HTML and extract listings."""
        listings = []
        soup = BeautifulSoup(content, 'html.parser')

        # Find listing elements
        for item in soup.find_all('div', class_='listing'):
            try:
                street = item.find('span', class_='street').text
                city = item.find('span', class_='city').text
                state = item.find('span', class_='state').text
                zip_code = item.find('span', class_='zip').text
                url = item.find('a')['href']

                listings.append({
                    'street': street,
                    'city': city,
                    'state': state,
                    'zip_code': zip_code,
                    'listing_url': url
                })
            except Exception as e:
                logger.debug(f"Error parsing listing: {e}")

        return listings
```

### 2. Register in Configuration

Add to `config/sites.json`:

```json
{
  "name": "My FSBO Site",
  "scraper": "my_site",
  "enabled": true,
  "min_delay": 2.0,
  "max_delay": 5.0
}
```

### 3. Register in Main CLI

Add to `main.py` in the `ScraperContext.__init__` method:

```python
from scrapers.my_site import MySiteScraper

self.scrapers = {
    'fsbo_com': FSBOComScraper,
    'zillow_fsbo': ZillowFSBOScraper,
    'craigslist_housing': CraigslistHousingScraper,
    'my_site': MySiteScraper,  # Add this
}
```

### 4. Run Scraper

```bash
python main.py scrape --site my_site
```

## 📊 CSV Export Format (Thanks.io Compatible)

The exported CSV includes:

| Field          | Description                    |
| -------------- | ------------------------------ |
| id             | Unique listing ID              |
| street         | Street address                 |
| city           | City name                      |
| state          | State abbreviation (2 letters) |
| zip_code       | ZIP code (5 or 9 digits)       |
| listing_url    | Link to original listing       |
| source_website | Where listing was scraped from |
| scraped_at     | Date/time of scrape            |

**Example CSV:**

```csv
id,street,city,state,zip_code,listing_url,source_website,scraped_at
1,123 Main St,Springfield,IL,62701,https://fsbo.com/123-main,FSBO.com,2025-02-06 10:30:00
2,456 Oak Ave,Chicago,IL,60601,https://zillow.com/456-oak,Zillow FSBO,2025-02-06 10:35:00
```

## ⚠️ Legal & Ethical Guidelines

**Always respect website terms of service:**

- ✅ Check `robots.txt` before scraping
- ✅ Respect rate limits and delays
- ✅ Identify yourself with appropriate User-Agent
- ✅ Don't scrape login-protected content
- ✅ Don't bypass CAPTCHAs or paywalls
- ❌ Don't scrape MLS-only or broker-restricted content

## 🔐 Thanks.io Integration

To enable Thanks.io postcard campaign integration:

1. **Set up API credentials:**

   ```bash
   export THANKS_IO_API_KEY=your_api_key
   export THANKS_IO_CAMPAIGN_ID=your_campaign_id
   ```

2. **Enable in config:**

   ```json
   {
     "thanks_io": {
       "enabled": true,
       "api_key": "YOUR_KEY",
       "campaign_id": "YOUR_CAMPAIGN_ID"
     }
   }
   ```

3. **Export CSV and import to Thanks.io**:
   - Log in to Thanks.io
   - Create new campaign
   - Upload CSV file
   - Map fields as needed

## 🐛 Debugging

**Enable debug logging:**

```bash
export LOG_LEVEL=DEBUG
python main.py scrape
```

**Check log files:**

```bash
tail -f logs/scraper.log
```

**View database contents:**

```bash
sqlite3 data/fsbo_listings.db
sqlite> SELECT * FROM listings LIMIT 5;
```

## 🚀 Performance Tips

1. **Increase delays for large scrapes:**

   ```bash
   export MIN_REQUEST_DELAY=5.0
   export MAX_REQUEST_DELAY=15.0
   ```

2. **Run scrapes during off-hours:**

   ```bash
   # Schedule with cron
   0 2 * * * cd /path/to/Fsbo-Scrapper-V2 && python main.py scrape
   ```

3. **Export in batches:**
   ```bash
   python main.py export -o batch1.csv --site fsbo_com
   python main.py export -o batch2.csv --site zillow_fsbo
   ```

## 📝 Examples

### Example 1: Full Workflow

```bash
# Initialize
python main.py init

# Scrape all sources
python main.py scrape

# Check statistics
python main.py stats

# Export for Thanks.io
python main.py export -o fsbo_listings_$(date +%Y%m%d).csv

# Upload to Thanks.io
# (Manual step in Thanks.io UI)
```

### Example 2: Scrape Only Craigslist

```bash
python main.py scrape --site craigslist_housing
python main.py list --site craigslist_housing --limit 20
```

### Example 3: Automated Daily Scrape

```bash
# Add to crontab
crontab -e

# Add line:
0 3 * * * cd /home/kait/Fsbo-Scrapper-V2 && python main.py scrape >> logs/cron.log 2>&1
```

## 🤝 Extending for Other Marketing Channels

The modular design makes it easy to extend for:

- **Email Marketing**: Add email list export
- **SMS Marketing**: Extract phone numbers for SMS campaigns
- **Direct Mail**: Format for postcard printing services
- **Lead Management**: Integration with CRM systems

## 📞 Support & Troubleshooting

**Common Issues:**

1. **"ModuleNotFoundError"** - Run `pip install -r requirements.txt`
2. **"Database locked"** - Close other database connections
3. **"No listings found"** - Check if sites are enabled in `config/sites.json`
4. **Playwright errors** - Run `python -m playwright install`

## 📄 License

MIT License - Feel free to use and modify for your needs.

## 📚 Additional Resources

- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Playwright Documentation](https://playwright.dev/python/)
- [Click Documentation](https://click.palletsprojects.com/)
- [Thanks.io API Documentation](https://www.thanks.io/api)
- [SQLite Documentation](https://www.sqlite.org/docs.html)

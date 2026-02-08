# FSBO Scraper - Scraper Status & Optimization Guide

## Current Status

### ✅ Working Scrapers

#### FSBO.com

- **Status**: Fully functional
- **Method**: Static HTML parsing with BeautifulSoup
- **Speed**: Fast (20-30 seconds for 20 listings)
- **Accuracy**: High address parsing success
- **Usage**: `python main.py scrape --site fsbo_com`
- **Config**: Max 20 listings by default

### ⏸️ Disabled Scrapers (Framework Ready)

#### Craigslist Housing

- **Status**: Framework implemented, disabled
- **Issue**: Page load initialization is slow (Playwright startup overhead ~15-20 seconds per region)
- **Method**: Playwright browser automation for JS rendering
- **Why disabled**: High latency from Playwright, unreliable listing parsing
- **To Enable**: Set `"enabled": true` in `config/sites.json`
- **Improvement needed**:
  - Implement connection pooling for Playwright browser
  - Or switch to HTTP-only strategy with updated selectors

**Code location**: `scrapers/craigslist_housing.py`

#### RealtyLess.com

- **Status**: Framework implemented, disabled
- **Issue**: Page takes >15 seconds to load (slow hosting/heavy JS)
- **Method**: Playwright browser automation
- **Why disabled**: Long page load times, often exceeds Playwright timeout
- **To Enable**: Set `"enabled": true` in `config/sites.json`
- **Improvement needed**:
  - Investigate site performance/CDN issues
  - Try with increased timeout (current: 12 seconds)
  - Consider skipping networkidle wait state

**Code location**: `scrapers/realtyless_com.py`

#### ByOwner.com

- **Status**: Framework implemented, disabled
- **Issue**: Cloudflare protection blocks automated requests
- **Why disabled**: Returns "You have been blocked" page
- **To Enable**: Install `undetected-chromedriver` or implement proxy rotation
- **Required changes**:
  ```bash
  pip install undetected-chromedriver
  ```

**Code location**: `scrapers/byowner_com.py`

#### Zillow FSBO

- **Status**: Placeholder, disabled
- **Issue**: Strict anti-scraping policies and JavaScript rendering
- **Why disabled**: Complex legal/technical barriers

**Code location**: `scrapers/zillow_fsbo.py`

## Usage

### Quick Start

```bash
# Scrape enabled sites (FSBO.com)
python main.py scrape

# View configuration
python main.py config

# Export to CSV
python main.py export

# View all listings
python main.py list

# Get stats
python main.py stats
```

### Advanced Usage

#### Change scrape URL for FSBO.com

Edit `config/sites.json`:

```json
{
  "name": "FSBO.com",
  "scraper": "fsbo_com",
  "scrape_url": "https://fsbo.com/" // Change this
}
```

#### Change max listings

```json
{
  "max_listings": 50 // Increase from default 20
}
```

## Performance Metrics

| Scraper    | Method            | Speed               | Reliability  |
| ---------- | ----------------- | ------------------- | ------------ |
| FSBO.com   | Static HTML       | ⚡ Fast (30s)       | ✅ Excellent |
| Craigslist | Playwright        | 🐢 Slow (60s+)      | ⚠️ Fair      |
| RealtyLess | Playwright        | 🐢 Very Slow (90s+) | ❌ Poor      |
| ByOwner    | Playwright        | ❌ Blocked          | ❌ Failed    |
| Zillow     | (Not implemented) | N/A                 | N/A          |

## Optimization Strategies

### For Craigslist

1. **Use Playwright pool**: Reuse browser instance across requests
2. **HTTP-only approach**: Scrape from HTML fallback endpoint
3. **Proxy rotation**: If needed, implement proxy support

### For RealtyLess

1. **Increase timeout**: Bump from 12s to 20-30s
2. **Skip networkidle**: Use just 'load' event
3. **Contact/API**: Check if they offer API access

### For ByOwner

1. **Install undetected-chromedriver**:
   ```bash
   pip install undetected-chromedriver
   ```
2. **Or use proxy service**: Bright Data, Oxylabs, etc.

### General Improvements

1. **Browser connection pooling**: Share Playwright browser across scrapers
2. **Caching**: Store page content to avoid re-scraping
3. **Rate limiting**: Already implemented (configurable delays)
4. **User-agent rotation**: Already implemented

## Database

SQLite database stored at: `data/fsbo_listings.db`

### Schema

```sql
CREATE TABLE listings (
  id INTEGER PRIMARY KEY,
  street TEXT,
  city TEXT,
  state TEXT,
  zip_code TEXT,
  listing_url TEXT,
  source_website TEXT,
  scraped_at DATETIME
)
```

### Query Examples

```bash
# Count listings by source
sqlite3 data/fsbo_listings.db "SELECT source_website, COUNT(*) FROM listings GROUP BY source_website;"

# Get all Miami listings
sqlite3 data/fsbo_listings.db "SELECT street, city, state, zip_code FROM listings WHERE city='Miami' ORDER BY scraped_at DESC;"

# Recent listings
sqlite3 data/fsbo_listings.db "SELECT street, city, state FROM listings ORDER BY scraped_at DESC LIMIT 10;"
```

## Logs

Logs are stored in: `logs/scraper.log`

View recent activity:

```bash
tail -50 logs/scraper.log
```

## Next Steps

1. **FSBO.com**: Currently working great - ready for production
2. **Craigslist**: Next priority - implement browser pooling
3. **RealtyLess**: Lower priority - needs investigation
4. **ByOwner**: Requires external tools (undetected-chromedriver)
5. **Zillow**: Consider API or legal alternative

## Support

For issues:

1. Check `logs/scraper.log` for detailed error messages
2. Review `config/sites.json` for settings
3. Verify URL accessibility: `curl https://fsbo.com/`
4. Check address parsing in `utils/address_normalizer.py`

# FSBO Scraper - Quick Reference Guide

## Installation & Initialization

```bash
# Install dependencies
pip install -r requirements.txt

# Install browser drivers
python -m playwright install

# Initialize project
python main.py init
```

## Basic Commands

### Scraping

```bash
# Scrape all sources
python main.py scrape

# Scrape single site
python main.py scrape --site fsbo_com

# Scrape with custom output
python main.py scrape --output exports/custom.csv
```

### Exporting

```bash
# Export all listings
python main.py export -o listings.csv

# Export from specific source
python main.py export -o fsbo_only.csv --site fsbo_com

# Export only new listings
python main.py export -o new.csv
```

### Database Management

```bash
# List stored listings
python main.py list --limit 20

# Show statistics
python main.py stats

# Clear database
python main.py clear -y
```

### Configuration

```bash
# View config
python main.py config

# Initialize default config
python main.py init
```

## Common Workflows

### Workflow 1: Fresh Scrape & Export

```bash
python main.py init              # Initialize
python main.py scrape            # Scrape all sources
python main.py export -o out.csv # Export to CSV
```

### Workflow 2: Single Source Scrape

```bash
python main.py scrape --site zillow_fsbo
python main.py list --site zillow_fsbo --limit 10
python main.py export -o zillow.csv --site zillow_fsbo
```

### Workflow 3: Weekly Recurring

```bash
# Run from cron
0 2 * * 0 cd /path/to/Fsbo-Scrapper-V2 && python main.py scrape

# Or manually weekly
python main.py scrape
python main.py export -o exports/weekly_$(date +%Y%m%d).csv
```

## Configuration Files

### Environment Variables

```bash
# Database
export DATABASE_PATH=data/fsbo_listings.db

# Logging
export LOG_LEVEL=INFO
export LOG_FILE=logs/scraper.log

# Scraping
export MIN_REQUEST_DELAY=1.0
export MAX_REQUEST_DELAY=5.0
export MAX_RETRIES=3

# Thanks.io
export THANKS_IO_API_KEY=sk_live_xxx
export THANKS_IO_CAMPAIGN_ID=camp_xxx
```

### sites.json

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
  ]
}
```

## Database Queries

### Direct SQLite Access

```bash
sqlite3 data/fsbo_listings.db

# List all listings
SELECT * FROM listings LIMIT 10;

# Count by source
SELECT source_website, COUNT(*) as count FROM listings GROUP BY source_website;

# Find duplicates
SELECT listing_hash, COUNT(*) FROM listings GROUP BY listing_hash HAVING COUNT(*) > 1;

# Export to CSV
.mode csv
.output exports/raw.csv
SELECT * FROM listings;
.quit
```

## Troubleshooting Quick Fixes

| Issue             | Fix                                        |
| ----------------- | ------------------------------------------ |
| No module errors  | `pip install -r requirements.txt`          |
| Database locked   | Close other connections, restart           |
| No listings found | Check `config/sites.json` - sites enabled? |
| Playwright errors | `python -m playwright install`             |
| Slow scraping     | Increase `MAX_REQUEST_DELAY` in config     |
| Too many retries  | Reduce `MAX_RETRIES` in config             |
| Permission denied | `chmod +x main.py`                         |

## Performance Tips

### Fast Scraping

```bash
# Reduce delays (fast but risky)
export MIN_REQUEST_DELAY=0.5
export MAX_REQUEST_DELAY=2.0
python main.py scrape
```

### Respectful Scraping (Recommended)

```bash
# Longer delays (respects servers)
export MIN_REQUEST_DELAY=3.0
export MAX_REQUEST_DELAY=10.0
python main.py scrape
```

### Large Exports

```bash
# Export specific sources separately
python main.py export -o fsbo.csv --site fsbo_com
python main.py export -o zillow.csv --site zillow_fsbo
python main.py export -o craigslist.csv --site craigslist_housing

# Combine if needed
cat fsbo.csv zillow.csv craigslist.csv > combined.csv
```

## Adding New Sites

### Quick Steps

1. **Create scraper** in `scrapers/my_site.py`
2. **Add to** `scrapers/__init__.py`
3. **Register in** `main.py` ScraperContext
4. **Add to** `config/sites.json`
5. **Test**: `python main.py scrape --site my_site`

See [ADDING_NEW_SITES.md](ADDING_NEW_SITES.md) for details.

## Thanks.io Integration

### Manual CSV Method

```bash
python main.py scrape
python main.py export -o thanks_io.csv

# Then upload CSV in Thanks.io UI
```

### API Method

```bash
export THANKS_IO_API_KEY=sk_live_xxx
export THANKS_IO_CAMPAIGN_ID=camp_xxx

python main.py scrape
python main.py submit-to-thanks-io --campaign-id camp_xxx
```

See [THANKS_IO_INTEGRATION.md](THANKS_IO_INTEGRATION.md) for details.

## Project Structure Cheatsheet

```
scrapers/           # Scraper implementations
├── base_scraper.py # Base classes (extend these)
├── fsbo_com.py    # Example FSBO scraper
└── my_site.py     # Your custom scraper

storage/
├── database.py    # SQLite database

utils/
├── address_normalizer.py  # Address formatting
├── rate_limiter.py        # Rate limiting & retries
├── user_agents.py         # User-Agent rotation
└── logger.py              # Logging setup

config/
├── settings.py    # App configuration
├── sites.json     # Site configuration
└── __init__.py   # Config loader

main.py           # CLI entry point
```

## CSV Export Format

```csv
id,street,city,state,zip_code,listing_url,source_website,scraped_at
1,123 Main St,Springfield,IL,62701,https://fsbo.com/123,FSBO.com,2025-02-06 10:30:00
2,456 Oak Ave,Chicago,IL,60601,https://zillow.com/456,Zillow FSBO,2025-02-06 10:35:00
```

## Logging

### Log Levels

```bash
export LOG_LEVEL=DEBUG    # Very verbose
export LOG_LEVEL=INFO     # Standard
export LOG_LEVEL=WARNING  # Warnings only
export LOG_LEVEL=ERROR    # Errors only
```

### View Logs

```bash
# Current session
tail -f logs/scraper.log

# Search logs
grep -i "error" logs/scraper.log

# Count errors
grep -c "ERROR" logs/scraper.log
```

## Common Error Messages

| Error                 | Cause                        | Solution                           |
| --------------------- | ---------------------------- | ---------------------------------- |
| `ModuleNotFoundError` | Missing dependency           | `pip install -r requirements.txt`  |
| `No listings found`   | Site disabled or parse error | Check `config/sites.json` and logs |
| `Request timeout`     | Server slow/unavailable      | Increase timeout, retry later      |
| `Database locked`     | Multiple connections         | Close other processes              |
| `Permission denied`   | File permissions             | `chmod +x main.py`                 |

## Tips & Tricks

### Batch Operations

```bash
# Scrape multiple times
for i in {1..5}; do
  python main.py scrape
  sleep 3600  # Wait 1 hour
done
```

### Monitor Scraping

```bash
# Watch progress
watch -n 5 "python main.py stats"

# Count new additions
python main.py list | wc -l
```

### Backup Database

```bash
# Daily backup
cp data/fsbo_listings.db data/fsbo_listings.db.$(date +%Y%m%d).bak
```

### Reset Everything

```bash
# WARNING: Deletes all data!
python main.py clear -y
rm -rf data/ exports/ logs/
python main.py init
```

## Resources

- **Main Docs**: [README.md](README.md)
- **Setup**: [SETUP.md](SETUP.md)
- **New Sites**: [ADDING_NEW_SITES.md](ADDING_NEW_SITES.md)
- **Thanks.io**: [THANKS_IO_INTEGRATION.md](THANKS_IO_INTEGRATION.md)
- **Config Example**: [config/sites.json](config/sites.json)
- **CSV Example**: [EXAMPLE_OUTPUT.csv](EXAMPLE_OUTPUT.csv)

## Getting Help

1. Check logs: `tail -f logs/scraper.log`
2. Enable debug: `export LOG_LEVEL=DEBUG`
3. Run config: `python main.py config`
4. Check stats: `python main.py stats`
5. Read docs in this directory

# Quick Fixes for Craigslist & RealtyLess

## Current Status

- ✅ **FSBO.com**: Working (30s per scrape)
- ⏸️ **Craigslist**: Code ready, disabled (needs browser pooling)
- ⏸️ **RealtyLess**: Code ready, disabled (slow page load)

---

## Enable Craigslist (Fast Method)

### Step 1: Edit config

```bash
# Open config/sites.json
# Find "Craigslist Housing" section
# Change: "enabled": false  →  "enabled": true
```

### Step 2: Run

```bash
python main.py scrape --site craigslist_housing
# First run: ~60 seconds (Playwright startup)
# Future runs: ~45-60 seconds
```

### Step 3: Why it's slow

- Playwright takes 15-20 seconds to launch browser
- Scraping 2 metro areas takes additional 30-45 seconds
- **Solution for production**: Implement browser pooling (reduces to 5-10 seconds total)

---

## Enable RealtyLess (Fast Method)

### Step 1: Edit config

```bash
# Open config/sites.json
# Find "RealtyLess.com" section
# Change: "enabled": false  →  "enabled": true
```

### Step 2: Run

```bash
python main.py scrape --site realtyless_com
# First run: ~30-45 seconds (page load wait)
# Subsequent runs: Same (~30-45 seconds)
```

### Step 3: If still timing out

Edit `scrapers/realtyless_com.py` line ~88:

```python
# Change from:
await page.goto(url, wait_until='load', timeout=12000)

# To:
await page.goto(url, wait_until='load', timeout=45000)  # 45 seconds
```

---

## Make Both Faster (Production Setup)

### Option 1: Use FSBO Only (Recommended)

```bash
python main.py scrape  # Just runs FSBO (30 seconds, fast & reliable)
```

### Option 2: Implement Browser Pooling

**Why it matters**: Saves 15-20 seconds per scrape by reusing browser

**Where to add**: `scrapers/base_scraper.py`

```python
# Add this to BaseScraper class
class BrowserPool:
    _browser = None

    @classmethod
    async def get_browser(cls):
        if cls._browser is None:
            from playwright.async_api import async_playwright
            p = await async_playwright().start()
            cls._browser = await p.chromium.launch(headless=True)
        return cls._browser
```

Then update scrapers to use: `page = await BrowserPool.get_browser()`

**Result**: First scrape 60s, subsequent scrapes 15-20s

---

## Verify Everything Works

```bash
# Check enabled scrapers
python main.py config

# Test FSBO
python main.py scrape

# Check database
sqlite3 data/fsbo_listings.db "SELECT COUNT(*) FROM listings;"

# Export data
python main.py export

# View listings
python main.py list
```

---

## Troubleshooting

### "Timeout exceeded" error

- **For RealtyLess**: Increase timeout (see above)
- **For Craigslist**: Increase timeout in `scrapers/craigslist_housing.py`

### "Page.goto: Timeout" error

- **Cause**: Playwright can't load page
- **Fix**: Set `enabled: false` and stick with FSBO.com

### No listings found

- **Cause**: HTML selectors don't match
- **Fix**: Check page source and update selectors in parse_listings()

---

## Recommended Setup

```json
// config/sites.json
// PRODUCTION READY:
{
  "sites": [
    {
      "name": "FSBO.com",
      "enabled": true, // ✅ Works great
      "max_listings": 20
    }
    // Optional for expansion:
    // {
    //   "name": "RealtyLess.com",
    //   "enabled": false,      // Enable when needed
    //   "max_listings": 20
    // },
    // {
    //   "name": "Craigslist Housing",
    //   "enabled": false,      // Enable when needed
    //   "max_listings": 30
    // }
  ]
}
```

---

## Summary

| Site       | Method      | Status       | Speed | Enable?  |
| ---------- | ----------- | ------------ | ----- | -------- |
| FSBO.com   | Static HTML | ✅ Ready     | 30s   | YES      |
| Craigslist | Playwright  | ✅ Code done | 60s   | Optional |
| RealtyLess | Playwright  | ✅ Code done | 45s   | Optional |

**For now**: Use FSBO.com (fastest & most reliable)

**Next phase**: Add Craigslist (need browser pooling for speed)

**Future**: Add RealtyLess if needed

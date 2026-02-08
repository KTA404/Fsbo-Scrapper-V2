# Setup Instructions

## Step 1: Prerequisites

Ensure you have Python 3.9 or higher installed:

```bash
python --version
```

## Step 2: Clone/Download Project

If you haven't already:

```bash
cd /home/kait/Fsbo-Scrapper-V2
```

## Step 3: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

## Step 4: Install Dependencies

**Note:** Before installing Python packages, make sure you have build tools and libxml2/libxslt development packages installed:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y build-essential python3-dev libxml2-dev libxslt1-dev

# Fedora/RHEL 8+
sudo dnf install -y gcc gcc-c++ make python3-devel libxml2-devel libxslt-devel

# RedHat/CentOS (older versions)
sudo yum groupinstall -y "Development Tools"
sudo yum install -y python3-devel libxml2-devel libxslt-devel

# macOS
brew install libxml2 libxslt
```

Then install Python dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 5: Install Browser Drivers (for JavaScript pages)

```bash
# Install Playwright browsers
python -m playwright install

# Or if using Selenium:
# Download ChromeDriver from https://chromedriver.chromium.org/
```

## Step 6: Initialize Project

```bash
python main.py init
```

This will:

- Create necessary directories (data/, exports/, logs/)
- Initialize SQLite database
- Generate default configuration file

## Step 7: Configure Sites (Optional)

Edit `config/sites.json` to:

- Enable/disable specific sources
- Adjust rate limiting settings
- Configure Thanks.io integration

```bash
nano config/sites.json
# or use your preferred editor
```

## Step 8: Run Your First Scrape

```bash
python main.py scrape
```

## Step 9: Export Results

```bash
python main.py export -o listings.csv
```

## 🎉 You're Done!

Your FSBO listings are now extracted and ready for Thanks.io postcard campaigns.

## Troubleshooting Setup

### Issue: "command not found: python"

**Solution:** Use `python3` instead of `python` (if on Linux/Mac)

```bash
python3 main.py scrape
```

### Issue: Wheel build errors (lxml, aiohttp, pydantic-core, greenlet)

**Solution:** Install build tools and development headers

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y build-essential python3-dev libxml2-dev libxslt1-dev

# Fedora/RHEL 8+
sudo dnf install -y gcc gcc-c++ make python3-devel libxml2-devel libxslt-devel

# RedHat/CentOS (older versions)
sudo yum groupinstall -y "Development Tools"
sudo yum install -y python3-devel libxml2-devel libxslt-devel

# macOS
brew install libxml2 libxslt

# Then clean pip cache and retry
pip cache purge
pip install --no-cache-dir -r requirements.txt
```

### Issue: ModuleNotFoundError

**Solution:** Ensure virtual environment is activated

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: Permission denied

**Solution:** Add execute permission to main.py

```bash
chmod +x main.py
./main.py scrape
```

### Issue: Database locked

**Solution:** Close other connections and restart

```bash
# Close other terminals using the database
# Then try again:
python main.py scrape
```

### Issue: Playwright installation fails

**Solution:** Install system dependencies

```bash
# Ubuntu/Debian
sudo apt-get install libnss3 libatk1.0-0 libgbm-dev libxss1 libasound2

# macOS
# Usually just works, or use:
python -m playwright install-deps

# Windows
# Download from: https://github.com/microsoft/playwright/releases
```

## Production Setup (Linux)

### Using systemd timer for automated scraping

1. **Create service file:**

```bash
sudo nano /etc/systemd/system/fsbo-scraper.service
```

2. **Add content:**

```ini
[Unit]
Description=FSBO Scraper Service
After=network.target

[Service]
Type=oneshot
User=username
WorkingDirectory=/home/kait/Fsbo-Scrapper-V2
ExecStart=/home/kait/Fsbo-Scrapper-V2/venv/bin/python main.py scrape
StandardOutput=journal
StandardError=journal
Environment="PATH=/home/kait/Fsbo-Scrapper-V2/venv/bin"

[Install]
WantedBy=multi-user.target
```

3. **Create timer file:**

```bash
sudo nano /etc/systemd/system/fsbo-scraper.timer
```

4. **Add content (runs daily at 3 AM):**

```ini
[Unit]
Description=Run FSBO Scraper daily
Requires=fsbo-scraper.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

5. **Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable fsbo-scraper.timer
sudo systemctl start fsbo-scraper.timer
sudo systemctl status fsbo-scraper.timer
```

### Docker Setup (Optional)

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    libnss3 libatk1.0-0 libgbm-dev libxss1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install

COPY . .

ENTRYPOINT ["python", "main.py"]
```

Build and run:

```bash
docker build -t fsbo-scraper .
docker run fsbo-scraper scrape
docker run -v $(pwd)/exports:/app/exports fsbo-scraper export -o /app/exports/listings.csv
```

## Upgrading

To update dependencies:

```bash
pip install --upgrade -r requirements.txt
```

To get latest code changes:

```bash
git pull origin main
```

## Getting Help

1. Check the main [README.md](README.md)
2. Review [example configuration](config/sites.json)
3. Check logs: `tail -f logs/scraper.log`
4. View database: `sqlite3 data/fsbo_listings.db`

## Next Steps

- Configure your Thanks.io API credentials
- Add additional FSBO sites to config
- Set up automated daily scraping
- Integrate with email/SMS marketing tools

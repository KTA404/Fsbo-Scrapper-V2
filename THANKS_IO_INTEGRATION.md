# Thanks.io Integration Guide

This guide explains how to integrate the FSBO Scraper with Thanks.io for postcard marketing campaigns.

## Overview

Thanks.io is a platform for sending personalized postcards and letters at scale. The FSBO Scraper exports CSV files that are compatible with Thanks.io's address import format.

## Prerequisites

1. **Thanks.io Account**: Sign up at https://www.thanks.io
2. **API Credentials**: Generate API key in Thanks.io settings
3. **Campaign ID**: Create a campaign in Thanks.io dashboard

## Setup

### 1. Get API Credentials

1. Log in to Thanks.io dashboard
2. Go to: **Settings** → **API Keys**
3. Create a new API key and note it
4. Create a new postcard campaign and note the Campaign ID

### 2. Configure FSBO Scraper

Set environment variables:

```bash
export THANKS_IO_API_KEY="sk_live_xxxxxxxxxxxx"
export THANKS_IO_CAMPAIGN_ID="camp_xxxxxxxxxxxx"
```

Or edit `config/sites.json`:

```json
{
  "thanks_io": {
    "enabled": true,
    "api_key": "sk_live_xxxxxxxxxxxx",
    "campaign_id": "camp_xxxxxxxxxxxx"
  }
}
```

### 3. Export Data

```bash
python main.py export -o thanks_io_import.csv
```

## CSV Format

The exported CSV matches Thanks.io's required format:

| Field       | Required | Example                      |
| ----------- | -------- | ---------------------------- |
| street      | Yes      | 123 Main Street              |
| city        | Yes      | Springfield                  |
| state       | Yes      | IL                           |
| zip_code    | Yes      | 62701                        |
| listing_url | No       | https://fsbo.com/listing/123 |

### Full Example

```csv
street,city,state,zip_code,listing_url,source_website,scraped_at
123 Main St,Springfield,IL,62701,https://fsbo.com/123,FSBO.com,2025-02-06 10:30:00
456 Oak Ave,Chicago,IL,60601,https://zillow.com/456,Zillow FSBO,2025-02-06 10:35:00
```

## Manual Import to Thanks.io

### Step 1: Prepare CSV

```bash
python main.py scrape
python main.py export -o addresses.csv
```

### Step 2: Upload to Thanks.io

1. Log in to Thanks.io
2. Navigate to your campaign
3. Click **"Add Addresses"** or **"Import CSV"**
4. Select your CSV file
5. Map the columns:
   - **street** → Street Address
   - **city** → City
   - **state** → State
   - **zip_code** → ZIP Code
6. Review addresses for accuracy
7. Click **"Import"**

### Step 3: Design Postcard

1. Upload or design your postcard template
2. Add personalization fields if needed
3. Set up mail distribution

### Step 4: Send Campaign

1. Review addresses and design
2. Click **"Approve & Send"**
3. Monitor campaign progress

## Automated Integration (API)

### Using Thanks.io API Directly

Create `integrations/thanks_io.py`:

```python
"""
Thanks.io API integration for postcard campaigns.
"""

import requests
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class ThanksIOClient:
    """Client for Thanks.io API."""

    BASE_URL = "https://api.thanks.io/v1"

    def __init__(self, api_key: str):
        """Initialize Thanks.io client."""
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def get_campaigns(self) -> List[Dict]:
        """Get list of campaigns."""
        response = requests.get(
            f"{self.BASE_URL}/campaigns",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()['campaigns']

    def create_batch(self, campaign_id: str, addresses: List[Dict]) -> str:
        """
        Create a batch of addresses for a campaign.

        Args:
            campaign_id: Thanks.io campaign ID
            addresses: List of address dictionaries

        Returns:
            Batch ID
        """
        payload = {
            'campaign_id': campaign_id,
            'addresses': addresses
        }

        response = requests.post(
            f"{self.BASE_URL}/batches",
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()['batch_id']

    def submit_batch(self, batch_id: str) -> Dict:
        """Submit batch for processing."""
        response = requests.post(
            f"{self.BASE_URL}/batches/{batch_id}/submit",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def get_batch_status(self, batch_id: str) -> Dict:
        """Get batch status."""
        response = requests.get(
            f"{self.BASE_URL}/batches/{batch_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def upload_addresses(self, campaign_id: str, addresses: List[Dict]) -> str:
        """
        Upload addresses to campaign and submit for processing.

        Args:
            campaign_id: Thanks.io campaign ID
            addresses: List of address dictionaries

        Returns:
            Batch ID
        """
        try:
            # Create batch
            batch_id = self.create_batch(campaign_id, addresses)
            logger.info(f"Created batch: {batch_id}")

            # Submit batch
            self.submit_batch(batch_id)
            logger.info(f"Submitted batch: {batch_id}")

            return batch_id

        except requests.RequestException as e:
            logger.error(f"Thanks.io API error: {e}")
            raise


def addresses_to_thanks_io_format(addresses: List[Dict]) -> List[Dict]:
    """Convert FSBO scraper format to Thanks.io format."""
    result = []

    for addr in addresses:
        thanks_io_addr = {
            'street': addr['street'],
            'city': addr['city'],
            'state': addr['state'],
            'zip': addr['zip_code'],
            'country': 'US'
        }

        # Optional fields
        if addr.get('listing_url'):
            thanks_io_addr['note'] = f"Listing: {addr['listing_url']}"

        result.append(thanks_io_addr)

    return result
```

### Using the API Client

```python
from integrations.thanks_io import ThanksIOClient, addresses_to_thanks_io_format
from storage import FSBODatabase

# Load listings from database
db = FSBODatabase()
listings = db.get_listings()

# Convert to Thanks.io format
addresses = addresses_to_thanks_io_format(listings)

# Upload to campaign
client = ThanksIOClient(api_key='sk_live_xxx')
batch_id = client.upload_addresses(
    campaign_id='camp_xxx',
    addresses=addresses
)

print(f"Uploaded batch: {batch_id}")
```

## CLI Command for Thanks.io Integration

Add to `main.py`:

```python
@cli.command()
@click.option('--campaign-id', required=True, help='Thanks.io campaign ID')
@click.option('--limit', type=int, default=None, help='Limit number of addresses')
@click.pass_context
def submit_to_thanks_io(ctx, campaign_id: str, limit: Optional[int]):
    """Submit listings directly to Thanks.io campaign."""
    context = ctx.obj['context']

    try:
        from integrations.thanks_io import (
            ThanksIOClient,
            addresses_to_thanks_io_format
        )

        api_key = os.environ.get('THANKS_IO_API_KEY')
        if not api_key:
            click.echo(click.style(
                "❌ THANKS_IO_API_KEY not set",
                fg='red'
            ))
            return

        # Load listings
        listings = context.db.get_listings(limit=limit)
        if not listings:
            click.echo("No listings to submit.")
            return

        # Convert format
        addresses = addresses_to_thanks_io_format(listings)

        # Upload to Thanks.io
        click.echo(click.style(
            f"📤 Uploading {len(addresses)} addresses to Thanks.io...",
            fg='cyan'
        ))

        client = ThanksIOClient(api_key=api_key)
        batch_id = client.upload_addresses(
            campaign_id=campaign_id,
            addresses=addresses
        )

        click.echo(click.style(
            f"✅ Batch {batch_id} submitted!",
            fg='green'
        ))

    except Exception as e:
        click.echo(click.style(f"❌ Error: {e}", fg='red'))
        logger.error(f"Thanks.io submission error: {e}")
```

## Workflow Examples

### Example 1: Simple CSV Export

```bash
# Scrape listings
python main.py scrape

# Export to CSV
python main.py export -o fsbo_listings.csv

# Manually upload to Thanks.io UI
```

### Example 2: API Integration

```bash
# Set credentials
export THANKS_IO_API_KEY="sk_live_xxx"
export THANKS_IO_CAMPAIGN_ID="camp_xxx"

# Scrape and submit directly
python main.py scrape
python main.py submit-to-thanks-io --campaign-id camp_xxx

# View campaign status in Thanks.io dashboard
```

### Example 3: Scheduled Daily Campaign

```bash
# Create script: send_fsbo_postcards.sh
#!/bin/bash
cd /home/kait/Fsbo-Scrapper-V2

# Scrape latest listings
python main.py scrape

# Export to CSV
EXPORT_FILE="exports/fsbo_$(date +%Y%m%d).csv"
python main.py export -o "$EXPORT_FILE"

# Log success
echo "Exported to $EXPORT_FILE" >> logs/postcard_schedule.log

# Note: Still need to manually import to Thanks.io
# Or use API integration for automatic submission
```

Add to crontab:

```bash
0 6 * * * /path/to/send_fsbo_postcards.sh
```

## Address Validation

Thanks.io requires properly formatted addresses. The FSBO Scraper automatically:

1. **Normalizes street addresses**:
   - Standardizes abbreviations (St, Ave, Rd, etc.)
   - Proper capitalization

2. **Validates states**:
   - Converts to 2-letter abbreviations
   - Validates against all US states

3. **Formats ZIP codes**:
   - Standard 5-digit format
   - Optional 9-digit format (12345-6789)

4. **Removes duplicates**:
   - Uses address hashing to prevent duplication

## Troubleshooting

### Issue: "Invalid addresses rejected"

Check the addresses in exported CSV:

```bash
head -20 exports/listings.csv
```

Ensure:

- ✅ Street addresses are present
- ✅ Cities are spelled correctly
- ✅ States are 2-letter abbreviations
- ✅ ZIP codes are 5 digits

### Issue: "API authentication failed"

Verify credentials:

```bash
echo $THANKS_IO_API_KEY
echo $THANKS_IO_CAMPAIGN_ID
```

Check Thanks.io dashboard:

- Confirm API key is active
- Verify campaign ID matches

### Issue: "Campaign not found"

Confirm campaign exists:

1. Log in to Thanks.io
2. Navigate to Campaigns
3. Copy correct Campaign ID
4. Update environment variable

## Thanks.io Documentation

For more information:

- API Docs: https://developers.thanks.io/
- Dashboard: https://app.thanks.io
- Support: https://support.thanks.io

## Tips for Successful Campaigns

1. **Clean Data**: Ensure all addresses are valid
2. **Test First**: Start with small batches
3. **Personalization**: Use postcard template variables
4. **Tracking**: Use Thanks.io analytics to track responses
5. **Follow-up**: Plan follow-up campaigns based on responses

## Next Steps

1. Export first batch of FSBO listings
2. Create postcard design in Thanks.io
3. Import addresses
4. Send test campaign
5. Monitor response rates
6. Scale with automated daily scraping

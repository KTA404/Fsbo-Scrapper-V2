#!/usr/bin/env python
"""
FSBO Scraper CLI - Main entry point for the application.
Provides commands to scrape FSBO listings, export to CSV, and manage data.
"""

import click
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from utils.logger import setup_logging
from config.settings import (
    DATABASE_PATH, EXPORT_DIR, LOG_LEVEL, LOG_FILE,
    MIN_REQUEST_DELAY, MAX_REQUEST_DELAY
)
from config import SiteConfig
from storage import FSBODatabase
from scrapers import FSBOComScraper, ByOwnerComScraper, RealtyLessComScraper, BeycomeScraper, ZillowFSBOScraper, CraigslistHousingScraper, FSBOLandingPageScraper

# Setup logging
logger = setup_logging(log_level=LOG_LEVEL, log_file=LOG_FILE)


class ScraperContext:
    """Context object for CLI commands."""

    def __init__(self):
        """Initialize context."""
        self.db = FSBODatabase(db_path=DATABASE_PATH)
        self.site_config = SiteConfig()
        self.scrapers = {
            'fsbo_com': FSBOComScraper,
            'byowner_com': ByOwnerComScraper,
            'realtyless_com': RealtyLessComScraper,
            'beycome_com': BeycomeScraper,
            'zillow_fsbo': ZillowFSBOScraper,
            'craigslist_housing': CraigslistHousingScraper,
            'fsbo_landing': FSBOLandingPageScraper,
        }


@click.group()
@click.pass_context
def cli(ctx):
    """
    FSBO Scraper - A Python-based web scraping system for FSBO property listings.
    
    Extract property addresses for postcard marketing campaigns via Thanks.io.
    """
    ctx.ensure_object(dict)
    ctx.obj['context'] = ScraperContext()


@cli.command()
@click.option('--site', type=str, default=None, help='Scrape only a specific site (fsbo_com, zillow_fsbo, craigslist_housing, fsbo_landing)')
@click.option('--output', type=str, default=None, help='Output CSV file path')
@click.pass_context
def scrape(ctx, site: Optional[str], output: Optional[str]):
    """Scrape FSBO listings from configured sources."""
    context = ctx.obj['context']
    
    click.echo(click.style("🔍 FSBO Scraper Starting...", fg='cyan', bold=True))
    click.echo(f"Database: {DATABASE_PATH}\n")

    if site and site not in context.scrapers:
        click.echo(click.style(f"❌ Unknown scraper: {site}", fg='red'))
        click.echo(f"Available scrapers: {', '.join(context.scrapers.keys())}")
        return

    scrapers_to_run = [site] if site else [k for k in context.scrapers.keys()]
    total_new = 0
    total_duplicates = 0
    total_errors = 0
    all_addresses = []

    for scraper_name in scrapers_to_run:
        if not context.site_config.is_site_enabled(scraper_name):
            click.echo(click.style(f"⏭️  Skipping disabled scraper: {scraper_name}", fg='yellow'))
            continue

        site_config = context.site_config.get_site(scraper_name)
        click.echo(click.style(f"\n📍 Scraping: {site_config['name']}", fg='cyan', bold=True))

        try:
            scraper_class = context.scrapers[scraper_name]
            
            # Pass config parameters for scrapers that support them
            if scraper_name == 'fsbo_com':
                kwargs = {}
                if 'max_listings' in site_config:
                    kwargs['max_listings'] = site_config['max_listings']
                    click.echo(f"   Max listings: {site_config['max_listings']}")
                if 'scrape_url' in site_config:
                    kwargs['scrape_url'] = site_config['scrape_url']
                    click.echo(f"   Scrape URL: {site_config['scrape_url']}")
                if 'allowed_states' in site_config:
                    kwargs['allowed_states'] = site_config['allowed_states']
                    click.echo(f"   Allowed states: {site_config['allowed_states']}")
                scraper = scraper_class(**kwargs) if kwargs else scraper_class()
            elif scraper_name == 'fsbo_landing':
                kwargs = {}
                if 'max_listings' in site_config:
                    kwargs['max_listings'] = site_config['max_listings']
                    click.echo(f"   Max listings: {site_config['max_listings']}")
                if 'landing_urls' in site_config:
                    kwargs['landing_urls'] = site_config['landing_urls']
                    click.echo(f"   Landing URLs: {site_config['landing_urls']}")
                if 'landing_search_queries' in site_config:
                    kwargs['search_queries'] = site_config['landing_search_queries']
                    click.echo(f"   Search queries: {site_config['landing_search_queries']}")
                if 'max_search_results' in site_config:
                    kwargs['max_search_results'] = site_config['max_search_results']
                    click.echo(f"   Max search results: {site_config['max_search_results']}")
                if 'landing_allowlist' in site_config:
                    kwargs['allowlist_domains'] = site_config['landing_allowlist']
                    click.echo(f"   Allowlist: {site_config['landing_allowlist']}")
                if 'landing_allowed_states' in site_config:
                    kwargs['allowed_states'] = site_config['landing_allowed_states']
                    click.echo(f"   Allowed states: {site_config['landing_allowed_states']}")
                if 'landing_blacklist' in site_config:
                    kwargs['blacklist_domains'] = site_config['landing_blacklist']
                    click.echo(f"   Blacklist: {site_config['landing_blacklist']}")
                scraper = scraper_class(**kwargs) if kwargs else scraper_class()
            else:
                scraper = scraper_class()

            click.echo(f"   Rate limiting: {scraper.rate_limiter.min_delay}s - {scraper.rate_limiter.max_delay}s")

            with click.progressbar(
                length=100,
                label='   Progress',
                show_eta=True
            ) as pbar:
                listings = scraper.scrape()
                pbar.update(100)

            # Add to database
            new_count, dup_count = context.db.bulk_add_listings(listings)
            total_new += new_count
            total_duplicates += dup_count
            
            # Collect addresses
            for listing in listings:
                address = f"{listing.get('street', '')}, {listing.get('city', '')}, {listing.get('state', '')} {listing.get('zip_code', '')}"
                all_addresses.append(address)

            # Record scrape session
            context.db.record_scrape_session(
                source_website=scraper.source_name,
                listings_found=len(listings),
                listings_new=new_count,
                listings_duplicates=dup_count,
                errors=0,
                status='completed'
            )

            scraper.close()

            click.echo(click.style(f"   ✅ Complete: {new_count} new, {dup_count} duplicates", fg='green'))

        except Exception as e:
            logger.error(f"Error scraping {scraper_name}: {e}")
            total_errors += 1
            click.echo(click.style(f"   ❌ Error: {str(e)}", fg='red'))
            
            context.db.record_scrape_session(
                source_website=scraper_name,
                listings_found=0,
                listings_new=0,
                listings_duplicates=0,
                errors=1,
                error_message=str(e),
                status='failed'
            )

    # Summary
    click.echo(click.style("\n📊 Summary", fg='cyan', bold=True))
    click.echo(f"   Total new listings: {total_new}")
    click.echo(f"   Total duplicates: {total_duplicates}")
    click.echo(f"   Errors: {total_errors}")

    # Print all addresses
    if all_addresses:
        click.echo(click.style("\n📍 Scraped Addresses", fg='cyan', bold=True))
        for address in all_addresses:
            click.echo(f"   {address}")
    else:
        click.echo(click.style("\n📍 No addresses scraped", fg='yellow'))

    # Auto-export if requested
    if output or output is None:
        export_path = output or f"{EXPORT_DIR}/fsbo_listings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        click.echo(f"\n📤 Exporting to: {export_path}")
        context.db.export_to_csv(export_path)
        click.echo(click.style("✅ Export complete!", fg='green'))


@cli.command()
@click.option('--site', type=str, default=None, help='Export only listings from a specific site')
@click.option('--output', '-o', type=str, required=True, help='Output CSV file path')
@click.option('--export-only', is_flag=True, help='Only export listings marked as exported')
@click.pass_context
def export(ctx, site: Optional[str], output: str, export_only: bool):
    """Export listings to CSV format compatible with Thanks.io."""
    context = ctx.obj['context']

    click.echo(click.style("📤 Exporting listings to CSV...", fg='cyan', bold=True))

    try:
        context.db.export_to_csv(
            output_path=output,
            source=site,
            exported_only=export_only
        )

        # Read and show sample
        from pathlib import Path
        csv_file = Path(output)
        if csv_file.exists():
            with open(csv_file, 'r') as f:
                lines = f.readlines()
                
            click.echo(click.style("✅ Export successful!", fg='green'))
            click.echo(f"   File: {output}")
            click.echo(f"   Rows: {len(lines) - 1}")  # Subtract header
            
            if len(lines) <= 5:
                click.echo("\n📋 Preview:")
                click.echo(''.join(lines))
            else:
                click.echo("\n📋 Preview (first 3 rows):")
                click.echo(''.join(lines[:4]))

    except Exception as e:
        click.echo(click.style(f"❌ Export failed: {e}", fg='red'))
        logger.error(f"Export error: {e}")


@cli.command(name='listings')
@click.option('--limit', '-l', type=int, default=10, help='Number of listings to display')
@click.option('--site', '-s', type=str, default=None, help='Filter by source website')
@click.pass_context
def listings(ctx, limit: int, site: Optional[str]):
    """List stored FSBO listings."""
    context = ctx.obj['context']

    click.echo(click.style("📋 FSBO Listings", fg='cyan', bold=True))

    listings = context.db.get_listings(limit=limit, source=site)
    total = context.db.get_listing_count(source=site)

    if not listings:
        click.echo("No listings found.")
        return

    # Display listings in table format
    click.echo(f"\nShowing {len(listings)} of {total} listings:\n")
    
    for i, listing in enumerate(listings, 1):
        click.echo(f"{i}. {listing['street']}")
        click.echo(f"   {listing['city']}, {listing['state']} {listing['zip_code']}")
        click.echo(f"   Source: {listing['source_website']}")
        if listing['listing_url']:
            click.echo(f"   URL: {listing['listing_url']}")
        click.echo()


@cli.command()
@click.pass_context
def stats(ctx):
    """Display scraping statistics."""
    context = ctx.obj['context']

    click.echo(click.style("📊 Scraping Statistics", fg='cyan', bold=True))

    total = context.db.get_listing_count()
    click.echo(f"\nTotal listings: {total}")

    # Count by source
    click.echo(click.style("\nListings by source:", fg='cyan'))
    for scraper_name in context.scrapers.keys():
        site_config = context.site_config.get_site(scraper_name)
        if site_config:
            count = context.db.get_listing_count(source=scraper_name)
            status = "✅" if context.site_config.is_site_enabled(scraper_name) else "⏸️"
            click.echo(f"  {status} {site_config['name']}: {count}")

    # Recent scrape history
    click.echo(click.style("\nRecent scrape sessions:", fg='cyan'))
    history = context.db.get_scrape_history(limit=5)
    
    if not history:
        click.echo("  No scrape history found.")
    else:
        for session in history:
            click.echo(f"  • {session['source_website']}")
            click.echo(f"    Status: {session['status']} | New: {session['listings_new']} | Duplicates: {session['listings_duplicates']}")


@cli.command()
@click.option('--confirm', '-y', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def clear(ctx, confirm: bool):
    """Clear all listings from database."""
    context = ctx.obj['context']

    if not confirm:
        click.confirm(click.style("⚠️  Are you sure you want to delete all listings?", fg='yellow'), abort=True)

    try:
        context.db.clear_all_data()
        click.echo(click.style("✅ Database cleared.", fg='green'))
    except Exception as e:
        click.echo(click.style(f"❌ Error clearing database: {e}", fg='red'))


@cli.command()
@click.pass_context
def config(ctx):
    """Display current configuration."""
    context = ctx.obj['context']

    click.echo(click.style("⚙️  Configuration", fg='cyan', bold=True))

    click.echo(f"\nDatabase: {DATABASE_PATH}")
    click.echo(f"Export dir: {EXPORT_DIR}")
    click.echo(f"Log level: {LOG_LEVEL}")
    click.echo(f"Log file: {LOG_FILE}")

    click.echo(click.style("\nEnabled scrapers:", fg='cyan'))
    for site in context.site_config.get_enabled_sites():
        click.echo(f"  ✅ {site['name']}")

    click.echo(click.style("\nRequest settings:", fg='cyan'))
    click.echo(f"  Min delay: {MIN_REQUEST_DELAY}s")
    click.echo(f"  Max delay: {MAX_REQUEST_DELAY}s")


@cli.command()
def version():
    """Show version information."""
    click.echo("FSBO Scraper v2.0.0")
    click.echo("A Python-based web scraping system for FSBO property listings")


@cli.command()
def init():
    """Initialize project with default configuration."""
    click.echo(click.style("Initializing FSBO Scraper project...", fg='cyan'))

    # Create directories
    dirs = ['data', 'exports', 'logs']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        click.echo(f"  ✅ Created {dir_name}/")

    # Initialize database
    db = FSBODatabase()
    click.echo("  ✅ Initialized database")

    # Save default config
    site_config = SiteConfig()
    site_config.save_config()
    click.echo("  ✅ Created default configuration")

    click.echo(click.style("\n✅ Project initialized!", fg='green'))
    click.echo("\nNext steps:")
    click.echo("  1. Review configuration: config/sites.json")
    click.echo("  2. Run first scrape: fsbo-scrape scrape")
    click.echo("  3. Export results: fsbo-scrape export -o listings.csv")


if __name__ == '__main__':
    cli()

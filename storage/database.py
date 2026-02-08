"""
SQLite database storage for FSBO listings.
Handles all database operations for storing and retrieving property data.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class FSBODatabase:
    """Manages SQLite database for FSBO property listings."""

    def __init__(self, db_path: str = 'data/fsbo_listings.db'):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _init_database(self) -> None:
        """Create database tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Listings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    street TEXT NOT NULL,
                    city TEXT NOT NULL,
                    state TEXT NOT NULL,
                    zip_code TEXT NOT NULL,
                    listing_url TEXT,
                    source_website TEXT NOT NULL,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    listing_hash TEXT UNIQUE NOT NULL,
                    is_exported INTEGER DEFAULT 0,
                    notes TEXT
                )
            ''')

            # Dedupe index
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_listing_hash 
                ON listings(listing_hash)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_address 
                ON listings(street, city, state, zip_code)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_source 
                ON listings(source_website)
            ''')

            # Scrape history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scrape_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_website TEXT NOT NULL,
                    scrape_start TIMESTAMP,
                    scrape_end TIMESTAMP,
                    listings_found INTEGER DEFAULT 0,
                    listings_new INTEGER DEFAULT 0,
                    listings_duplicates INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,
                    status TEXT,
                    error_message TEXT
                )
            ''')

            conn.commit()
            logger.info("Database initialized successfully")

    def add_listing(self, street: str, city: str, state: str, zip_code: str,
                   listing_url: str, source_website: str, notes: str = None) -> Optional[int]:
        """
        Add a listing to the database.
        
        Args:
            street: Street address
            city: City name
            state: State abbreviation
            zip_code: ZIP code
            listing_url: URL to listing
            source_website: Website scraped from
            notes: Additional notes
            
        Returns:
            Listing ID if inserted, None if duplicate
        """
        listing_hash = self._generate_hash(street, city, state, zip_code)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute('''
                    INSERT INTO listings (street, city, state, zip_code, 
                                         listing_url, source_website, listing_hash, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (street, city, state, zip_code, listing_url, source_website, 
                      listing_hash, notes))
                
                listing_id = cursor.lastrowid
                logger.debug(f"Added listing {listing_id}: {street}, {city}, {state}")
                return listing_id

            except sqlite3.IntegrityError:
                logger.debug(f"Duplicate listing skipped: {street}, {city}, {state}")
                return None

    def bulk_add_listings(self, listings: List[Dict]) -> Tuple[int, int]:
        """
        Add multiple listings at once.
        
        Args:
            listings: List of listing dictionaries
            
        Returns:
            Tuple of (new_count, duplicate_count)
        """
        new_count = 0
        duplicate_count = 0

        for listing in listings:
            result = self.add_listing(
                street=listing['street'],
                city=listing['city'],
                state=listing['state'],
                zip_code=listing['zip_code'],
                listing_url=listing.get('listing_url'),
                source_website=listing['source_website'],
                notes=listing.get('notes')
            )
            
            if result is not None:
                new_count += 1
            else:
                duplicate_count += 1

        return new_count, duplicate_count

    def get_listings(self, limit: int = None, offset: int = 0,
                    source: str = None, exported: bool = False) -> List[Dict]:
        """
        Retrieve listings from database.
        
        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            source: Filter by source website
            exported: Only exported listings
            
        Returns:
            List of listing dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            query = 'SELECT * FROM listings WHERE 1=1'
            params = []

            if source:
                query += ' AND source_website = ?'
                params.append(source)

            if exported:
                query += ' AND is_exported = 1'
            else:
                query += ' AND is_exported = 0'

            query += ' ORDER BY scraped_at DESC'

            if limit:
                query += f' LIMIT ? OFFSET ?'
                params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

    def get_listing_count(self, source: str = None) -> int:
        """Get total count of listings."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if source:
                cursor.execute('SELECT COUNT(*) FROM listings WHERE source_website = ?', (source,))
            else:
                cursor.execute('SELECT COUNT(*) FROM listings')

            return cursor.fetchone()[0]

    def mark_as_exported(self, listing_ids: List[int]) -> None:
        """Mark listings as exported."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            for listing_id in listing_ids:
                cursor.execute(
                    'UPDATE listings SET is_exported = 1, last_updated = CURRENT_TIMESTAMP WHERE id = ?',
                    (listing_id,)
                )

            conn.commit()

    def record_scrape_session(self, source_website: str, listings_found: int,
                            listings_new: int, listings_duplicates: int,
                            errors: int = 0, error_message: str = None,
                            status: str = 'completed') -> int:
        """
        Record a scraping session.
        
        Args:
            source_website: Website that was scraped
            listings_found: Total listings found
            listings_new: New listings added
            listings_duplicates: Duplicate listings skipped
            errors: Number of errors encountered
            error_message: Error details if any
            status: Session status
            
        Returns:
            Session ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO scrape_history 
                (source_website, scrape_start, scrape_end, listings_found, 
                 listings_new, listings_duplicates, errors, status, error_message)
                VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?)
            ''', (source_website, listings_found, listings_new, 
                  listings_duplicates, errors, status, error_message))

            session_id = cursor.lastrowid
            logger.info(
                f"Scrape session {session_id} recorded: {source_website} - "
                f"{listings_new} new, {listings_duplicates} duplicates, "
                f"{errors} errors"
            )
            return session_id

    def get_scrape_history(self, source: str = None, limit: int = 10) -> List[Dict]:
        """Get scrape session history."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if source:
                cursor.execute('''
                    SELECT * FROM scrape_history 
                    WHERE source_website = ?
                    ORDER BY scrape_start DESC
                    LIMIT ?
                ''', (source, limit))
            else:
                cursor.execute('''
                    SELECT * FROM scrape_history 
                    ORDER BY scrape_start DESC
                    LIMIT ?
                ''', (limit,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def clear_all_data(self) -> None:
        """Clear all listings from database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM listings')
            cursor.execute('DELETE FROM scrape_history')
            conn.commit()
            logger.warning("All data cleared from database")

    def export_to_csv(self, output_path: str, source: str = None,
                     exported_only: bool = False) -> None:
        """
        Export listings to CSV file.
        
        Args:
            output_path: Path to CSV file
            source: Filter by source website
            exported_only: Only export marked listings
        """
        import csv

        listings = self.get_listings(source=source, exported=exported_only)

        if not listings:
            logger.warning("No listings to export")
            return

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Filter to only include fields we want in CSV
        fieldnames = ['id', 'street', 'city', 'state', 'zip_code', 
                     'listing_url', 'source_website', 'scraped_at']
        
        filtered_listings = [
            {key: listing.get(key, '') for key in fieldnames}
            for listing in listings
        ]

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(filtered_listings)

        logger.info(f"Exported {len(listings)} listings to {output_path}")

    @staticmethod
    def _generate_hash(street: str, city: str, state: str, zip_code: str) -> str:
        """Generate unique hash for address deduplication."""
        import hashlib
        address_string = f"{street.lower()}{city.lower()}{state.lower()}{zip_code}"
        return hashlib.md5(address_string.encode()).hexdigest()

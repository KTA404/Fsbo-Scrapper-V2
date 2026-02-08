"""
Site configuration loader.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SiteConfig:
    """Manages configuration for scraper sites."""

    def __init__(self, config_file: str = 'config/sites.json'):
        """
        Initialize site configuration.
        
        Args:
            config_file: Path to sites.json configuration file
        """
        self.config_file = Path(config_file)
        self.sites = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from JSON file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Loaded configuration from {self.config_file}")
                    return config
            except Exception as e:
                logger.error(f"Error loading config file {self.config_file}: {e}")
                return self._get_default_config()
        else:
            logger.warning(f"Config file {self.config_file} not found. Using defaults.")
            return self._get_default_config()

    @staticmethod
    def _get_default_config() -> Dict:
        """Get default configuration."""
        return {
            "sites": [
                {
                    "name": "FSBO.com",
                    "scraper": "fsbo_com",
                    "enabled": True,
                    "min_delay": 3.0,
                    "max_delay": 8.0
                },
                {
                    "name": "Zillow FSBO",
                    "scraper": "zillow_fsbo",
                    "enabled": True,
                    "min_delay": 4.0,
                    "max_delay": 10.0
                },
                {
                    "name": "Craigslist Housing",
                    "scraper": "craigslist_housing",
                    "enabled": True,
                    "min_delay": 2.0,
                    "max_delay": 5.0
                }
            ],
            "thanks_io": {
                "enabled": False,
                "api_key": "",
                "campaign_id": ""
            },
            "export": {
                "format": "csv",
                "delimiter": ",",
                "encoding": "utf-8"
            }
        }

    def get_enabled_sites(self) -> List[Dict]:
        """Get list of enabled sites."""
        return [s for s in self.sites.get('sites', []) if s.get('enabled', True)]

    def get_site(self, scraper_name: str) -> Optional[Dict]:
        """Get configuration for a specific scraper."""
        for site in self.sites.get('sites', []):
            if site.get('scraper') == scraper_name:
                return site
        return None

    def is_site_enabled(self, scraper_name: str) -> bool:
        """Check if a scraper is enabled."""
        site = self.get_site(scraper_name)
        return site.get('enabled', False) if site else False

    def save_config(self) -> None:
        """Save current configuration to file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.sites, f, indent=2)
        logger.info(f"Configuration saved to {self.config_file}")


def load_site_config(config_file: str = 'config/sites.json') -> Dict:
    """Load site configuration."""
    return SiteConfig(config_file).sites

"""
Rate limiting and retry logic for respectful web scraping.
"""

import time
import random
from typing import Callable, Any, TypeVar
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RateLimiter:
    """
    Rate limiter to enforce request delays between scrapes.
    Respects target site's robots.txt recommendations.
    """

    def __init__(self, min_delay: float = 1.0, max_delay: float = 3.0,
                 jitter: bool = True):
        """
        Initialize rate limiter.
        
        Args:
            min_delay: Minimum delay between requests (seconds)
            max_delay: Maximum delay between requests (seconds)
            jitter: Whether to randomize delays
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.last_request_time = 0

    def wait(self) -> None:
        """Wait appropriate amount before making next request."""
        elapsed = time.time() - self.last_request_time
        
        if self.jitter:
            delay = random.uniform(self.min_delay, self.max_delay)
        else:
            delay = self.min_delay

        if elapsed < delay:
            sleep_time = delay - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def record_request(self) -> None:
        """Record that a request was made."""
        self.last_request_time = time.time()


class RetryConfig:
    """Configuration for retry logic."""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0,
                 retry_on_status: list = None):
        """
        Initialize retry configuration.
        
        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Multiplier for exponential backoff
            retry_on_status: HTTP status codes to retry on
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_on_status = retry_on_status or [408, 429, 500, 502, 503, 504]


def retry_with_backoff(config: RetryConfig) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        config: RetryConfig instance
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < config.max_retries:
                        wait_time = config.backoff_factor ** attempt
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/"
                            f"{config.max_retries + 1}). Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"{func.__name__} failed after {config.max_retries + 1} attempts")
            
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


class RequestThrottler:
    """
    Throttles requests per domain to prevent overwhelming servers.
    """

    def __init__(self, max_requests_per_minute: int = 60):
        """
        Initialize throttler.
        
        Args:
            max_requests_per_minute: Max requests per domain per minute
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.request_times = {}

    def should_throttle(self, domain: str) -> bool:
        """Check if domain is being accessed too frequently."""
        now = time.time()
        cutoff = now - 60  # 1 minute window

        if domain not in self.request_times:
            self.request_times[domain] = []

        # Remove old requests outside the window
        self.request_times[domain] = [
            t for t in self.request_times[domain] if t > cutoff
        ]

        return len(self.request_times[domain]) >= self.max_requests_per_minute

    def record_request(self, domain: str) -> None:
        """Record a request for a domain."""
        if domain not in self.request_times:
            self.request_times[domain] = []
        
        self.request_times[domain].append(time.time())

    def get_wait_time(self, domain: str) -> float:
        """Get how long to wait before next request for domain."""
        now = time.time()
        cutoff = now - 60

        if domain not in self.request_times or not self.request_times[domain]:
            return 0

        recent_requests = [t for t in self.request_times[domain] if t > cutoff]
        
        if len(recent_requests) < self.max_requests_per_minute:
            return 0

        # Wait until oldest request leaves the 60-second window
        return (recent_requests[0] + 60) - now

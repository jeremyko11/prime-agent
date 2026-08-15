"""Firecrawl Skill - __init__.py"""

from firecrawl_skill._impl import (
    scrape,
    search,
    crawl,
    batch_scrape,
    deep_research,
    get_credits,
)

__version__ = "1.0.0"
__all__ = ["scrape", "search", "crawl", "batch_scrape", "deep_research", "get_credits"]

"""
Firecrawl Skill - _impl.py

Wraps firecrawl-py V1FirecrawlApp for Prime Agent.
Provides: scrape, search, crawl, batch_scrape, deep_research
"""

import os
import sys
import time
from typing import Optional, List, Dict, Any

# Lazy-init the app (so import doesn't fail if no API key yet)
_app = None
_last_error = None


def _get_app():
    """Get or create the FirecrawlApp instance."""
    global _app, _last_error

    if _app is not None:
        return _app

    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        # Try loading from .env file
        env_path = os.path.expanduser("~/.prime/agent/skills/firecrawl/.env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("FIRECRAWL_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        os.environ["FIRECRAWL_API_KEY"] = api_key
                        break

    if not api_key:
        _last_error = (
            "FIRECRAWL_API_KEY not set. Set it with:\n"
            "  export FIRECRAWL_API_KEY='fc-xxx'\n"
            "Or create ~/.prime/agent/skills/firecrawl/.env with:\n"
            "  FIRECRAWL_API_KEY=fc-xxx"
        )
        print(f"[FIRECRAWL] Error: {_last_error}", file=sys.stderr)
        return None

    try:
        from firecrawl import V1FirecrawlApp
        _app = V1FirecrawlApp(api_key=api_key, timeout=60, max_retries=2)
        print("[FIRECRAWL] Connected (V1FirecrawlApp)", file=sys.stderr)
        return _app
    except Exception as e:
        _last_error = f"Failed to init FirecrawlApp: {e}"
        print(f"[FIRECRAWL] Error: {_last_error}", file=sys.stderr)
        return None


def scrape(url: str, formats: list = None, timeout: int = 30) -> Optional[str]:
    """
    Scrape a single URL and return clean Markdown.

    Args:
        url: The URL to scrape
        formats: Output formats (default: ['markdown'])
        timeout: Request timeout in seconds

    Returns:
        Markdown string of the page content, or None on error.
    """
    app = _get_app()
    if app is None:
        return None

    if formats is None:
        formats = ["markdown"]

    try:
        result = app.scrape_url(url, params={
            "formats": formats,
            "waitFor": 1000,  # wait 1s for JS rendering
        })

        # Extract markdown from result
        if isinstance(result, dict):
            data = result.get("data", result)
            if isinstance(data, dict):
                md = data.get("markdown", "")
                if md:
                    return md
                # Fallback to content
                return data.get("content", "")
            return str(data)
        elif isinstance(result, str):
            return result
        else:
            return str(result)

    except Exception as e:
        print(f"[FIRECRAWL] scrape error for {url}: {e}", file=sys.stderr)
        return None


def search(query: str, limit: int = 5) -> List[Dict[str, str]]:
    """
    Search the web using Firecrawl.

    Args:
        query: Search query
        limit: Max number of results (default 5, each costs 1 credit)

    Returns:
        List of dicts: [{"url": "...", "title": "...", "markdown": "..."}, ...]
    """
    app = _get_app()
    if app is None:
        return []

    try:
        result = app.search(query, params={
            "limit": limit,
            "scrapeOptions": {"formats": ["markdown"]},
        })

        results = []
        if isinstance(result, dict):
            data = result.get("data", result)
            if isinstance(data, list):
                for item in data:
                    results.append({
                        "url": item.get("url", ""),
                        "title": item.get("title", item.get("metadata", {}).get("title", "")),
                        "markdown": item.get("markdown", item.get("content", ""))[:2000],
                    })
            elif isinstance(data, dict):
                results.append({
                    "url": data.get("url", ""),
                    "title": data.get("title", ""),
                    "markdown": data.get("markdown", data.get("content", ""))[:2000],
                })

        print(f"[FIRECRAWL] search '{query}': {len(results)} results", file=sys.stderr)
        return results

    except Exception as e:
        print(f"[FIRECRAWL] search error: {e}", file=sys.stderr)
        return []


def crawl(url: str, limit: int = 10) -> List[Dict[str, str]]:
    """
    Crawl an entire website. Returns all discovered pages as Markdown.
    WARNING: Uses 1 credit per page discovered. Use limit to control cost.

    Args:
        url: Root URL to start crawling
        limit: Max pages to crawl (default 10)

    Returns:
        List of dicts: [{"url": "...", "markdown": "..."}, ...]
    """
    app = _get_app()
    if app is None:
        return []

    try:
        result = app.crawl_url(url, params={
            "limit": limit,
            "scrapeOptions": {"formats": ["markdown"]},
        }, wait_until_done=True, timeout=120)

        results = []
        if isinstance(result, dict):
            data = result.get("data", result)
            if isinstance(data, list):
                for item in data:
                    results.append({
                        "url": item.get("url", ""),
                        "markdown": item.get("markdown", item.get("content", ""))[:3000],
                    })

        print(f"[FIRECRAWL] crawl '{url}': {len(results)} pages", file=sys.stderr)
        return results

    except Exception as e:
        print(f"[FIRECRAWL] crawl error: {e}", file=sys.stderr)
        return []


def batch_scrape(urls: List[str]) -> List[Dict[str, str]]:
    """
    Scrape multiple URLs in batch.

    Args:
        urls: List of URLs to scrape

    Returns:
        List of dicts: [{"url": "...", "markdown": "..."}, ...]
    """
    app = _get_app()
    if app is None:
        return []

    try:
        result = app.batch_scrape_urls(urls, params={
            "formats": ["markdown"],
        }, wait_until_done=True, timeout=120)

        results = []
        if isinstance(result, dict):
            data = result.get("data", result)
            if isinstance(data, list):
                for item in data:
                    results.append({
                        "url": item.get("url", ""),
                        "markdown": item.get("markdown", item.get("content", ""))[:3000],
                    })

        print(f"[FIRECRAWL] batch_scrape: {len(results)}/{len(urls)} succeeded", file=sys.stderr)
        return results

    except Exception as e:
        print(f"[FIRECRAWL] batch_scrape error: {e}", file=sys.stderr)
        # Fallback: scrape one by one
        print("[FIRECRAWL] Falling back to sequential scrape...", file=sys.stderr)
        results = []
        for url in urls:
            md = scrape(url)
            if md:
                results.append({"url": url, "markdown": md})
            time.sleep(0.5)  # rate limit
        return results


def deep_research(query: str, max_depth: int = 3, time_limit: int = 60) -> Optional[Dict[str, Any]]:
    """
    Firecrawl's AI-powered deep research. Analyzes a topic across multiple sources.
    WARNING: Uses 10-50 credits per query. Use sparingly!

    Args:
        query: Research question
        max_depth: Research depth (1-5, default 3)
        time_limit: Max time in seconds (default 60)

    Returns:
        Dict with research report and sources, or None on error.
    """
    app = _get_app()
    if app is None:
        return None

    try:
        result = app.deep_research(query, params={
            "maxDepth": max_depth,
            "timeLimit": time_limit,
        })

        if isinstance(result, dict):
            data = result.get("data", result)
            print(f"[FIRECRAWL] deep_research '{query}': completed", file=sys.stderr)
            return {
                "report": data.get("analysis", data.get("report", "")),
                "sources": data.get("sources", []),
                "activity": data.get("activity", []),
            }
        return {"report": str(result), "sources": [], "activity": []}

    except Exception as e:
        print(f"[FIRECRAWL] deep_research error: {e}", file=sys.stderr)
        return None


def get_credits() -> Optional[int]:
    """Check remaining Firecrawl credits."""
    app = _get_app()
    if app is None:
        return None

    try:
        result = app.get_credit_usage()
        if isinstance(result, dict):
            remaining = result.get("data", {}).get("remaining_credits", result.get("remaining", 0))
            print(f"[FIRECRAWL] Remaining credits: {remaining}", file=sys.stderr)
            return remaining
    except Exception as e:
        print(f"[FIRECRAWL] get_credits error: {e}", file=sys.stderr)
    return None


# Print status on import (don't auto-connect, just show availability)
print(
    "[FIRECRAWL] Skill loaded. Functions: scrape, search, crawl, batch_scrape, "
    "deep_research, get_credits. Call any function to auto-connect.",
    file=sys.stderr, flush=True
)

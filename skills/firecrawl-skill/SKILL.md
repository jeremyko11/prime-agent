---
name: firecrawl-skill
description: "Firecrawl: powerful web scraping with JS rendering, Markdown output, site crawling, and deep research. 500 free credits/month. Use for data collection when websearch is not enough."
version: 1.0.0
author: user
---

# Firecrawl - Web Scraping & Data Collection

Turns any URL into clean Markdown. Handles JS-rendered pages, paginated content,
and entire site crawls. Also supports search and deep research.

## When to Use

1. **Scrape a specific page**: `firecrawl.scrape("https://example.com/page")` → clean Markdown
2. **Search the web**: `firecrawl.search("建工一切险 临时设施 条款")` → list of results with content
3. **Crawl a whole site**: `firecrawl.crawl("https://www.nfra.gov.cn", limit=20)` → all pages as Markdown
4. **Batch scrape**: `firecrawl.batch_scrape(["url1", "url2", "url3"])` → multiple pages at once
5. **Deep research**: `firecrawl.deep_research("2026财产险新规对建工险影响", max_depth=3)` → structured research report

## Usage

```python
import firecrawl_skill as fc

# Scrape a single URL (returns Markdown text)
markdown = fc.scrape("https://www.nfra.gov.cn/xx/通知.html")
print(markmark[:500])

# Search (returns list of {url, title, markdown})
results = fc.search("GB/T 50500-2024 临时设施费", limit=5)
for r in results:
    print(r['title'], r['url'])

# Crawl an entire site (returns list of pages)
pages = fc.crawl("https://www.iachina.cn", limit=10)

# Batch scrape multiple URLs
pages = fc.batch_scrape([
    "https://example.com/page1",
    "https://example.com/page2"
])

# Deep research (Firecrawl's AI-powered research)
report = fc.deep_research(
    "建工一切险临时设施理赔 2026新规",
    max_depth=3,
    time_limit=60
)
```

## API Key

Requires `FIRECRAWL_API_KEY` environment variable.
Set it in `~/.bashrc` or pass directly:
```python
import os
os.environ['FIRECRAWL_API_KEY'] = 'fc-xxx'
import firecrawl_skill as fc
```

## Credit Usage

- Free tier: 500 credits/month
- `scrape`: 1 credit per page
- `crawl`: 1 credit per page discovered
- `search`: 1 credit per result
- `deep_research`: ~10-50 credits per query (use sparingly!)

## Error Handling

All functions return `None` on failure and print error to stderr.
Check for `None` before using results.

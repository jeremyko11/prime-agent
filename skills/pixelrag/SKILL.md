---
name: pixelrag
description: "Visual RAG tool - screenshot web pages/PDFs and search by visual content. Uses pixelshot CLI for rendering and PixelRAG API for visual search. Preserves tables, charts, and layout that text parsing loses."
version: 1.0.0
author: user
---

# PixelRAG - Visual RAG Tool

## What it does

PixelRAG renders documents (web pages, PDFs, images) as screenshots and retrieves over the images directly. Visual structure that HTML parsing throws away — tables, charts, layout, infographics — stays intact.

## When to use

- When you need to **see** a web page (tables, charts, diagrams) instead of reading raw HTML
- When you need to search Wikipedia by visual content
- When building a visual index of your own documents (PDFs, web pages)
- When text-based RAG loses important formatting

## Functions

### `screenshot(url_or_path, output_dir="/tmp/pixelrag_tiles")`
Render a web page or PDF to screenshot tiles.
- `url_or_path`: URL (https://...) or local file path (.pdf, .png, .html)
- `output_dir`: Where to save screenshot tiles
- Returns: list of tile file paths

### `search(query, n_docs=5)`
Search the hosted PixelRAG index (8.28M Wikipedia pages).
- `query`: Search query text
- `n_docs`: Number of results (default 5)
- Returns: list of {title, url, score, text}

### `build_index(source_path, output_dir, device="auto")`
Build a visual index from your own documents.
- `source_path`: Path to PDF, web page, or directory of documents
- `output_dir`: Where to save the index
- `device`: "auto", "cpu", "cuda", or "mps"
- Returns: index path

### `serve_index(index_dir, port=30001)`
Start a local search server for your custom index.
- `index_dir`: Path to the built index
- `port`: Port number (default 30001)
- Returns: server URL

## Important notes

- `pixelshot` CLI must be on PATH (installed via `uv tool install pixelrag`)
- Chrome headless shell auto-downloads on first use (linux-x64)
- Hosted API at https://api.pixelrag.ai is free, no API key needed
- For custom indexes, needs `pip install 'pixelrag[index]'` (downloads ~4GB model)

## Examples

```python
import pixelrag_skill as pr

# Screenshot a web page
tiles = pr.screenshot("https://example.com")
print(f"Got {len(tiles)} tiles")

# Search Wikipedia visually
results = pr.search("construction insurance temporary facilities")
for r in results:
    print(r['title'], r['score'])

# Build index from PDF
pr.build_index("/root/work/policy.pdf", "/root/work/policy_index")

# Search custom index
pr.serve_index("/root/work/policy_index")
results = pr.search_local("temporary facility cost breakdown", port=30001)
```

#!/usr/bin/env python3
"""
PixelRAG skill for Prime Agent.
Provides visual RAG capabilities: screenshot, search, and index building.
"""

import os
import json
import subprocess
import shutil
import httpx
from pathlib import Path
from typing import Optional

# Ensure pixelshot is on PATH
_PIXELSHOT = shutil.which("pixelshot") or "/root/.local/bin/pixelshot"
_PIXELRAG = shutil.which("pixelrag") or "/root/.local/bin/pixelrag"
_API_URL = "https://api.pixelrag.ai"


def screenshot(
    url_or_path: str,
    output_dir: str = "/tmp/pixelrag_tiles",
    backend: str = "cdp",
    quality: int = 80,
    tile_height: int = 1200,
    viewport_width: int = 1280,
) -> list[str]:
    """
    Render a web page or PDF to screenshot tiles.

    Args:
        url_or_path: URL (https://...) or local file path (.pdf, .png, .html)
        output_dir: Where to save screenshot tiles
        backend: "cdp" (faster, default) or "playwright"
        quality: JPEG quality (1-100, default 80)
        tile_height: Tile height in pixels (default 1200)
        viewport_width: Browser viewport width (default 1280)

    Returns:
        List of screenshot tile file paths
    """
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        _PIXELSHOT,
        url_or_path,
        "--output", output_dir,
        "--backend", backend,
        "--quality", str(quality),
        "--tile-height", str(tile_height),
        "--viewport-width", str(viewport_width),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PATH": f"/root/.local/bin:{os.environ.get('PATH', '')}"},
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"pixelshot failed (exit {result.returncode}): {result.stderr[-500:]}"
        )

    tiles = sorted(Path(output_dir).glob("*.jpg")) + sorted(Path(output_dir).glob("*.png"))
    return [str(t) for t in tiles]


def search(
    query: str,
    n_docs: int = 5,
    timeout: int = 30,
) -> list[dict]:
    """
    Search the hosted PixelRAG index (8.28M Wikipedia pages).

    Args:
        query: Search query text
        n_docs: Number of results (default 5, max 20)
        timeout: Request timeout in seconds

    Returns:
        List of {title, url, score, text} dicts
    """
    # Bypass proxy to avoid 502 from Clash
    no_proxy_env = {k: v for k, v in os.environ.items()
                    if k.lower() not in ('http_proxy', 'https_proxy', 'all_proxy')}
    no_proxy_env["NO_PROXY"] = "*"

    data = {
        "queries": [{"text": query}],
        "n_docs": min(n_docs, 20),
    }

    try:
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            resp = client.post(
                f"{_API_URL}/search",
                json=data,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            result = resp.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 502:
            raise RuntimeError(
                "PixelRAG API is temporarily unavailable (502). "
                "Try again later or use build_index() to create a local index."
            ) from e
        raise
    except Exception as e:
        raise RuntimeError(f"PixelRAG API request failed: {e}") from e

    results = result.get("results", [])
    parsed = []
    for doc in results:
        parsed.append({
            "title": doc.get("title", ""),
            "url": doc.get("url", ""),
            "score": doc.get("score", 0),
            "text": doc.get("text", doc.get("content", ""))[:500],
        })
    return parsed


def search_image(
    image_path: str,
    n_docs: int = 5,
    timeout: int = 30,
) -> list[dict]:
    """
    Search the hosted PixelRAG index with an image query (visual search).

    Args:
        image_path: Path to the query image
        n_docs: Number of results

    Returns:
        List of {title, url, score} dicts
    """
    import base64

    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    data = {
        "queries": [{"image": img_b64}],
        "n_docs": min(n_docs, 20),
    }

    with httpx.Client(timeout=timeout, trust_env=False) as client:
        resp = client.post(
            f"{_API_URL}/search",
            json=data,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        result = resp.json()

    return result.get("results", [])


def build_index(
    source_path: str,
    output_dir: str,
    device: str = "auto",
    config_path: Optional[str] = None,
) -> str:
    """
    Build a visual index from your own documents.

    Args:
        source_path: Path to PDF, web page URL, or directory of documents
        output_dir: Where to save the index
        device: "auto" (default), "cpu", "cuda", or "mps"
        config_path: Optional path to pixelrag.yaml config

    Returns:
        Path to the built index
    """
    os.makedirs(output_dir, exist_ok=True)

    if config_path is None:
        # Auto-generate config
        config = f"""source:
  type: local
  path: {source_path}
embed:
  model: Qwen/Qwen3-VL-Embedding-2B
  device: {device}
output: {output_dir}
"""
        config_path = os.path.join(output_dir, "pixelrag.yaml")
        with open(config_path, "w") as f:
            f.write(config)

    # Run pixelrag index build
    cmd = [_PIXELRAG, "index", "build"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=3600,
        cwd=output_dir,
        env={**os.environ, "PATH": f"/root/.local/bin:{os.environ.get('PATH', '')}"},
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"pixelrag index build failed (exit {result.returncode}): {result.stderr[-500:]}"
        )

    return output_dir


def serve_index(
    index_dir: str,
    port: int = 30001,
    background: bool = True,
) -> str:
    """
    Start a local search server for your custom index.

    Args:
        index_dir: Path to the built index
        port: Port number (default 30001)
        background: If True, run in background

    Returns:
        Server URL (http://localhost:{port})
    """
    cmd = [_PIXELRAG, "serve", "--index-dir", index_dir, "--port", str(port)]

    if background:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "PATH": f"/root/.local/bin:{os.environ.get('PATH', '')}"},
        )
        import time
        time.sleep(3)  # Wait for server to start
        return f"http://localhost:{port}"
    else:
        # Blocking call
        subprocess.run(cmd, env={**os.environ, "PATH": f"/root/.local/bin:{os.environ.get('PATH', '')}"})
        return f"http://localhost:{port}"


def search_local(
    query: str,
    port: int = 30001,
    n_docs: int = 5,
    timeout: int = 30,
) -> list[dict]:
    """
    Search a local PixelRAG index served by serve_index().

    Args:
        query: Search query text
        port: Port of the local server (default 30001)
        n_docs: Number of results
        timeout: Request timeout

    Returns:
        List of result dicts
    """
    data = {
        "queries": [{"text": query}],
        "n_docs": min(n_docs, 20),
    }

    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            f"http://localhost:{port}/search",
            json=data,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        result = resp.json()

    return result.get("results", [])


def check_status() -> dict:
    """Check the status of PixelRAG hosted API."""
    try:
        with httpx.Client(timeout=10, trust_env=False) as client:
            resp = client.get(f"{_API_URL}/status")
            return resp.json() if resp.status_code == 200 else {"status": "error", "code": resp.status_code}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_credits() -> Optional[int]:
    """Check remaining API credits (if applicable)."""
    return None  # Hosted API is free, no credits


# Re-export for convenience
__all__ = [
    "screenshot",
    "search",
    "search_image",
    "build_index",
    "serve_index",
    "search_local",
    "check_status",
    "get_credits",
]

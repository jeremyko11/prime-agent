"""Websearch skill: Bocha + DuckDuckGo + GitHub + Wikipedia.

Free fallbacks (DuckDuckGo/GitHub/Wikipedia) never expire, no API key needed.
- Bocha: DeepSeek's official search, China-direct (needs BOCHA_API_KEY)
- DuckDuckGo: free, no key (uses ddgs lib, needs proxy in China)
- GitHub: free, no key, 10 req/min (code/tech search, direct)
- Wikipedia: free, no key, never expires (zh+en encyclopedia, direct)
"""

from __future__ import annotations

import asyncio
import os
import re

import httpx

_UA = "prime-agent/0.7.1 (https://github.com/PrimeIntellect-ai/prime-agent)"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


def _get_proxy() -> str | None:
    return (
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("http_proxy")
        or None
    )


def _has_bocha_key() -> bool:
    return bool(os.environ.get("BOCHA_API_KEY") or os.environ.get("bocha_api_key"))


# ---- Bocha backend (China-direct, DeepSeek's official search) ----

def _bocha_search_sync(query: str, num_results: int, timeout: int) -> list[dict]:
    api_key = os.environ.get("BOCHA_API_KEY") or os.environ.get("bocha_api_key") or ""
    if not api_key:
        raise RuntimeError("BOCHA_API_KEY not set")
    url = "https://api.bochaai.com/v1/web-search"
    headers = {"Authorization": "Bearer " + api_key, "Content-Type": "application/json"}
    payload = {"query": query, "summary": True, "freshness": "noLimit", "count": min(num_results, 50)}
    with httpx.Client(timeout=timeout, headers=headers) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    data_inner = data.get("data") or data
    web_pages = data_inner.get("webPages") or {}
    results: list[dict] = []
    for item in web_pages.get("value") or []:
        results.append({
            "title": item.get("name") or "",
            "url": item.get("url") or "",
            "snippet": item.get("snippet") or "",
            "summary": item.get("summary") or "",
            "siteName": item.get("siteName") or "",
            "datePublished": item.get("datePublished") or "",
        })
    return results


# ---- DuckDuckGo backend (free, no key) ----

def _ddg_search_sync(query: str, num_results: int, timeout: int) -> list[dict]:
    from ddgs import DDGS
    proxy = _get_proxy()
    try:
        kwargs = {"timeout": timeout}
        if proxy:
            kwargs["proxy"] = proxy
        with DDGS(**kwargs) as ddgs:
            return list(ddgs.text(query, max_results=num_results))
    except Exception as e:
        try:
            with DDGS(timeout=timeout) as ddgs:
                return list(ddgs.text(query, max_results=num_results))
        except Exception:
            raise RuntimeError("DuckDuckGo search failed: " + str(e))


# ---- GitHub backend (free, no key, 10 req/min, code/tech search) ----

def _github_search_sync(query: str, num_results: int, timeout: int) -> list[dict]:
    headers = {"User-Agent": _UA, "Accept": "application/vnd.github+json"}
    url = "https://api.github.com/search/repositories"
    params = {"q": query, "per_page": str(min(num_results, 10)), "sort": "stars", "order": "desc"}
    with httpx.Client(timeout=timeout, headers=headers) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    results = []
    for item in (data.get("items") or [])[:num_results]:
        results.append({
            "title": item.get("full_name") or "",
            "url": item.get("html_url") or "",
            "snippet": item.get("description") or "",
            "siteName": "GitHub (stars: " + str(item.get("stargazers_count", 0)) + ")",
        })
    return results


# ---- Wikipedia backend (free, no key, never expires, zh+en) ----

def _wikipedia_search_sync(query: str, num_results: int, timeout: int) -> list[dict]:
    headers = {"User-Agent": _UA}
    results: list[dict] = []
    for lang in ["zh", "en"]:
        url = "https://" + lang + ".wikipedia.org/w/api.php"
        params = {"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": str(min(num_results, 5))}
        try:
            with httpx.Client(timeout=timeout, headers=headers) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            search_results = (data.get("query") or {}).get("search") or []
            for item in search_results:
                title = item.get("title") or ""
                snippet = re.sub(r"<[^>]+>", "", item.get("snippet") or "")
                results.append({
                    "title": title,
                    "url": "https://" + lang + ".wikipedia.org/wiki/" + title.replace(" ", "_"),
                    "snippet": snippet,
                    "siteName": "Wikipedia(" + lang + ")",
                })
            if results:
                return results
        except Exception:
            continue
    if not results:
        raise RuntimeError("Wikipedia search returned no results")
    return results


# ---- Format ----

def _format_results(results: list[dict], query: str) -> str:
    sections: list[str] = []
    for i, r in enumerate(results):
        title = (r.get("title") or "").strip() or "Untitled"
        lines = ["Result " + str(i) + ": " + title]
        link = (r.get("url") or r.get("href") or "").strip()
        if link:
            lines.append("URL: " + link)
        site = (r.get("siteName") or "").strip()
        if site:
            lines.append("Source: " + site)
        date = (r.get("datePublished") or "").strip()
        if date:
            lines.append("Published: " + date)
        summary = (r.get("summary") or "").strip()
        snippet = (r.get("snippet") or r.get("body") or "").strip()
        if summary:
            lines.append("Summary: " + summary)
        elif snippet:
            lines.append("Snippet: " + snippet)
        sections.append("\n".join(lines))
    if not sections:
        return "No results returned for query: " + query
    return "\n\n---\n\n".join(sections)


# ---- Main run ----

async def run(
    query: str,
    *,
    max_output: int = 8192,
    timeout: int | None = None,
    num_results: int | None = None,
) -> str:
    if timeout is None:
        timeout = _env_int("PRIME_AGENT_WEBSEARCH_TIMEOUT", 30)
    if num_results is None:
        num_results = _env_int("PRIME_AGENT_WEBSEARCH_NUM_RESULTS", 8)

    # Backend chain: Bocha (if key) -> DuckDuckGo -> GitHub -> Wikipedia
    backends = []
    if _has_bocha_key():
        backends.append(("Bocha", _bocha_search_sync))
    backends.append(("DuckDuckGo", _ddg_search_sync))
    backends.append(("GitHub", _github_search_sync))
    backends.append(("Wikipedia", _wikipedia_search_sync))

    backend = "none"
    result = ""
    errors = []
    for name, fn in backends:
        try:
            results = await asyncio.to_thread(fn, query, num_results, timeout)
            if results:
                result = _format_results(results, query)
                backend = name
                break
        except Exception as e:
            errors.append(name + ": " + str(e))
            continue
    else:
        result = "Error: all backends failed. " + "; ".join(errors)

    output = "[" + backend + "] Results for query \"" + query + "\":\n\n" + result

    if len(output) > max_output:
        total = len(output)
        marker = "\n... [output truncated, " + str(total) + " chars total] ...\n"
        half = max(0, (max_output - len(marker)) // 2)
        output = output[:half] + marker + output[len(output) - half:]
        if len(output) > max_output:
            output = output[:max_output]

    return output

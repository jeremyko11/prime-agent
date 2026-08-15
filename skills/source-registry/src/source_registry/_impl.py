"""Source Registry: unified multi-source research connectors.

Output format matches the websearch skill ("Result N: ..." + "URL: ...") so the
deep-research URL extractor works unchanged.

Search backends (free, no API key):
- arXiv        preprints (physics/CS/quant/econ)
- OpenAlex     250M+ works, open scholarly index
- Semantic Scholar (unauthenticated pool; 429s are expected and tolerated)
- HackerNews   Algolia search API, tech community
- Reddit       /search.json, community discussions
- GDELT        global news article list (real article URLs)
- GoogleNewsRSS international news (links are news.google.com redirects)
- SecRSS       security media feeds (BleepingComputer/The Record), keyword-filtered

Opt-in backends (not in the default set):
- webz         Webz.io dark-web/threat stream, paid API gated by WEBZ_IO_API_KEY.
               Aggregated-layer strategy: cleaned intel via legal commercial feed,
               no Tor connection. Without the key the backend raises a clear
               config error that fan-out tolerates as "[backend errors]".

Special actions:
- action="tg"     read a Telegram PUBLIC channel web preview (t.me/s/<channel>)
- action="crawl"  same-domain crawl seeded from one URL, tier-ranked
- action="status" backend health / env summary
"""

from __future__ import annotations

import asyncio
import html as _html
import json
import os
import re
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None

try:
    from research_guard import consume, log_event
except ImportError:
    consume = None
    log_event = None

try:
    from read_page._impl import _tier_for
except ImportError:
    def _tier_for(url: str) -> str:
        return "P3"

_UA = "prime-agent-source-registry/1.0 (research skill; contact: agent@prime.local)"
_UA_BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

DEFAULT_BACKENDS = ("arxiv", "openalex", "s2", "hn", "reddit", "gdelt", "newsrss")
_PER_BACKEND_LIMIT = 4
_MERGE_LIMIT = 12


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _explicit_proxy() -> str | None:
    return (os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy") or None)


def _root_domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _get(url: str, *, params: dict | None = None, timeout: int = 15,
         ua: str = _UA, accept: str = "application/json,text/xml,*/*") -> httpx.Response:
    """GET with env-proxy first, explicit env proxy, then direct. Raises on HTTP error."""
    if httpx is None:
        raise RuntimeError("httpx not installed")
    errors = []
    attempts = [{"trust_env": True}, {"trust_env": False}]
    proxy = _explicit_proxy()
    if proxy:
        attempts.insert(1, {"proxy": proxy, "trust_env": False})
    for opts in attempts:
        try:
            with httpx.Client(timeout=timeout, headers={"User-Agent": ua, "Accept": accept},
                              follow_redirects=True, **opts) as client:
                r = client.get(url, params=params)
                r.raise_for_status()
                return r
        except Exception as e:
            errors.append(str(e))
    raise RuntimeError("; ".join(errors[:2]))


def _clean(text: str, cap: int = 320) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = _html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:cap]


# ---------------- arXiv ----------------

def _arxiv_sync(query: str, n: int, timeout: int) -> list[dict]:
    r = _get("http://export.arxiv.org/api/query", params={
        "search_query": f"all:{query}", "start": "0", "max_results": str(n),
        "sortBy": "relevance",
    }, timeout=timeout, accept="application/atom+xml")
    out = []
    for entry in re.findall(r"<entry>(.*?)</entry>", r.text, re.S)[:n]:
        title = _clean(re.search(r"<title>(.*?)</title>", entry, re.S).group(1), 160)
        aid = re.search(r"<id>(.*?)</id>", entry, re.S)
        summary = _clean(re.search(r"<summary>(.*?)</summary>", entry, re.S).group(1), 300)
        pub = re.search(r"<published>(\d{4}-\d{2})", entry)
        out.append({"title": title, "url": aid.group(1) if aid else "",
                    "snippet": summary, "siteName": "[arXiv] preprint",
                    "date": pub.group(1) if pub else ""})
    return out


# ---------------- OpenAlex ----------------

def _openalex_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    size = max((max(v) for v in inv.values() if v), default=0) + 1
    words = [""] * size
    for w, idxs in inv.items():
        for i in idxs:
            if i < size:
                words[i] = w
    return " ".join(words)


def _openalex_sync(query: str, n: int, timeout: int) -> list[dict]:
    r = _get("https://api.openalex.org/works", params={
        "search": query, "per_page": str(n), "mailto": "agent@prime.local",
    }, timeout=timeout)
    out = []
    for w in (r.json().get("results") or [])[:n]:
        loc = (w.get("primary_location") or {})
        url = loc.get("landing_page_url") or w.get("doi") or (w.get("id") or "")
        year = w.get("publication_year") or ""
        abstract = _clean(_openalex_abstract(w.get("abstract_inverted_index")), 300)
        out.append({"title": _clean(w.get("display_name") or "", 160), "url": url,
                    "snippet": abstract, "siteName": f"[OpenAlex] cited by {w.get('cited_by_count', 0)}",
                    "date": str(year)})
    return [o for o in out if o["url"]]


# ---------------- Semantic Scholar ----------------

def _s2_sync(query: str, n: int, timeout: int) -> list[dict]:
    r = _get("https://api.semanticscholar.org/graph/v1/paper/search", params={
        "query": query, "limit": str(n), "fields": "title,abstract,year,url,citationCount,venue",
    }, timeout=timeout)
    out = []
    for p in (r.json().get("data") or [])[:n]:
        url = p.get("url") or f"https://www.semanticscholar.org/paper/{p.get('paperId', '')}"
        out.append({"title": _clean(p.get("title") or "", 160), "url": url,
                    "snippet": _clean(p.get("abstract") or "", 300),
                    "siteName": f"[SemanticScholar] {p.get('venue') or ''} | cited {p.get('citationCount', 0)}",
                    "date": str(p.get("year") or "")})
    return out


# ---------------- HackerNews (Algolia) ----------------

def _hn_sync(query: str, n: int, timeout: int) -> list[dict]:
    r = _get("https://hn.algolia.com/api/v1/search", params={
        "query": query, "hitsPerPage": str(n), "tags": "story",
    }, timeout=timeout)
    out = []
    for h in (r.json().get("hits") or [])[:n]:
        url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID', '')}"
        date = (h.get("created_at") or "")[:10]
        out.append({"title": _clean(h.get("title") or "", 160), "url": url,
                    "snippet": f"{h.get('points', 0)} points, {h.get('num_comments', 0)} comments",
                    "siteName": "[HackerNews] community", "date": date})
    return out


# ---------------- Reddit ----------------

def _reddit_sync(query: str, n: int, timeout: int) -> list[dict]:
    r = _get("https://www.reddit.com/search.json", params={
        "q": query, "limit": str(n), "sort": "relevance",
    }, timeout=timeout, ua=_UA)
    out = []
    for c in ((r.json().get("data") or {}).get("children") or [])[:n]:
        d = c.get("data") or {}
        permalink = d.get("permalink") or ""
        url = "https://www.reddit.com" + permalink if permalink else (d.get("url") or "")
        body = _clean(d.get("selftext") or d.get("title") or "", 280)
        out.append({"title": _clean(d.get("title") or "", 160), "url": url,
                    "snippet": body, "siteName": f"[Reddit] r/{d.get('subreddit', '')}",
                    "date": ""})
    return [o for o in out if o["url"]]


# ---------------- GDELT news ----------------

def _gdelt_sync(query: str, n: int, timeout: int) -> list[dict]:
    r = _get("https://api.gdeltproject.org/api/v2/doc/doc", params={
        "query": f"{query} sourcelang:english", "mode": "artlist",
        "maxrecords": str(n), "format": "json", "sort": "hybridrel",
    }, timeout=timeout)
    arts = r.json().get("articles") or []
    out = []
    for a in arts[:n]:
        date = (a.get("seendate") or "")
        date = f"{date[:4]}-{date[4:6]}-{date[6:8]}" if len(date) >= 8 else ""
        out.append({"title": _clean(a.get("title") or "", 160), "url": a.get("url") or "",
                    "snippet": "", "siteName": f"[GDELT] {a.get('domain', '')}",
                    "date": date})
    return [o for o in out if o["url"]]


# ---------------- Google News RSS ----------------

def _newsrss_sync(query: str, n: int, timeout: int) -> list[dict]:
    r = _get("https://news.google.com/rss/search", params={
        "q": query, "hl": "en-US", "gl": "US", "ceid": "US:en",
    }, timeout=timeout, accept="application/rss+xml,application/xml,text/xml")
    out = []
    for item in re.findall(r"<item>(.*?)</item>", r.text, re.S)[:n]:
        title = _clean(re.search(r"<title>(.*?)</title>", item, re.S).group(1), 160)
        link = re.search(r"<link>(.*?)</link>", item, re.S)
        src = re.search(r"<source[^>]*>(.*?)</source>", item, re.S)
        pub = re.search(r"<pubDate>(.*?)</pubDate>", item, re.S)
        out.append({"title": title, "url": (link.group(1).strip() if link else ""),
                    "snippet": "", "siteName": f"[NewsRSS] {src.group(1) if src else 'news'} (redirect link)",
                    "date": (pub.group(1)[:16] if pub else "")})
    return [o for o in out if o["url"]]


# ---------------- Security media RSS (threat-intel aggregated layer) ----------------

_SEC_FEEDS = (
    ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
    ("TheRecord", "https://therecord.media/feed"),
    ("TheHackersNews", "https://feeds.feedburner.com/TheHackersNews"),
)
_SEC_SITES = " OR ".join(f"site:{u.split('//', 1)[1].split('/')[0]}" for _, u in _SEC_FEEDS)


def _rss_items(xml: str, name: str, n: int) -> list[dict]:
    out = []
    for item in re.findall(r"<item>(.*?)</item>", xml, re.S)[:n]:
        m_title = re.search(r"<title>(.*?)</title>", item, re.S)
        m_link = re.search(r"<link>(.*?)</link>", item, re.S)
        if not (m_title and m_link):
            continue
        m_desc = re.search(r"<description>(.*?)</description>", item, re.S)
        m_pub = re.search(r"<pubDate>(.*?)</pubDate>", item, re.S)
        out.append({"title": _clean(m_title.group(1), 160),
                    "url": m_link.group(1).strip(),
                    "snippet": _clean(m_desc.group(1), 280) if m_desc else "",
                    "siteName": f"[SecRSS] {name}",
                    "date": (m_pub.group(1)[:16] if m_pub else "")})
    return out


def _secrss_sync(query: str, n: int, timeout: int) -> list[dict]:
    """Security-media feeds, keyword-filtered by query.

    Direct feeds first; Cloudflare blocks them in some regions, so fall back to
    Google News RSS with a site:-restricted query (same aggregated layer, more
    reliable transport)."""
    pool: list[dict] = []
    errors = []
    for name, feed_url in _SEC_FEEDS:
        try:
            r = _get(feed_url, timeout=timeout, ua=_UA_BROWSER,
                     accept="application/rss+xml,application/xml,text/xml")
            items = _rss_items(r.text, name, n * 3)
            if not items:
                errors.append(f"{name}: feed parsed 0 items")
            pool.extend(items)
        except Exception as e:
            errors.append(f"{name}: {str(e)[:60]}")
    if not pool and errors:
        try:
            r = _get("https://news.google.com/rss/search", params={
                "q": f"{query} {_SEC_SITES}", "hl": "en-US", "gl": "US", "ceid": "US:en",
            }, timeout=timeout, accept="application/rss+xml,application/xml,text/xml")
            pool = _rss_items(r.text, "GoogleNews", n * 3)
            if not pool:
                raise ValueError("fallback parsed 0 items (blocked or empty)")
            errors.append("direct feeds blocked, used GoogleNews fallback")
        except Exception as e:
            raise RuntimeError("; ".join(errors + [f"fallback: {str(e)[:80]}"]))
    words = [w.lower() for w in re.split(r"[^A-Za-z0-9]+", query) if len(w) >= 4]
    hits = [p for p in pool if any(w in f"{p['title']} {p['snippet']}".lower() for w in words)]
    return hits[:n] if hits else pool[:n]


# ---------------- Webz.io dark-web stream (paid, env-key gated) ----------------

def _webz_sync(query: str, n: int, timeout: int) -> list[dict]:
    key = os.environ.get("WEBZ_IO_API_KEY", "")
    if not key:
        raise RuntimeError("webz: WEBZ_IO_API_KEY not set (paid commercial feed)")
    r = _get("https://api.webz.io/io/api/v1/darkWeb/stream", params={
        "token": key, "q": query, "format": "json", "size": str(n * 2),
    }, timeout=timeout)
    posts = (r.json() or {}).get("posts") or []
    out = []
    for p in posts[:n]:
        thread = p.get("thread") or {}
        url = p.get("url") or thread.get("main_url") or ""
        out.append({"title": _clean(p.get("title") or "", 160), "url": url,
                    "snippet": _clean(p.get("text") or "", 300),
                    "siteName": f"[Webz.io] {thread.get('site_full') or 'darkweb'}",
                    "date": (p.get("published") or "")[:10]})
    return [o for o in out if o["url"]]


_BACKENDS = {
    "arxiv": _arxiv_sync, "openalex": _openalex_sync, "s2": _s2_sync,
    "hn": _hn_sync, "reddit": _reddit_sync, "gdelt": _gdelt_sync, "newsrss": _newsrss_sync,
    "secrss": _secrss_sync, "webz": _webz_sync,
}


def _format(results: list[dict], query: str, errors: list[str]) -> str:
    sections = []
    for i, r in enumerate(results):
        lines = [f"Result {i}: {r['title'] or 'Untitled'}", f"URL: {r['url']}"]
        if r.get("siteName"):
            lines.append(f"Source: {r['siteName']}")
        if r.get("date"):
            lines.append(f"Published: {r['date']}")
        if r.get("snippet"):
            lines.append(f"Snippet: {r['snippet']}")
        sections.append("\n".join(lines))
    body = "\n\n---\n\n".join(sections) if sections else f"No results for: {query}"
    if errors:
        body += "\n\n[backend errors] " + "; ".join(errors)
    return body


# ---------------- Telegram public channel ----------------

_TG_TIME_RE = re.compile(r'<time[^>]+datetime="([^"]+)"')
_TG_TEXT_RE = re.compile(r'<div[^>]*class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', re.S)
_TG_BLOCK_RE = re.compile(r'tgme_widget_message_wrap')


def _tg_read_sync(channel: str, limit: int, timeout: int) -> str:
    channel = channel.strip().strip("/").removeprefix("t.me/").removeprefix("https://t.me/")
    r = _get(f"https://t.me/s/{channel}", timeout=timeout, ua=_UA_BROWSER,
             accept="text/html")
    html = r.text
    blocks: list[str] = []
    starts = [m.start() for m in _TG_BLOCK_RE.finditer(html)]
    for i, s in enumerate(starts):
        chunk = html[s:starts[i + 1] if i + 1 < len(starts) else s + 20000]
        m = _TG_TEXT_RE.search(chunk)
        if not m:
            continue
        text = _clean(m.group(1), 600)
        t = _TG_TIME_RE.search(chunk)
        blocks.append(f"[{(t.group(1)[:16] if t else 'n/a')}] {text}")
    if not blocks:
        raise RuntimeError("no messages parsed (channel may be private or blocked)")
    return f"[t.me/s/{channel}] latest {min(limit, len(blocks))} of {len(blocks)} public posts\n\n" + \
        "\n\n".join(reversed(blocks[-limit:]))


# ---------------- same-domain crawl ----------------

_HREF_RE = re.compile(r'href="(https?://[^"#]+?)"')


def _crawl_links_sync(url: str, timeout: int) -> list[str]:
    r = _get(url, timeout=timeout, ua=_UA_BROWSER, accept="text/html")
    base_host = (urlparse(url).hostname or "").lower()
    links = []
    for h in _HREF_RE.findall(r.text):
        host = (urlparse(h).hostname or "").lower()
        if host == base_host and not re.search(r"\.(png|jpe?g|gif|svg|pdf|zip|css|js|ico|mp4)$", h, re.I):
            links.append(h.split("?")[0])
    seen, ordered = set(), []
    for l in links:
        if l not in seen and not l.rstrip("/").rstrip("=") .endswith(urlparse(url).path.rstrip("/")):
            seen.add(l)
            ordered.append(l)
    return ordered


async def _crawl(url: str, max_pages: int, timeout: int) -> str:
    try:
        from read_page import run as rp_run
    except ImportError:
        return "[crawl] read_page skill not installed"
    links = await asyncio.to_thread(_crawl_links_sync, url, timeout)
    ranked = sorted(links, key=lambda u: (_tier_for(u) != "P0", _tier_for(u) != "P1", links.index(u)))
    picked, seen_root = [], set()
    base_root = _root_domain(url)
    for l in ranked:
        rd = _root_domain(l)
        if rd == base_root and rd not in seen_root:
            seen_root.add(rd)
            picked.append(l)
        if len(picked) >= max_pages:
            break
    parts = [f"[crawl] base: {url} | same-domain links found: {len(links)} | reading top {len(picked)}"]
    for l in picked:
        text = await rp_run(l, max_output=3000, timeout=timeout)
        parts.append(f"\n===== {l} =====\n{text}")
    return "\n".join(parts)


# ---------------- main run ----------------

async def run(
    query: str = "",
    *,
    action: str = "search",
    backends: tuple[str, ...] | None = None,
    max_results: int | None = None,
    limit: int = 8,
    channel: str = "",
    url: str = "",
    max_pages: int = 3,
    max_output: int = 6000,
    timeout: int | None = None,
) -> str:
    timeout = timeout or _env_int("PRIME_SOURCE_REGISTRY_TIMEOUT", 20)

    if action == "status":
        names = list(_BACKENDS)
        return json.dumps({
            "backends": names,
            "default": list(DEFAULT_BACKENDS),
            "webz_key": bool(os.environ.get("WEBZ_IO_API_KEY")),
            "proxy_env": bool(_explicit_proxy()),
            "tg_config": str(_tg_config_path()),
        }, ensure_ascii=False, indent=1)

    if action == "tg":
        if not channel:
            return "[tg] channel required, e.g. run(action='tg', channel='durov')"
        try:
            text = await asyncio.to_thread(_tg_read_sync, channel, limit, timeout)
        except Exception as e:
            return f"[tg] FAILED for {channel}: {e}"
        if consume:
            consume(pages=1, chars=len(text))
        if log_event:
            log_event("tg_read", channel=channel, chars=len(text))
        return text[:max_output]

    if action == "crawl":
        if not url:
            return "[crawl] url required"
        out = await _crawl(url, max_pages, timeout)
        if log_event:
            log_event("crawl", url=url, pages=max_pages)
        return out[:max_output]

    # ---- search fan-out ----
    if not query:
        return "[source_registry] query required"
    names = backends or DEFAULT_BACKENDS
    fns = [(n, _BACKENDS[n]) for n in names if n in _BACKENDS]

    async def one(name, fn):
        try:
            res = await asyncio.to_thread(fn, query, _PER_BACKEND_LIMIT, timeout)
            return name, res, None
        except Exception as e:
            return name, [], f"{name}: {str(e)[:120]}"

    triples = await asyncio.gather(*(one(n, fn) for n, fn in fns))
    merged, errors, seen_root = [], [], set()
    order = {n: i for i, (n, _) in enumerate(fns)}
    flat = sorted(((order[n], r) for n, res, _ in triples for r in res), key=lambda t: t[0])
    for _, r in flat:
        rd = _root_domain(r.get("url") or "")
        if not rd or rd in seen_root:
            continue
        seen_root.add(rd)
        merged.append(r)
    errors = [e for _, _, e in triples if e]
    cap = max_results or _MERGE_LIMIT
    out = "[source-registry] " + "/".join(names) + f' results for query "{query}":\n\n' + \
        _format(merged[:cap], query, errors)
    if len(out) > max_output:
        out = out[:max_output] + "\n... [source-registry truncated]"
    if log_event:
        log_event("source_search", backends=list(names), results=len(merged), errors=errors)
    return out


def _tg_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "tg_channels.json"


def load_tg_channels() -> dict[str, list[str]]:
    p = _tg_config_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def match_tg_channels(topic: str) -> list[str]:
    matched = []
    for pattern, channels in load_tg_channels().items():
        try:
            if re.search(pattern, topic, re.I):
                matched.extend(channels)
        except re.error:
            continue
    seen, out = set(), []
    for c in matched:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out[:2]

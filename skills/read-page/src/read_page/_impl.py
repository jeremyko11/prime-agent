import asyncio
import hashlib
import os
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

try:
    from research_guard import consume, log_event, trim
except ImportError:
    consume = None
    log_event = None
    trim = None

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
# Wikimedia requires a descriptive UA with contact info; browser-style UAs get 403
_UA_WIKI = "prime-agent-readpage/1.0 (research skill; contact: agent@prime.local)"
_CACHE_TTL = 86400

_TIER_P0_DOMAINS = ("gov.cn", "gov", "edu.cn", "edu", "who.int", "imf.org", "worldbank.org", "un.org", "europa.eu",
                    "oecd.org", "iaea.org", "iea.org", "cern.ch", "unesco.org", "nato.int", "wto.org",
                    "iter.org", "nasa.gov", "noaa.gov", "usgs.gov", "ecb.europa.eu", "bis.org")
_TIER_P1_DOMAINS = ("wikipedia.org", "github.com", "arxiv.org", "nature.com", "science.org", "ieee.org", "acm.org",
                    "python.org", "nodejs.org", "react.dev", "mozilla.org", "w3.org", "reuters.com", "apnews.com",
                    "bbc.com", "nytimes.com", "cnbc.com", "ft.com", "economist.com", "infoq.cn", "36kr.com",
                    "cloud.tencent.com", "developer.mozilla.org", "coindesk.com", "theblock.co", "bloomberg.com",
                    "semanticscholar.org", "openalex.org", "ourworldindata.org", "pnas.org", "sciencedirect.com",
                    "springer.com", "springernature.com", "aps.org", "iop.org", "cell.com", "nejm.org",
                    "thelancet.com", "jstor.org", "ssrn.com", "doi.org", "nber.org", "rand.org", "csis.org",
                    "cfr.org", "chathamhouse.org",
                    "bleepingcomputer.com", "therecord.media", "thehackernews.com",
                    "krebsonsecurity.com", "darkreading.com", "securityweek.com")
_TIER_P2_DOMAINS = ("medium.com", "zhihu.com", "csdn.net", "juejin.cn", "stackoverflow.com", "segmentfault.com",
                    "cnblogs.com", "jianshu.com", "oschina.net", "twitter.com", "x.com", "reddit.com",
                    "weibo.com", "mp.weixin.qq.com", "toutiao.com",
                    "cointelegraph.com", "odaily.news", "techflowpost.com", "panews.com", "decrypt.co",
                    "news.ycombinator.com", "old.reddit.com", "lobste.rs", "substack.com", "t.me", "telegram.me")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _tier_for(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    for d in _TIER_P0_DOMAINS:
        if host == d or host.endswith("." + d):
            return "P0"
    for d in _TIER_P1_DOMAINS:
        if host == d or host.endswith("." + d):
            return "P1"
    for d in _TIER_P2_DOMAINS:
        if host == d or host.endswith("." + d):
            return "P2"
    return "P3"


def _cache_path(url: str) -> Path:
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()
    d = Path.home() / ".prime" / "agent" / "cache" / "read_page"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{key}.txt"


def _cache_get(url: str) -> str | None:
    p = _cache_path(url)
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > _CACHE_TTL:
        return None
    text = p.read_text(encoding="utf-8", errors="replace")
    return text or None


def _cache_put(url: str, text: str) -> None:
    try:
        _cache_path(url).write_text(text, encoding="utf-8")
    except Exception:
        pass


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "svg", "iframe", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in ("p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "blockquote", "pre"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0 and data.strip():
            self.parts.append(data)


def _html_to_text(html: str) -> str:
    ex = _TextExtractor()
    try:
        ex.feed(html)
    except Exception:
        pass
    text = "".join(ex.parts)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _jina_fetch_sync(url: str, timeout: int) -> str:
    errors = []
    for trust_env in (False, True):
        try:
            with httpx.Client(timeout=timeout, trust_env=trust_env) as client:
                r = client.get(f"https://r.jina.ai/{url}",
                               headers={"User-Agent": _UA, "X-Return-Format": "markdown"})
                r.raise_for_status()
                return r.text
        except Exception as e:
            errors.append(str(e))
    raise RuntimeError("; ".join(errors))


def _wiki_fetch_sync(url: str, timeout: int) -> str:
    m = re.match(r"https?://([a-z-]+)\.wikipedia\.org/wiki/([^#?]+)", url)
    if not m:
        raise ValueError("not a wikipedia article url")
    lang, title = m.group(1), unquote(m.group(2))
    with httpx.Client(timeout=timeout) as client:
        r = client.get(
            f"https://{lang}.wikipedia.org/w/api.php",
            params={"action": "query", "prop": "extracts", "explaintext": 1,
                    "titles": title, "format": "json", "redirects": 1},
            headers={"User-Agent": _UA_WIKI},
        )
        r.raise_for_status()
        pages = (r.json().get("query") or {}).get("pages") or {}
        parts = [p.get("extract") or "" for p in pages.values()]
        text = "\n\n".join(parts).strip()
    if not text:
        raise ValueError("empty extract")
    return text


def _direct_fetch_sync(url: str, timeout: int) -> str:
    errors = []
    headers = {"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
               "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
    for trust_env in (True, False):
        try:
            with httpx.Client(timeout=timeout, trust_env=trust_env, follow_redirects=True) as client:
                r = client.get(url, headers=headers)
                r.raise_for_status()
                ctype = r.headers.get("content-type", "")
                if "html" in ctype:
                    return _html_to_text(r.text)
                if "text/" in ctype or "json" in ctype or "xml" in ctype:
                    return r.text
                raise ValueError(f"unsupported content-type: {ctype or 'unknown'}")
        except Exception as e:
            errors.append(str(e))
    raise RuntimeError("; ".join(errors))


def _firecrawl_fetch_sync(url: str, timeout: int) -> str:
    key = os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        raise ValueError("FIRECRAWL_API_KEY not set")
    from firecrawl import FirecrawlApp
    app = FirecrawlApp(api_key=key)
    out = app.scrape_url(url, params={"formats": ["markdown"]})
    if isinstance(out, dict):
        return out.get("data", {}).get("markdown") or out.get("markdown") or ""
    return ""


async def run(
    url: str,
    *,
    max_output: int = 8192,
    head_keep: int = 4096,
    tail_keep: int = 1024,
    use_cache: bool = True,
    timeout: int | None = None,
) -> str:
    if not re.match(r"^https?://", url):
        url = "https://" + url.lstrip("/")
    timeout = timeout or _env_int("PRIME_AGENT_READPAGE_TIMEOUT", 40)

    host = urlparse(url).hostname or url
    tier = _tier_for(url)

    if use_cache:
        cached = _cache_get(url)
        if cached is not None:
            if consume:
                consume(pages=1, chars=len(cached))
            if log_event:
                log_event("read_page", url=url, backend="cache", chars=len(cached), tier=tier)
            return cached

    backends = []
    if re.match(r"^https?://[a-z-]+\.wikipedia\.org/wiki/", url):
        backends.append(("WikiAPI", _wiki_fetch_sync))
    backends.append(("Jina", _jina_fetch_sync))
    backends.append(("Direct", _direct_fetch_sync))
    backends.append(("Firecrawl", _firecrawl_fetch_sync))
    text, backend, errors = "", "none", []
    for name, fn in backends:
        try:
            text = await asyncio.to_thread(fn, url, timeout)
            if text and len(text.strip()) > 200:
                backend = name
                break
            errors.append(f"{name}: too short ({len(text or '')} chars)")
            text = ""
        except Exception as e:
            errors.append(f"{name}: {e}")
            continue

    if not text:
        out = f"[read_page] FAILED for {url}\nBackends tried: " + "; ".join(errors)
        if log_event:
            log_event("read_page_fail", url=url, errors=errors)
        return out

    if consume:
        consume(pages=1, chars=len(text))
    if log_event:
        log_event("read_page", url=url, backend=backend, chars=len(text), tier=tier)

    header = f"[{tier} | {host} | via {backend} | {len(text)} chars]\n\n"
    if trim:
        body = trim(text, max_chars=max_output, head_keep=head_keep, tail_keep=tail_keep)
        result = header + body
    else:
        result = (header + text)[:max_output]

    if use_cache:
        _cache_put(url, result)
    return result

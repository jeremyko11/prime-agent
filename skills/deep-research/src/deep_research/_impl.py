import asyncio
import os
import re
from urllib.parse import urlparse

try:
    import httpx
except ImportError:
    httpx = None

try:
    from research_guard import budget, check, consume, log_event, status, trim
except ImportError:
    budget = None
    check = None
    consume = None
    log_event = None
    status = None
    trim = None

try:
    from websearch import run as _ws_run
except ImportError:
    _ws_run = None

try:
    from read_page import run as _rp_run
    from read_page._impl import _tier_for
except ImportError:
    _rp_run = None

    def _tier_for(url: str) -> str:
        return "P3"

try:
    from source_registry import run as _sr_run
    from source_registry._impl import match_tg_channels as _match_tg
except ImportError:
    _sr_run = None

    def _match_tg(topic: str) -> list:
        return []

try:
    from mnemosyne import run as _mn_run
except ImportError:
    _mn_run = None

_URL_RE = re.compile(r"https?://[^\s)\]}>\"']+")
_CLAIM_RE = re.compile(r"[0-9０-９][0-9０-９,.%％百万亿万元美金倍]|[12][0-9]{3}\s*年|发布|官方|数据|显示|达到|增长|下降|超过|约占|相比")
_SENT_SPLIT = re.compile(r"(?<=[。！？.!?\n])\s*")

_CYCLE_ASPECTS = [
    ["{t}", "{t} 是什么 原理 机制", "{t} 最新 2026 数据"],
    ["{t} 实际案例 应用", "{t} 成本 价格 对比", "{t} 替代 竞品"],
    ["{t} 失败 案例 教训", "{t} 争议 质疑 风险", "{t} 局限 不足"],
]
# English aspect per cycle, fed to source-registry (arXiv/OpenAlex/S2/HN/GDELT...)
_CYCLE_EN_ASPECTS = ["{t}", "{t} commercialization economics cost", "{t} challenges criticism risks"]

# Threat-intel topics get the aggregated-layer backends (legal commercial feeds,
# no Tor): free security-media RSS always; Webz.io only when a key is configured.
_THREAT_RE = re.compile(
    r"ransomware|dark\s*web|暗网|勒索|数据泄露|data\s*breach|threat\s*intel|threat\s*actor"
    r"|APT\s?\d|CVE-\d|zero[\s-]?day|漏洞利用|黑市|black\s*market|威胁情报|credential\s*stuffing"
    r"|量子计算|quantum\s+(comput|crypt)|post[-\s]?quantum|后量子|抗量子"
    r"|密码学|加密体系|cryptography|Q-day|harvest.{0,20}decrypt", re.I)


def _threat_extra_backends() -> tuple[str, ...]:
    extra = ("secrss",)
    if os.environ.get("WEBZ_IO_API_KEY"):
        extra += ("webz",)
    return extra


def _domain(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def _root_domain(d: str) -> str:
    parts = d.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else d


def _extract_urls(search_results: list[str]) -> list[str]:
    seen, ordered = set(), []
    for block in search_results:
        for u in _URL_RE.findall(block):
            u = u.rstrip(".,;")
            rd = _root_domain(_domain(u))
            if rd in seen:
                continue
            seen.add(rd)
            ordered.append(u)
    return ordered


_TIER_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
# generic words that must never boost a same-named domain (e.g. topic "AI research" -> research.com)
_BOOST_STOPWORDS = frozenset({
    "news", "research", "market", "markets", "blog", "tech", "data", "cloud", "web",
    "app", "apps", "info", "shop", "site", "online", "world", "global", "china",
    "chinese", "english", "study", "report", "review", "guide", "best", "top",
    "analysis", "trends", "trend", "agent", "agents", "model", "models", "open",
})


def _topic_tokens(topic: str) -> frozenset:
    return frozenset(t for t in re.findall(r"[a-z][a-z0-9-]{4,}", topic.lower()) if t not in _BOOST_STOPWORDS)


def _rank_urls(urls: list[str], exclude_domains: frozenset = frozenset(), boost_tokens: frozenset = frozenset()) -> list[tuple[str, str]]:
    scored = []
    seen = set()
    for i, u in enumerate(urls):
        rd = _root_domain(_domain(u))
        if rd in exclude_domains or rd in seen:
            continue
        seen.add(rd)
        label = rd.split(".")[0]
        tier = "P0" if label in boost_tokens else _tier_for(u)
        scored.append((_TIER_ORDER[tier], i, u, tier))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [(u, tier) for _, _, u, tier in scored]


_CJK_RE = re.compile(r"[\u4e00-\u9fa5]")
_WIKI_UA = "prime-agent-deepresearch/1.0 (research skill; contact: agent@prime.local)"


async def _wiki_anchor(topic: str) -> str:
    """One P1 baseline page per topic via Wikipedia opensearch (zh for CJK topics, en otherwise)."""
    if httpx is None:
        return ""
    lang = "zh" if _CJK_RE.search(topic) else "en"
    search = re.sub(r"[0-9０-９]{4}\s*年?|\s{2,}", " ", topic).strip() or topic
    for attempt in (search, re.split(r"[\s,，、;；]", search)[0]):
        try:
            async with httpx.AsyncClient(timeout=20, trust_env=True, headers={"User-Agent": _WIKI_UA}) as c:
                r = await c.get(
                    f"https://{lang}.wikipedia.org/w/api.php",
                    params={"action": "opensearch", "search": attempt, "limit": 1, "format": "json"},
                )
                data = r.json()
                links = data[3] if len(data) > 3 else []
                if links:
                    return links[0]
        except Exception:
            continue
    return ""


_EN_TOPIC_CACHE: dict[str, str] = {}
_SEG_SPLIT = re.compile(r"[\s,，、;；:：]+|以及|对于|及其|的|之|与|和|及|或|对|在|是|了|把|将|被|让|而|并|且")


def _title_plausible(seg: str, title: str) -> bool:
    """Reject opensearch canonical titles unrelated to the segment (drift guard)."""
    if not title:
        return False
    return seg[:2] == title[:2] or seg in title or title in seg


_ARTICLE_TITLE_RE = re.compile(r"^(?:the|a|an)\s", re.I)


async def _langlinks_en(c, zh_title: str) -> str:
    """Query zh→en langlinks. zh redirects routinely land on traditional/synonym
    titles (就业→僱傭), so the guard targets the EN side instead: concept articles
    are plain noun phrases, while drift hits named works (冲击 → "The
    Adventurer's") whose titles start with an article. Parenthetical
    disambiguators ("Interstellar (film)") are stripped to the searchable head."""
    try:
        r = await c.get("https://zh.wikipedia.org/w/api.php", params={
            "action": "query", "prop": "langlinks", "titles": zh_title,
            "lllang": "en", "redirects": 1, "format": "json",
        })
        for p in ((r.json().get("query") or {}).get("pages") or {}).values():
            if p.get("missing") is not None:
                continue
            for ll in p.get("langlinks") or []:
                en = (ll.get("*") or "").strip()
                if not en or "disambiguation" in en.lower() or "消歧义" in en:
                    continue
                if _ARTICLE_TITLE_RE.match(en):
                    continue
                return re.sub(r"\s*\([^)]*\)$", "", en)
    except Exception:
        pass
    return ""


async def _seg_en(c, seg: str) -> str:
    """Translate one CJK segment: langlinks direct, then opensearch-normalized
    canonical title (segments >= 3 chars, title must look related)."""
    if seg in _EN_TOPIC_CACHE:
        return _EN_TOPIC_CACHE[seg]
    en = await _langlinks_en(c, seg)
    if not en and len(seg) >= 3:
        try:
            r = await c.get("https://zh.wikipedia.org/w/api.php", params={
                "action": "opensearch", "search": seg, "limit": 1, "format": "json"})
            data = r.json()
            if len(data) > 1 and data[1] and _title_plausible(seg, data[1][0]):
                en = await _langlinks_en(c, data[1][0])
        except Exception:
            pass
    # Chinese compounds are head-final (加密体系 = 加密 + 体系): when the full
    # segment has no entry, trim trailing chars to recover the distinctive
    # modifier (加密体系 → 加密 → Encryption).
    if not en and len(seg) >= 4:
        for head in [seg[:k] for k in range(len(seg) - 1, 1, -1)][:3]:
            en = await _langlinks_en(c, head)
            if en:
                break
    if en:
        _EN_TOPIC_CACHE[seg] = en
    return en


async def _en_topic(topic: str) -> str:
    """Deterministic zh→en topic translation via Wikipedia langlinks (no LLM, free).

    Fallback chain: whole phrase → first whitespace segment → CJK segmentation
    (structural-particle split; per-segment langlinks with opensearch
    normalization; latin segments kept as-is)."""
    if not _CJK_RE.search(topic):
        return topic
    if topic in _EN_TOPIC_CACHE:
        return _EN_TOPIC_CACHE[topic]
    if httpx is None:
        return topic
    search = re.sub(r"[0-9０-９]{4}\s*年?|\s{2,}", " ", topic).strip() or topic

    async with httpx.AsyncClient(timeout=15, trust_env=True, headers={"User-Agent": _WIKI_UA}) as c:
        tried = set()
        for zh_title in (search, re.split(r"[\s,，、;；]", search)[0]):
            if zh_title in tried:
                continue
            tried.add(zh_title)
            en = await _langlinks_en(c, zh_title)
            if en:
                _EN_TOPIC_CACHE[topic] = en
                return en
        segs, seen = [], set()
        for s in _SEG_SPLIT.split(search):
            if len(s) >= 2 and s not in seen:
                seen.add(s)
                segs.append(s)
        parts = []
        for s in segs[:5]:
            en = s if not _CJK_RE.search(s) else await _seg_en(c, s)
            if en and en not in parts:
                parts.append(en)
        if parts:
            joined = " ".join(parts)
            _EN_TOPIC_CACHE[topic] = joined
            return joined
    _EN_TOPIC_CACHE[topic] = topic
    return topic


def _extract_claims(corpus: dict[str, str]) -> list[dict]:
    per_domain_terms = {}
    raw_claims = []
    for url, text in corpus.items():
        dom = _root_domain(_domain(url))
        sents = [s.strip() for s in _SENT_SPLIT.split(text) if 15 <= len(s.strip()) <= 220]
        terms = set(re.findall(r"[\u4e00-\u9fa5]{2,6}|[A-Za-z][A-Za-z0-9-]{3,}", text.lower()))
        per_domain_terms[dom] = per_domain_terms.get(dom, set()) | terms
        for s in sents:
            if _CLAIM_RE.search(s):
                raw_claims.append({"text": s, "domain": dom, "url": url})
    for c in raw_claims[:60]:
        c_terms = set(re.findall(r"[\u4e00-\u9fa5]{2,6}|[A-Za-z][A-Za-z0-9-]{3,}", c["text"].lower()))
        c_terms &= {t for t in c_terms if len(t) >= 3}
        supporting = [d for d, ts in per_domain_terms.items() if d != c["domain"] and len(c_terms & ts) >= 3]
        c["support_domains"] = supporting
        c["confidence"] = "CONFIRMED" if len(supporting) >= 2 else ("MAJORITY" if len(supporting) == 1 else "SINGLE-SOURCE")
    dedup, seen_texts = [], set()
    for c in raw_claims[:60]:
        key = c["text"][:60]
        if key not in seen_texts:
            seen_texts.add(key)
            dedup.append(c)
    order = {"CONFIRMED": 0, "MAJORITY": 1, "SINGLE-SOURCE": 2}
    return sorted(dedup, key=lambda c: order[c["confidence"]])[:12]


async def _mnemosyne_retain(summary: str, topic: str) -> str:
    if _mn_run is None:
        return "mnemosyne not installed"
    for kwargs in ({"content": summary}, {"text": summary}, {"memory": summary}):
        try:
            out = await _mn_run(action="retain", **kwargs)
            return f"retained: {str(out)[:80]}"
        except TypeError:
            continue
        except Exception as e:
            return f"retain failed: {e}"
    return "retain failed: no accepted kwarg"


async def run(
    topic: str,
    *,
    max_cycles: int = 3,
    queries_per_cycle: int = 3,
    pages_per_cycle: int = 2,
    adversarial: bool = True,
    retain: bool = True,
    max_output: int = 14000,
) -> str:
    if _ws_run is None:
        return "[deep_research] websearch skill not installed in this kernel."
    if log_event:
        log_event("research_start", topic=topic, max_cycles=max_cycles)

    corpus: dict[str, str] = {}
    all_sources: list[str] = []
    cycle_notes = []
    cycles_run = 0
    boost = _topic_tokens(topic)

    en_topic = await _en_topic(topic) if _sr_run else topic
    en_ok = bool(_sr_run and en_topic and not _CJK_RE.search(en_topic))
    if en_ok and log_event:
        log_event("research_en_topic", topic=topic, en=en_topic)

    for ci in range(min(max_cycles, 3)):
        ok, reason = check(need_searches=queries_per_cycle, need_pages=pages_per_cycle)
        if not ok:
            cycle_notes.append(f"cycle {ci + 1}: stopped ({reason})")
            if log_event:
                log_event("research_budget_stop", cycle=ci + 1, reason=reason)
            break

        templates = _CYCLE_ASPECTS[ci % len(_CYCLE_ASPECTS)][:queries_per_cycle]
        queries = [t.format(t=topic) for t in templates]
        en_q = _CYCLE_EN_ASPECTS[ci % len(_CYCLE_EN_ASPECTS)].format(t=en_topic) if en_ok else ""
        is_adv_cycle = ci == 2

        search_tasks = [_ws_run(q, max_output=3000, timeout=40) for q in queries]
        threat_extra = _THREAT_RE.search(topic) and _sr_run is not None
        if threat_extra:
            tb = _threat_extra_backends()
            if en_q:
                search_tasks.append(_sr_run(en_q, backends=tb, max_output=3000, timeout=45))
            else:
                search_tasks.append(_sr_run(topic, backends=tb, max_output=3000, timeout=45))
            if log_event:
                log_event("research_threat_intel", backends=list(tb))
        if en_q and not threat_extra:
            search_tasks.append(_sr_run(en_q, max_output=3500, timeout=45))
        try:
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
        except Exception as e:
            cycle_notes.append(f"cycle {ci + 1}: search error {e}")
            continue
        results = [r if isinstance(r, str) else f"search error: {r}" for r in results]
        if consume:
            consume(searches=len(search_tasks))
        if log_event:
            log_event("research_search", cycle=ci + 1,
                      queries=queries + ([f"[EN] {en_q}"] if en_q else []))

        candidates = _extract_urls(results)
        if ci == 0:
            anchor = await _wiki_anchor(topic)
            if anchor:
                anchor_rd = _root_domain(_domain(anchor))
                candidates = [anchor] + [c for c in candidates
                                         if _root_domain(_domain(c)) != anchor_rd]
        ranked = _rank_urls(candidates,
                            exclude_domains=frozenset(_root_domain(_domain(u)) for u in corpus),
                            boost_tokens=boost)
        urls = [u for u, _ in ranked[:pages_per_cycle]]
        if log_event:
            log_event("research_select_pages", cycle=ci + 1, chosen=ranked[:pages_per_cycle])
        pages = {}
        for u in urls:
            ok, reason = check(need_pages=1)
            if not ok:
                break
            try:
                text = await _rp_run(u, max_output=6000, timeout=40)
                if "FAILED" not in text[:120]:
                    pages[u] = text
            except Exception as e:
                if log_event:
                    log_event("research_read_fail", url=u, error=str(e))
        corpus.update(pages)
        all_sources.extend(u for u in urls if u not in all_sources)

        if ci == 1 and _sr_run:
            for ch in _match_tg(topic):
                ok_tg, _ = check(need_pages=1)
                if not ok_tg:
                    break
                try:
                    tg = await _sr_run(action="tg", channel=ch, limit=8, max_output=4000, timeout=30)
                    if "FAILED" not in tg[:100]:
                        key = f"https://t.me/s/{ch}"
                        corpus[key] = tg
                        if key not in all_sources:
                            all_sources.append(key)
                        if log_event:
                            log_event("research_tg", channel=ch, chars=len(tg))
                except Exception as e:
                    if log_event:
                        log_event("research_tg_fail", channel=ch, error=str(e))

        cycles_run += 1
        if log_event:
            log_event("research_read", cycle=ci + 1, pages=list(pages))

    claims = _extract_claims(corpus) if corpus else []

    confirmed = [c for c in claims if c["confidence"] == "CONFIRMED"]
    majority = [c for c in claims if c["confidence"] == "MAJORITY"]
    single = [c for c in claims if c["confidence"] == "SINGLE-SOURCE"]

    adversarial_note = "skipped"
    if adversarial:
        adv_q = [f"{topic} 失败 案例", f"{topic} 争议 风险 质疑"]
        ok, reason = check(need_searches=len(adv_q))
        if ok:
            adv_results = await asyncio.gather(*[_ws_run(q, max_output=2500, timeout=40) for q in adv_q],
                                               return_exceptions=True)
            adv_results = [r if isinstance(r, str) else f"error: {r}" for r in adv_results]
            if consume:
                consume(searches=len(adv_q))
            adversarial_note = "\n\n".join(f"--- [{q}]\n{r}" for q, r in zip(adv_q, adv_results))
            if log_event:
                log_event("research_adversarial", queries=adv_q)
        else:
            adversarial_note = f"skipped ({reason})"

    stats = status() if status else ""
    b = budget() if budget else {}
    summary_line = f"topic={topic}; cycles_run={cycles_run}; claims={len(claims)} (C{len(confirmed)}/M{len(majority)}/S{len(single)})"

    retain_note = ""
    if retain:
        retain_note = await _mnemosyne_retain(f"deep_research[{topic}]: " + summary_line, topic)

    def fmt_claims(cs):
        return "\n".join(f"- [{c['confidence']}] {c['text'][:200]} (src: {_domain(c['url'])})" for c in cs) or "(无)"

    report = "\n".join([
        f"# Deep Research: {topic}",
        "",
        "## 执行摘要",
        f"共检索 {b.get('usage', {}).get('searches', '?')} 次、精读 {len(corpus)} 页；"
        f"抽取关键主张 {len(claims)} 条，其中跨域验证 {len(confirmed) + len(majority)} 条。",
        (f"英文检索词（Wikipedia langlinks）: {en_topic}" if en_ok else ""),
        "",
        "## 关键发现（跨域验证）",
        fmt_claims(confirmed + majority),
        "",
        "## 单一来源（需人工复核）",
        fmt_claims(single),
        "",
        "## 反证与风险搜索",
        str(adversarial_note)[:3000],
        "",
        "## 来源",
        "\n".join(f"- {u}" for u in all_sources[:15]) or "(无)",
        "",
        "## 运行统计",
        stats,
    ])
    if cycle_notes:
        report += "\n\n## 中断记录\n" + "\n".join(cycle_notes)
    if retain_note:
        report += f"\n\nmemory: {retain_note}"
    if log_event:
        log_event("research_done", topic=topic, claims=len(claims), pages=len(corpus))

    if trim:
        report = trim(report, max_chars=max_output, head_keep=max_output - 2500, tail_keep=2500)
    else:
        report = report[:max_output]
    return report

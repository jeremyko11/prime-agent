import asyncio

try:
    from research_guard import check, consume, log_event, trim
except ImportError:
    check = None
    consume = None
    log_event = None
    trim = None

try:
    from websearch import run as _ws_run
except ImportError:
    _ws_run = None

try:
    from read_page import run as _rp_run
except ImportError:
    _rp_run = None

_NEGATIVE_MARKERS = ("失败", "争议", "风险", "质疑", "批评", "局限", "陷阱", "坑", "翻车",
                     "debunk", "fail", "risk", "controvers", "critic", "limitation", "scam", "overrated")


def _adversarial_queries(topic: str) -> list[str]:
    return [
        topic,
        f"{topic} 最新 数据 2026",
        f"{topic} 失败 案例 教训",
        f"{topic} 争议 质疑 风险",
        f"{topic} debunked limitations",
    ]


def _is_negative(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in _NEGATIVE_MARKERS)


async def _search_one(query: str, idx: int, max_output_per: int, timeout: int) -> str:
    if idx > 0:
        await asyncio.sleep(0.5 * idx)
    try:
        out = await _ws_run(query, max_output=max_output_per, timeout=timeout)
    except Exception as e:
        out = f"[parallel_explore] query failed: {query} ({e})"
    if trim:
        out = trim(out, max_chars=max_output_per, head_keep=max_output_per - 1024, tail_keep=1024)
    return out


async def _read_one(url: str, idx: int, max_output_per: int, timeout: int) -> str:
    if idx > 0:
        await asyncio.sleep(0.3 * idx)
    try:
        out = await _rp_run(url, max_output=max_output_per, timeout=timeout)
    except Exception as e:
        out = f"[parallel_explore] read failed: {url} ({e})"
    return out


async def _gather_ordered(tasks_creator, items, workers, max_output_per, timeout, kind):
    sem = asyncio.Semaphore(workers)
    done: list[str] = [""] * len(items)

    async def worker(i, item):
        ok, reason = True, ""
        if check:
            need = 1 if kind == "search" else 0
            need_pages = 0 if kind == "search" else 1
            ok, reason = check(need_searches=need, need_pages=need_pages)
            if not ok:
                done[i] = f"[budget-stop] {item}: {reason}"
                return
        async with sem:
            done[i] = await tasks_creator(item, i, max_output_per, timeout)
        if consume:
            if kind == "search":
                consume(searches=1)
            else:
                consume(chars=len(done[i]))
        if log_event:
            log_event(f"parallel_{kind}", target=item, chars=len(done[i]))

    await asyncio.gather(*(worker(i, it) for i, it in enumerate(items)))
    return done


async def run(
    queries: list[str] | None = None,
    urls: list[str] | None = None,
    topic: str | None = None,
    adversarial: bool = False,
    workers: int = 3,
    max_output_per: int = 4096,
    timeout: int = 40,
) -> str:
    if topic and adversarial:
        queries = _adversarial_queries(topic)
        if log_event:
            log_event("adversarial_explore", topic=topic, n_queries=len(queries))

    if queries:
        if _ws_run is None:
            return "[parallel_explore] websearch skill not installed in this kernel."
        results = await _gather_ordered(_search_one, queries, workers, max_output_per, timeout, "search")
        if not (topic and adversarial):
            parts = []
            for q, r in zip(queries, results):
                parts.append(f"=== Query: {q} ===\n{r}")
            return "\n\n".join(parts)

        pro, contra = [], []
        for q, r in zip(queries, results):
            block = f"--- [{q}]\n{r}"
            (contra if _is_negative(q) else pro).append(block)
        out = ["### 支持证据面", "\n\n".join(pro) if pro else "(无结果)",
               "\n\n### 反证/风险面", "\n\n".join(contra) if contra else "(无结果)"]
        return "\n\n".join(out)

    if urls:
        if _rp_run is None:
            return "[parallel_explore] read_page skill not installed in this kernel."
        results = await _gather_ordered(_read_one, urls, max(1, workers + 1), max_output_per, timeout, "read")
        parts = []
        for u, r in zip(urls, results):
            parts.append(f"=== Page: {u} ===\n{r}")
        return "\n\n".join(parts)

    return "[parallel_explore] provide queries=[...], urls=[...], or topic=... with adversarial=True."

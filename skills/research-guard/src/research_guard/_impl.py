import json
import os
import sys
import threading
import time
from pathlib import Path

_LOCK = threading.Lock()
_T0 = time.monotonic()
_USAGE = {"searches": 0, "pages": 0, "chars": 0}
_RUN_ID: str | None = None
_LOG_PATH: Path | None = None


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def caps() -> dict:
    return {
        "pages": _env_int("PRIME_RESEARCH_MAX_PAGES", 20),
        "searches": _env_int("PRIME_RESEARCH_MAX_SEARCHES", 15),
        "chars": _env_int("PRIME_RESEARCH_MAX_CHARS", 200_000),
        "runtime_sec": _env_int("PRIME_RESEARCH_MAX_RUNTIME", 900),
    }


def _log_file() -> Path:
    global _RUN_ID, _LOG_PATH
    if _LOG_PATH is None:
        _RUN_ID = os.environ.get("PRIME_RESEARCH_RUN_ID") or time.strftime("%Y%m%d-%H%M%S")
        d = Path.home() / ".prime" / "agent" / "research"
        d.mkdir(parents=True, exist_ok=True)
        _LOG_PATH = d / f"run-{_RUN_ID}.jsonl"
    return _LOG_PATH


def log_event(event: str, **data) -> None:
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "run": _RUN_ID or "", "event": event}
    entry.update(data)
    line = json.dumps(entry, ensure_ascii=False, default=str)
    with _LOCK:
        try:
            with open(_log_file(), "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            print(f"[research_guard] log write failed: {e}", file=sys.stderr)


def trim(text: str | None, max_chars: int = 8192, head_keep: int = 4096, tail_keep: int = 1024) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    total = len(text)
    head_keep = min(head_keep, max_chars)
    tail_keep = min(tail_keep, max_chars - head_keep)
    marker = f"\n... [trimmed: {total} chars total, kept head {head_keep} + tail {tail_keep}] ...\n"
    return text[:head_keep] + marker + text[total - tail_keep:]


def budget() -> dict:
    c = caps()
    return {
        "usage": dict(_USAGE),
        "caps": c,
        "elapsed_sec": round(time.monotonic() - _T0, 1),
    }


def check(need_pages: int = 0, need_searches: int = 0, need_chars: int = 0) -> tuple[bool, str]:
    b = budget()
    u, c = b["usage"], b["caps"]
    if u["searches"] + need_searches > c["searches"]:
        return False, f"search cap reached ({u['searches']}/{c['searches']})"
    if u["pages"] + need_pages > c["pages"]:
        return False, f"page cap reached ({u['pages']}/{c['pages']})"
    if u["chars"] + need_chars > c["chars"]:
        return False, f"char cap reached ({u['chars']}/{c['chars']})"
    if b["elapsed_sec"] > c["runtime_sec"]:
        return False, f"runtime cap reached ({b['elapsed_sec']}s/{c['runtime_sec']}s)"
    return True, ""


def consume(searches: int = 0, pages: int = 0, chars: int = 0) -> None:
    with _LOCK:
        _USAGE["searches"] += searches
        _USAGE["pages"] += pages
        _USAGE["chars"] += chars


def reset() -> str:
    global _T0, _RUN_ID, _LOG_PATH
    with _LOCK:
        _USAGE["searches"] = _USAGE["pages"] = _USAGE["chars"] = 0
        _T0 = time.monotonic()
        _RUN_ID = None
        _LOG_PATH = None
    log_event("budget_reset")
    return "budget reset; new run log will start on next event"


def status() -> str:
    b = budget()
    u, c = b["usage"], b["caps"]
    log_event("status", **u, elapsed_sec=b["elapsed_sec"])
    lines = [
        "Research budget:",
        f"  searches: {u['searches']}/{c['searches']}",
        f"  pages:    {u['pages']}/{c['pages']}",
        f"  chars:    {u['chars']}/{c['chars']}",
        f"  runtime:  {b['elapsed_sec']}s/{c['runtime_sec']}s",
    ]
    return "\n".join(lines)


async def run(action: str = "status", **kw) -> str:
    if action == "status":
        return status()
    if action == "trim":
        return trim(
            kw.get("text", ""),
            int(kw.get("max_chars", 8192)),
            int(kw.get("head_keep", 4096)),
            int(kw.get("tail_keep", 1024)),
        )
    if action == "log":
        log_event(str(kw.get("event", "custom")), **(kw.get("data") or {}))
        return "logged"
    if action == "budget":
        return json.dumps(budget(), ensure_ascii=False)
    if action == "reset":
        return reset()
    return f"Unknown action: {action}. Use status | trim | log | budget | reset."

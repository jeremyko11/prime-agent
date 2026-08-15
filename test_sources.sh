#!/usr/bin/env bash
KV=$HOME/.prime/agent/kernel-venv
"$KV/bin/python" - <<'EOF'
import asyncio, time

async def main():
    from source_registry._impl import (
        _BACKENDS, _tg_read_sync, _get
    )
    from deep_research._impl import _en_topic
    import concurrent.futures as cf

    print("=== per-backend health ===")
    loop = asyncio.get_event_loop()
    q = "fusion energy commercialization"
    for name, fn in _BACKENDS.items():
        t0 = time.monotonic()
        try:
            res = await loop.run_in_executor(None, fn, q, 3, 15)
            urls = [r.get("url", "")[:60] for r in res[:2]]
            print(f"OK   {name:8s} {len(res)} results {time.monotonic()-t0:.1f}s | {urls}")
        except Exception as e:
            print(f"FAIL {name:8s} {time.monotonic()-t0:.1f}s | {str(e)[:110]}")

    print("\n=== en_topic (langlinks) ===")
    for t in ("可控核聚变 商业化", "量子计算", "not-cjk-topic"):
        en = await _en_topic(t)
        print(f"  {t} -> {en}")

    print("\n=== telegram public channel ===")
    try:
        tg = await loop.run_in_executor(None, _tg_read_sync, "durov", 3, 15)
        print(tg[:400])
    except Exception as e:
        print("tg FAIL:", str(e)[:150])

asyncio.run(main())
EOF

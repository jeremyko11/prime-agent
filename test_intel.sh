#!/usr/bin/env bash
# Test threat-intel aggregated-layer backends (secrss + webz gating + topic detection)
KV=$HOME/.prime/agent/kernel-venv
"$KV/bin/python" - <<'EOF'
import asyncio, time

async def main():
    from source_registry._impl import _BACKENDS, _secrss_sync, _webz_sync
    from deep_research._impl import _THREAT_RE, _threat_extra_backends

    print("=== secrss backend (BleepingComputer + The Record) ===")
    for q in ("ransomware attack", "non-matching-xyzzy-query"):
        t0 = time.time()
        try:
            res = await asyncio.to_thread(_secrss_sync, q, 4, 25)
            print(f"  query={q!r}: {len(res)} results in {time.time()-t0:.1f}s")
            for r in res[:2]:
                print(f"    - [{r['siteName']}] {r['title'][:70]} | {r['date']}")
                print(f"      {r['url'][:90]}")
        except Exception as e:
            print(f"  query={q!r}: FAILED {e}")

    print("\n=== webz backend without key (graceful gating) ===")
    import os
    os.environ.pop("WEBZ_IO_API_KEY", None)
    try:
        await asyncio.to_thread(_webz_sync, "test", 4, 15)
        print("  ERROR: should have raised without key")
    except RuntimeError as e:
        print(f"  OK raises clean config error: {e}")

    print("\n=== threat topic detection ===")
    for t in ("勒索软件 攻击趋势", "暗网 数据泄露 事件", "RaaS ransomware 2026",
              "可控核聚变 商业化", "CVE-2026 zero-day exploit"):
        hit = bool(_THREAT_RE.search(t))
        print(f"  {t!r}: threat={hit}")

    print("\n=== extra backends resolution ===")
    print(f"  no key  -> {_threat_extra_backends()}")
    os.environ["WEBZ_IO_API_KEY"] = "dummy"
    print(f"  with key -> {_threat_extra_backends()}")

    print("\n=== fan-out with secrss+webz (webz key dummy -> remote auth error tolerated) ===")
    from source_registry import run as sr
    out = await sr("ransomware gangs 2026", backends=("secrss", "webz"), max_output=1800)
    print(out[:1400])

asyncio.run(main())
EOF

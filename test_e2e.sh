#!/usr/bin/env bash
KV=$HOME/.prime/agent/kernel-venv
$KV/bin/python - <<'EOF'
import asyncio, time

async def main():
    from deep_research import run as dr
    from research_guard import run as guard, budget

    print(await guard(action="reset"))
    t0 = time.monotonic()
    try:
        report = await asyncio.wait_for(
            dr("Polymarket 预测市场 2026", max_cycles=2, queries_per_cycle=2,
               pages_per_cycle=2, adversarial=True, retain=False, max_output=9000),
            timeout=480,
        )
        print(report)
    except asyncio.TimeoutError:
        print("[E2E] TIMEOUT after 480s")
    print(f"\n[E2E] elapsed: {time.monotonic() - t0:.0f}s")
    print("[E2E] budget:", budget())

asyncio.run(main())
EOF

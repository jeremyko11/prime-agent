#!/usr/bin/env bash
KV=$HOME/.prime/agent/kernel-venv
$KV/bin/python - <<'EOF'
import asyncio, time

async def main():
    from parallel_explore import run as pe
    from research_guard import run as guard

    await guard(action="reset")

    print("=== T1 parallel search (3 queries) ===")
    t0 = time.monotonic()
    out = await pe(queries=["DeepSeek V4 发布", "预测市场 Kalshi Polymarket 对比", "agent harness 插件架构"],
                   workers=3, max_output_per=1200, timeout=45)
    print(f"[elapsed {time.monotonic()-t0:.0f}s]")
    print(out[:600].replace("\n", " | "))
    print(" ... [truncated]")

    print("\n=== T2 parallel read (2 urls) ===")
    t0 = time.monotonic()
    out = await pe(urls=["https://en.wikipedia.org/wiki/Polymarket",
                         "https://arxiv.org/abs/1706.03762"],
                   max_output_per=800, timeout=45)
    print(f"[elapsed {time.monotonic()-t0:.0f}s]")
    print(out[:400].replace("\n", " | "))
    print(" ... [truncated]")

    print("\n=== T3 adversarial mode ===")
    out = await pe(topic="Polymarket", adversarial=True, max_output_per=800, timeout=45)
    print(out[:400].replace("\n", " | "))

    print("\n=== budget after parallel tests ===")
    print(await guard(action="status"))

asyncio.run(main())
EOF

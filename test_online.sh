#!/usr/bin/env bash
KV=$HOME/.prime/agent/kernel-venv
"$KV/bin/python" - <<'EOF'
import asyncio

async def main():
    from read_page import run as rp
    from websearch import run as ws
    from parallel_explore import run as pe
    from deep_research import run as dr

    print("=== T1 read_page arxiv ===")
    try:
        out = await rp("https://arxiv.org/abs/1706.03762", use_cache=False, timeout=30)
        print(out[:300].replace("\n", " | "))
    except Exception as e:
        print("ERR", e)

    print("\n=== T2 read_page wikipedia ===")
    try:
        out = await rp("https://en.wikipedia.org/wiki/DeepSeek", use_cache=False, timeout=40)
        print(out[:300].replace("\n", " | "))
    except Exception as e:
        print("ERR", e)

    print("\n=== T3 websearch smoke ===")
    try:
        out = await ws("deepseek harness plugin", max_output=1500, timeout=30)
        print(out[:250].replace("\n", " | "))
    except Exception as e:
        print("ERR", e)

asyncio.run(main())
EOF

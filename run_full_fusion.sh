#!/usr/bin/env bash
KV=$HOME/.prime/agent/kernel-venv
mkdir -p /root/work/research_out
$KV/bin/python - <<'EOF'
import asyncio, time, json

async def main():
    from deep_research import run as dr
    from research_guard import run as guard

    await guard(action="reset")
    t0 = time.monotonic()
    try:
        report = await asyncio.wait_for(
            dr("可控核聚变 商业化", max_cycles=3, queries_per_cycle=3,
               pages_per_cycle=3, adversarial=True, retain=False, max_output=16000),
            timeout=850,
        )
    except asyncio.TimeoutError:
        report = "[E2E] TIMEOUT after 850s"
    print(f"[elapsed {time.monotonic()-t0:.0f}s]")
    with open("/root/work/research_out/fusion_full.md", "w", encoding="utf-8") as f:
        f.write(report)
    print(report[:1500])
    print("\n... [saved to /root/work/research_out/fusion_full.md]")

asyncio.run(main())
EOF
echo "--- copy to windows ---"
cp /root/work/research_out/fusion_full.md /mnt/d/A/PPT/prime_upgrade/research_out_fusion_full.md && echo copied
LATEST=$(ls -t /root/.prime/agent/research/*.jsonl | head -1)
cp "$LATEST" /mnt/d/A/PPT/prime_upgrade/research_out_run_log.jsonl && echo "log copied: $LATEST"

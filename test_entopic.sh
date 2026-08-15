#!/usr/bin/env bash
bash /mnt/d/A/PPT/prime_upgrade/deploy.sh 2>&1 | grep -cE '^OK'
echo "=== _en_topic fallback chain test ==="
~/.prime/agent/kernel-venv/bin/python - <<'EOF'
import asyncio, time

async def main():
    from deep_research._impl import _en_topic, _EN_TOPIC_CACHE, _SEG_SPLIT

    cases = [
        ("量子计算对加密体系的冲击", "segmented fallback (the fixed gap)"),
        ("可控核聚变 商业化", "regression: first-segment path"),
        ("量子计算", "regression: whole-phrase hit"),
        ("后量子密码迁移 NIST", "mixed CJK + latin segment"),
        ("固态电池 量产进展", "regression: first segment"),
        ("人工智能对就业市场的重构效应", "synonym/traditional redirect survives guard"),
        ("固态电池对新能源汽车产业的影响", "head-final trim fallback"),
    ]
    for topic, note in cases:
        t0 = time.time()
        en = await _en_topic(topic)
        dt = time.time() - t0
        flag = "OK " if en and not any('\u4e00' <= ch <= '\u9fa5' for ch in en.split(" NIST")[0] if '\u4e00' <= ch <= '\u9fa5') else "RAW"
        print(f"  {topic} -> {en!r}  [{dt:.1f}s] {flag} ({note})")

    print("\n=== segmentation preview ===")
    for t in ("量子计算对加密体系的冲击", "固态电池对新能源汽车产业的影响"):
        segs = [s for s in _SEG_SPLIT.split(t) if len(s) >= 2]
        print(f"  {t} => {segs}")

asyncio.run(main())
EOF

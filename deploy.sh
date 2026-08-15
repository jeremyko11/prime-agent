#!/usr/bin/env bash
set -uo pipefail
SKILLS_SRC=/mnt/d/A/PPT/prime_upgrade/skills
DEST=$HOME/.prime/agent/skills
KV=$HOME/.prime/agent/kernel-venv
MV=/opt/prime-agent/prime-agent-main/.venv

SKILLS=(research-guard read-page parallel-explore deep-research source-registry)

echo "== 1. copy skills =="
for s in "${SKILLS[@]}"; do
  rm -rf "$DEST/$s"
  cp -r "$SKILLS_SRC/$s" "$DEST/$s" && echo "copied $s"
done

echo "== 2. pip install -e (kernel-venv) =="
for s in "${SKILLS[@]}"; do
  "$KV/bin/pip" install -e "$DEST/$s" -q 2>&1 | tail -1
done

echo "== 3. pip install -e (main .venv, via uv) =="
for s in "${SKILLS[@]}"; do
  uv pip install -e "$DEST/$s" --python "$MV/bin/python" -q 2>&1 | tail -1
done

echo "== 4. import smoke test =="
"$KV/bin/python" - <<'EOF'
import importlib
for m in ("research_guard", "read_page", "parallel_explore", "deep_research", "source_registry"):
    try:
        mod = importlib.import_module(m)
        has_run = hasattr(mod, "run")
        print(f"OK {m} (run={has_run})")
    except Exception as e:
        print(f"FAIL {m}: {e}")
EOF

echo "== 5. offline function test =="
"$KV/bin/python" - <<'EOF'
import asyncio
from research_guard import run as guard

async def main():
    print(await guard(action="status"))
    t = "x" * 20000
    out = await guard(action="trim", text=t, max_chars=8192, head_keep=4096, tail_keep=1024)
    print("trim result len:", len(out), "| head ok:", out.startswith("xxx"), "| marker:", "trimmed" in out)

asyncio.run(main())
EOF

echo "== deploy done =="

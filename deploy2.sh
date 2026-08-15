#!/usr/bin/env bash
set -uo pipefail
DEST=$HOME/.prime/agent/skills
MV=/opt/prime-agent/prime-agent-main/.venv
SKILLS=(research-guard read-page parallel-explore deep-research)

echo "== main .venv install via uv =="
for s in "${SKILLS[@]}"; do
  if [ -x "$MV/bin/pip" ]; then
    "$MV/bin/pip" install -e "$DEST/$s" -q 2>&1 | tail -1
  elif command -v uv >/dev/null 2>&1; then
    uv pip install -e "$DEST/$s" --python "$MV/bin/python" -q 2>&1 | tail -1
  else
    echo "no pip/uv available"
    break
  fi
done

echo "== verify main venv imports =="
"$MV/bin/python" - <<'EOF'
import importlib
for m in ("research_guard", "read_page", "parallel_explore", "deep_research"):
    try:
        importlib.import_module(m)
        print(f"OK {m}")
    except Exception as e:
        print(f"FAIL {m}: {type(e).__name__}: {e}")
EOF

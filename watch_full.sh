#!/usr/bin/env bash
LATEST=$(ls -t /root/.prime/agent/research/*.jsonl | head -1)
echo "=== $LATEST ==="
wc -l < "$LATEST"
grep -cE "read_page\"" "$LATEST" 2>/dev/null || true
cat "$LATEST"

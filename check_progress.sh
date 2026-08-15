#!/usr/bin/env bash
L=$(ls -t ~/.prime/agent/research/run-*.jsonl | head -1)
echo "$L"
grep -o '"event": "[a-z_]*"' "$L" | tail -6
grep -E 'research_done|budget_stop|threat_intel' "$L" | tail -3

#!/usr/bin/env bash
L=$(ls -t ~/.prime/agent/research/run-*.jsonl | head -1)
echo "== select pages =="
grep '"research_select_pages"' "$L"
echo "== research_en_topic =="
grep '"research_en_topic"' "$L"
echo "== search queries =="
grep '"research_search"' "$L" | tail -3
echo "== tg / adversarial =="
grep -cE '"research_tg"' "$L" || true
grep '"research_adversarial"' "$L" | head -1

---
name: research-guard
description: "Research guardrails and token economics for research skills: DSH-style tool-result trimming, budget caps (pages/searches/chars/runtime), and append-only run logs. Use trim() to slim long outputs, status() to check budget."
version: 0.1.0
author: user
---

# Research Guard — 护栏 + Token 经济学

为 deep_research / read_page / parallel_explore 提供三件横切能力（仿 DeepSeek Harness 的三道控制线与事件日志设计）：

1. **工具结果瘦身**：`trim(text)` — 超过上限保留头部+尾部，中段替换为说明（DSH 默认 8192 字符，保留头 4096 + 尾 1024）
2. **预算护栏**：页数 / 搜索次数 / 累计字符 / 运行时长四项上限，超限自动熔断（防自主探索失控卡死）
3. **Append-only 运行日志**：每次搜索/读页/熔断写入 JSONL，只增不改，事后可复盘

## Usage

```python
# 查看当前预算消耗
print(await research_guard(action="status"))

# 瘦身长文本（默认 8192 上限，头 4096 + 尾 1024）
print(await research_guard(action="trim", text=long_text))

# 手动记录事件（自动记录的之外）
print(await research_guard(action="log", event="custom_note", data={"note": "..."}))
```

## Environment variables

- `PRIME_RESEARCH_MAX_PAGES` — 单次研究最多读页数（默认 20）
- `PRIME_RESEARCH_MAX_SEARCHES` — 单次研究最多搜索次数（默认 15）
- `PRIME_RESEARCH_MAX_CHARS` — 单次研究累计抓取字符上限（默认 200000）
- `PRIME_RESEARCH_MAX_RUNTIME` — 单次研究运行秒数上限（默认 900）
- `PRIME_RESEARCH_RUN_ID` — 运行日志标识（默认时间戳），日志在 `~/.prime/agent/research/run-<id>.jsonl`

## Notes

- 预算是内核进程内状态：同一会话内多个技能共享同一份预算；重启内核即清零
- 其余技能内部自动调用本包，日常无需手动调用

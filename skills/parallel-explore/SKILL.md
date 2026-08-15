---
name: parallel-explore
description: "Parallel exploration: run multiple websearch queries or read_page URLs concurrently (results kept in input order), or adversarial mode that auto-generates counter-evidence queries (失败/争议/风险/debunked) for a topic. Respects research_guard budget."
version: 0.1.0
author: user
---

# Parallel Explore — 并行探索 + 反证搜索

仿 DSH 的并行工具池思路：多路并发、结果按输入顺序返回（不因网速抖动打乱上下文），默认 3 并发对免费后端友好。

## Usage

```python
# 1) 并行搜索多个查询
print(await parallel_explore(queries=["topic A", "topic B", "topic C"]))

# 2) 并行精读多个 URL
print(await parallel_explore(urls=["https://a.com/1", "https://b.com/2"]))

# 3) 反证模式：自动生成正反两组查询（含 失败/争议/风险/debunked 变体），按支持/反证分组返回
print(await parallel_explore(topic="Kimi K2 vs DeepSeek V4", adversarial=True))
```

## Notes

- 每路结果默认瘦身到 4096 字符（可用 `max_output_per` 调整）
- 全部计入 research_guard 预算，超限自动熔断未开始的查询
- 并发数 `workers` 默认 3（搜索）/ 4（读页），不要调太大以免触发后端限流

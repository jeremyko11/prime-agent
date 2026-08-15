---
name: deep-research
description: "Iterative deep research loop: decompose topic -> parallel search -> deep-read top pages -> cross-validate claims across >=2 independent domains (CONFIRMED/MAJORITY/DISPUTED/SINGLE-SOURCE) -> adversarial counter-evidence pass -> structured markdown report. Auto-stops on research_guard budget. Persists findings to mnemosyne when available."
version: 0.1.0
author: user
---

# Deep Research — 深度研究循环

一站式调研流水线（确定性执行，不由技能内 LLM 编造内容）：

```
拆解主题 → parallel_explore 并行搜索 → read_page 精读高价值页（P0-P2 信源优先）
        → 跨域交叉验证（≥2 个独立域名支持 = CONFIRMED）
        → 反证轮（主动搜索失败/争议/风险证据）
        → 结构化报告 + mnemosyne 沉淀（可选）
```

**选页规则**：候选 URL 按信源等级排序——主题官方域名视作 P0（如研究 Polymarket 时 polymarket.com），其后依次 P0（政府/学术）→ P1（权威媒体/机构）→ P2（专业社区）→ P3（其余，仅作补位）；已读过的域名跨轮跳过，不重复精读。第一轮自动通过 Wikipedia opensearch 注入一篇 P1 基准页作锚点（中文课题走 zh.wiki，英文课题走 en.wiki），保证任何课题至少有一个可交叉验证的权威来源。

三轮默认视角：**基础事实 → 案例/数据 → 反证/局限**（DSH 的 Creator 思路：把"研究方法"本身固化为可复用流程）。

## Usage

```python
# 标准深度调研（3 轮，预算内自动推进）
print(await deep_research("Polymarket 天气市场结算机制"))

# 轻量快查（1 轮 + 2 页精读）
print(await deep_research("DeepSeek V4 Pro 定价", max_cycles=1, pages_per_cycle=2))

# 不写记忆、不做反证轮
print(await deep_research("...", adversarial=False, retain=False))
```

## Output

Markdown 报告：执行摘要 / 关键发现（带置信标签与来源域名）/ 争议与反证 / 待查问题 / 来源清单 / 预算统计。运行日志在 `~/.prime/agent/research/run-*.jsonl`。

## Notes

- 预算由 research_guard 控制（默认 15 次搜索 / 20 页 / 200K 字符 / 15 分钟），超限自动熔断并输出已完成部分
- 主张抽取为启发式（含数字/日期/关键词的句子），置信标签只反映**来源交叉情况**，不代表事实正确性——最终判断留给模型

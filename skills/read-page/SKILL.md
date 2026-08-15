---
name: read-page
description: "Read a single web page into clean text with backend fallback: local cache -> Jina Reader -> direct HTTP + HTML-to-text -> Firecrawl (if key). Grades source credibility (P0 gov/edu ... P3 unknown) and applies DSH-style head+tail trimming. Use after websearch to deep-read the most promising URLs."
version: 0.1.0
author: user
---

# Read Page — 单页精读

搜索之后的下一步：把 URL 变成干净正文。四级回退链，全部免费：

| 顺序 | 后端 | 依赖 | 说明 |
|---|---|---|---|
| 1 | 本地缓存 | 无 | 24h TTL，同 URL 二次读取零成本 |
| 2 | Jina Reader (r.jina.ai) | 无需 Key | JS 页面也能转 Markdown |
| 3 | 直接 HTTP + 自带 HTML 转文本 | 无 | 兜底，纯静态页 |
| 4 | Firecrawl | FIRECRAWL_API_KEY | 若已配置则自动启用 |

每个结果自动带**来源分级**（P0 政府/教育/国际组织，P1 权威媒体与文档，P2 社区/博客，P3 未知），供交叉验证时参考。

## Usage

```python
# 精读单个页面（默认瘦身到 8192 字符：头 4096 + 尾 1024）
print(await read_page("https://example.com/article"))

# 完整参数
print(await read_page("https://example.com/a", max_output=12000, use_cache=False))
```

## Notes

- 输出头部标注：域名、来源等级、命中后端、原始字符数
- 自动计入 research_guard 预算（页数/字符）并写运行日志
- 需要代理时沿用 HTTPS_PROXY 环境变量（与 websearch 一致）

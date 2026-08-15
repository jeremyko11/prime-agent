---
name: websearch
description: Search the web via Bocha (DeepSeek's search) with 3 free fallbacks: DuckDuckGo, GitHub, Wikipedia. All free sources never expire.
---

# Web Search (Bocha + DuckDuckGo + GitHub + Wikipedia)

**4 backends** with automatic fallback. First success wins.

| Backend | Free? | Key? | Never expires? | Coverage |
|---|---|---|---|---|
| **Bocha** | 2000 free calls | BOCHA_API_KEY | No (quota) | General (China-direct, DeepSeek engine) |
| **DuckDuckGo** | Yes | No | Yes | General (needs proxy in China) |
| **GitHub** | Yes | No | Yes | Code/repositories/tech |
| **Wikipedia** | Yes | No | Yes | Encyclopedia (zh+en) |

## Usage

```python
print(await websearch("any query"))
```

## Environment variables

- `BOCHA_API_KEY` — enables Bocha (get free at https://open.bochaai.com)
- `HTTPS_PROXY` — proxy for DuckDuckGo (e.g. http://127.0.0.1:7897)
- `PRIME_AGENT_WEBSEARCH_TIMEOUT` — timeout in seconds (default 30)
- `PRIME_AGENT_WEBSEARCH_NUM_RESULTS` — number of results (default 8)

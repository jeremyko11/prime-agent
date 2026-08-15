---
name: source-registry
description: Unified research source registry - academic (arXiv/OpenAlex/SemanticScholar), community (HackerNews/Reddit), global news (GDELT/NewsRSS), Telegram public channel reader, and same-domain crawler. Output format matches websearch so deep-research picks URLs up unchanged.
---

# Source Registry

One call fans out to free search backends in parallel, merges, dedupes by
root domain, and returns websearch-compatible text. English/international
queries work best (arXiv/OpenAlex/GDELT are English-first).

| Backend | Free | Key | Coverage |
|---|---|---|---|
| **arXiv** | yes | no | preprints: physics / CS / quant-finance / econ |
| **OpenAlex** | yes | no | 250M+ scholarly works, abstracts + citation counts |
| **Semantic Scholar** | yes (shared pool) | no | CS/bio papers; 429 tolerated silently |
| **HackerNews** | yes | no | tech community discussion (Algolia API) |
| **Reddit** | yes | no | community discussions; may 403, tolerated |
| **GDELT** | yes | no | global news, real article URLs |
| **NewsRSS** | yes | no | Google News RSS (redirect links, ranked lower) |
| **SecRSS** | yes | no | BleepingComputer + The Record feeds, keyword-filtered; falls back to latest headlines |

Opt-in (not in the default fan-out):

| Backend | Free | Key | Coverage |
|---|---|---|---|
| **webz** | no (paid) | `WEBZ_IO_API_KEY` | Webz.io dark-web/threat stream — the *aggregated layer*: pre-cleaned intel via legal commercial feed, no Tor. Without the key the backend reports a config error in `[backend errors]` and everything else still works. |

## Usage

```python
# multi-backend search (all backends, merged + domain-deduped)
print(await source_registry("fusion energy commercialization"))

# subset of backends
print(await source_registry("SMR cost", backends=("arxiv", "openalex")))

# read a Telegram PUBLIC channel web preview (last posts)
print(await source_registry(action="tg", channel="durov"))

# same-domain crawl: read base page's top same-domain links
print(await source_registry(action="crawl", url="https://www.iaea.org/", max_pages=3))

# backend health
print(await source_registry(action="status"))
```

## deep-research integration

`deep_research(topic)` automatically:
1. resolves an English topic via Wikipedia zh→en langlinks (CJK topics),
2. runs one source-registry query per cycle alongside websearch,
3. reads matched Telegram channels from `tg_channels.json` (cycle 2).

## Environment

- `PRIME_SOURCE_REGISTRY_TIMEOUT` — per-backend timeout seconds (default 20)
- `WEBZ_IO_API_KEY` — enables the paid Webz.io dark-web backend (deep-research auto-activates it for threat-intel topics)
- `HTTPS_PROXY` — used for backends needing a proxy (China network)

## tg_channels.json (optional, same dir as this file)

```json
{
  "核聚变|fusion": ["iter_org"],
  "polymarket|预测市场": ["polymarket"]
}
```

Only PUBLIC channels (t.me/s/ web preview) are supported. Private or invite-only
channels are out of scope by design.

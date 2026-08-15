# Fork Notes

## Baseline

This fork is based on upstream
[PrimeIntellect-ai/prime-agent](https://github.com/PrimeIntellect-ai/prime-agent)
at commit `10fb172b` (2026-08-07, between tags v0.7.1 and v0.7.2). The harness
source under `packages/`, `scripts/`, `prime-agent-runtime/` is **byte-identical
to upstream** (verified: full-tree diff = 0). All local work lives outside the
harness source, listed below.

## What's mine

### 1. Research skill suite (`skills/`)

Self-authored skills, deployed to `~/.prime/agent/skills/` and pip-installed
(`pip install -e`) into both venvs (`.venv` + `kernel-venv`):

| Skill | Purpose |
|---|---|
| `research-guard` | Token/page/char/time budget caps + JSONL audit logging for research runs |
| `read-page` | Single-page extraction, 4-level backend fallback, source tier grading (P0 gov/edu → P3) |
| `parallel-explore` | Parallel query fan-out with adversarial mode |
| `deep-research` | Full research cycle: bilingual topic translation (zh→en via Wikipedia langlinks with compound-phrase segmentation fallback), 3 progressive cycles, adversarial rounds, cross-source validation |
| `source-registry` | Unified fan-out: arXiv / OpenAlex / Semantic Scholar / HackerNews / Reddit / GDELT / NewsRSS / SecRSS, Telegram channel reader, same-domain crawler |
| `websearch` | 4-backend search fallback chain: Bocha → DuckDuckGo → GitHub → Wikipedia (replaces the bundled Serper skill) |
| `wsl-safety` | Monkey-patches glob/os.walk to block slow /mnt (9P) wildcard scans that hang the IPython kernel |
| `firecrawl-skill` | Firecrawl API wrapper: scrape / search / crawl / batch / deep_research |
| `engineering-insurance-claim-review` | 工程险理赔审案与定损 (CAR/EAR/IDI claim review & loss assessment) |

Third-party skills included for a complete backup (see each `SKILL.md` for
attribution): `mnemosyne` (MIT, FrankHu-HK), `pixelrag`,
`CTF-Sandbox-Orchestrator` (GPL-3, ships its own LICENSE), and
`reverse-skill-router` (from the public reverse-skill repo zip; it ships no
upstream LICENSE — included at the repo owner's discretion for backup
completeness).

### 2. Deployment & tests (repo root)

- `deploy.sh` — Windows → WSL: syncs skills to `~/.prime/agent/skills/` and
  `pip install -e` into both venvs
- `test_*.sh` — regression suite (e2e, per-skill, `_en_topic` translation chain)

### 3. Harness config

- `docs/settings.example.json` — active settings: `"bundledSkills": { "websearch": false }`
  (disables the bundled Serper skill so the custom 4-backend `websearch` takes over),
  default provider `opencode`, model `deepseek-v4-flash`, thinking level high.
- `auth.json.enc` — encrypted backup of `~/.prime/agent/auth.json` (API keys).
  Decrypt (passphrase kept separately by the owner):

  ```bash
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
    -in auth.json.enc -pass pass:'<PASSPHRASE>' -out auth.json
  ```

## Environment variables

| Var | Required by | Notes |
|---|---|---|
| `BOCHA_API_KEY` | `websearch` | primary search backend (2000 free calls) |
| `WEBZ_IO_API_KEY` | `source-registry` (webz backend) | optional; dark-web/threat feed |
| `FIRECRAWL_API_KEY` | `firecrawl-skill` | optional; JS-rendered scraping |

## License

Upstream code: MIT (see `LICENSE`, Copyright Mario Zechner / Prime Intellect).
My additions: MIT.

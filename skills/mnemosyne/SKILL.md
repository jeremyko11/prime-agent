---
name: mnemosyne
description: "Mnemosyne Memory Engine v4.0: L1 memory cache for 80%+ token savings. recall before answering, retain after learning."
version: 4.0.0
author: FrankHu-HK
license: MIT
---

# Mnemosyne Memory Engine

L1 Memory Cache for AI Agents. Zero dependencies, 100% local, 80%+ token savings.

## When to Use

1. **Before answering complex questions**: `recall` Top-5 relevant memories → answer with just those as context → save 80%+ tokens
2. **After learning new facts/preferences/lessons**: `retain` to store in mnemosyne
3. **Periodically**: `reflect` to consolidate and extract patterns

## Usage

```python
# Recall memories before answering
print(await mnemosyne(action="recall", query="Polymarket strategy", k=5))

# Store a memory
print(await mnemosyne(action="retain", content="important fact", mtype="lesson", tags="trading"))

# Deep reflection
print(await mnemosyne(action="reflect"))

# Memory statistics
print(await mnemosyne(action="stats"))
```

## Memory Types (for retain)
semantic|episodic|procedural|reflective|preference|lesson|strategy|belief|observation|identity|todo|web

## Token Saving Strategy
Instead of loading full context every turn, recall Top-5 relevant memories (~200 tokens).
This reduces memory-related tokens by 80%+.

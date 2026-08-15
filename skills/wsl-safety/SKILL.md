---
name: wsl-safety
description: "Prevents IPython kernel hangs by blocking slow glob/walk operations on /mnt (WSL 9P filesystem). Auto-patches glob.glob and os.walk. Use safe_search() for file searches."
version: 1.0.0
author: user
---

# WSL Filesystem Safety

Prevents the #1 cause of Prime Agent hangs on WSL: recursive glob/os.walk on `/mnt`
(Windows filesystem via 9P protocol is 10-100x slower than native Linux paths).

## How It Works (Automatic)

On import, this skill **monkey-patches** `glob.glob`, `glob.iglob`, and `os.walk`:

| Operation | Behavior |
|---|---|
| `glob.glob("/mnt/**/*.md", recursive=True)` | **BLOCKED** — returns `[]` + prints warning |
| `glob.glob("/mnt/c/Users/.../file.md")` (no wildcard) | Allowed (single file, not a scan) |
| `glob.glob("/root/**/*.md", recursive=True)` | Allowed (native Linux path, fast) |
| `os.walk("/mnt/c/")` | **BLOCKED** — returns immediately + prints warning |
| `os.walk("/root/work/")` | Allowed (native Linux path, fast) |

## Hard Rules (MUST follow)

1. **NEVER** use `glob.glob()`, `glob.iglob()`, `os.walk()`, or `pathlib.Path().rglob()`
   with wildcard patterns on `/mnt`, `/media`, `/mnt/c`, `/mnt/d`, or any Windows mount.
2. If you need a file from Windows, first copy it: `shutil.copy("/mnt/c/path/file", "/root/work/")`
3. Then operate on the copy in `/root/work/` (native Linux path, full speed).
4. For file searches, use `safe_search()` provided by this skill.

## Usage

```python
import wsl_safety

# Safe file search (with timeout, blocks /mnt by default)
results = wsl_safety.safe_search(
    root="/root/work",
    pattern="*.md",
    max_results=50,
    timeout=10
)
print(results)

# Copy a Windows file to native Linux path for fast access
wsl_safety.copy_from_windows(
    windows_path="/mnt/c/Users/username/Downloads/file.md",
    dest="/root/work/"
)
```

## Why This Exists

Without this skill, an Agent running `glob.glob("/mnt/**/*keyword*", recursive=True)`
will hang the IPython kernel for 20+ minutes (or until aborted), because WSL's 9P
protocol traverses the entire Windows filesystem sector by sector.

Hermes Agent and OpenClaw don't have this problem because their tool calls have
independent timeouts. Prime Agent's IPython kernel has no execution timeout, so
a single bad glob can freeze the entire session.

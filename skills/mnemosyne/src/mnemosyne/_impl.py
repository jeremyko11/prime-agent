"""Mnemosyne Memory Engine skill for prime-agent."""

import asyncio

MNEMOSYNE_PY = "/opt/mnemosyne/mnemosyne.py"
MEMORY_DIR = "/root/.mnemosyne"
TIMEOUT = 30


async def run(
    action: str = "recall",
    query: str = "",
    content: str = "",
    k: int = 5,
    mtype: str = "semantic",
    tags: str = "",
):
    """Mnemosyne L1 Memory Cache — 80%+ token savings.

    Args:
        action: recall|retain|reflect|stats|consolidate
        query: search query (for recall)
        content: memory content (for retain)
        k: number of results (for recall, default 5)
        mtype: memory type (for retain): semantic|episodic|procedural|reflective|preference|lesson|strategy|belief|observation|identity|todo|web
        tags: comma-separated tags (for retain)

    Returns:
        str: mnemosyne output (recalled memories, storage confirmation, stats, etc.)
    """
    cmd = ["python3", MNEMOSYNE_PY, "--dir", MEMORY_DIR]

    if action == "recall":
        if not query:
            return "Error: query is required for recall"
        cmd += ["recall", query, "--k", str(k)]
    elif action == "retain":
        if not content:
            return "Error: content is required for retain"
        cmd += ["retain", "--content", content, "--type", mtype]
        if tags:
            cmd += ["--tags", tags]
    elif action == "reflect":
        cmd += ["reflect", "--deep"]
    elif action == "consolidate":
        cmd += ["consolidate"]
    elif action == "stats":
        cmd += ["stats"]
    else:
        return f"Error: unknown action '{action}'. Use: recall|retain|reflect|stats|consolidate"

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT)
        if proc.returncode == 0:
            return stdout.decode("utf-8", errors="replace").strip()
        else:
            return f"Error: {stderr.decode('utf-8', errors='replace').strip()}"
    except asyncio.TimeoutError:
        return f"Error: timeout after {TIMEOUT}s"
    except Exception as e:
        return f"Error: {e}"

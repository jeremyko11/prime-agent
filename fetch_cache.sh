#!/usr/bin/env bash
KV=$HOME/.prime/agent/kernel-venv
$KV/bin/python - <<'EOF'
import hashlib
from pathlib import Path

urls = [
    "https://www.36kr.com/p/2902871526300291",
    "https://www.nuclear-fusion.com.cn/blog/ornl",
    "https://h5.ifeng.com/c/vivoArticle/v002XumGt3MggcW13YiNU6kwAjjhr9D1A62XL2E8nxIZv--k__?isNews=1&showComments=0",
    "https://www.baogaobox.com/insights/260309000026092.html",
    "https://www.iim.net.cn/103/view-244321-1.html",
    "https://zh.wikipedia.org/wiki/%E5%8F%AF%E6%8E%A7%E6%A0%B8%E8%81%9A%E5%8F%98",
]
d = Path.home() / ".prime" / "agent" / "cache" / "read_page"
out = []
for u in urls:
    key = hashlib.sha1(u.encode("utf-8")).hexdigest()
    p = d / f"{key}.txt"
    if p.exists():
        out.append(f"===== {u} =====\n{p.read_text(encoding='utf-8', errors='replace')}")
    else:
        out.append(f"===== {u} =====\n(no cache)")
dest = Path("/mnt/d/A/PPT/prime_upgrade/research_out_pages.txt")
dest.write_text("\n\n".join(out), encoding="utf-8")
print(f"saved {dest} ({dest.stat().st_size} bytes)")
EOF

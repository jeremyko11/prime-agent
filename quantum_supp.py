import asyncio

async def main():
    from source_registry import run as sr
    jobs = [
        ("post-quantum cryptography NIST migration status", ("arxiv", "openalex", "s2")),
        ("harvest now decrypt later quantum threat", ("gdelt", "newsrss", "hn")),
        ("quantum computing cryptography threat", ("secrss",)),
        ("Shor algorithm RSA logical qubits requirement", ("arxiv", "s2")),
    ]
    parts = []
    for q, be in jobs:
        try:
            out = await sr(q, backends=be, max_output=4500, timeout=40)
            parts.append(f"\n\n########## {q} [{','.join(be)}] ##########\n{out}")
            print(f"OK {q}: {len(out)} chars")
        except Exception as e:
            print(f"FAIL {q}: {e}")
    with open('/root/work/quantum_supplement.md', 'w') as f:
        f.write("".join(parts))

asyncio.run(main())

import asyncio, time

async def main():
    from deep_research._impl import run
    t0 = time.time()
    out = await run('量子计算对加密体系的冲击',
                    max_cycles=3, queries_per_cycle=3, pages_per_cycle=3, max_output=30000)
    with open('/root/work/research_out_quantum.md', 'w') as f:
        f.write(out)
    print(f'DONE in {time.time()-t0:.0f}s, {len(out)} chars')
    print(out[:2500])

asyncio.run(main())

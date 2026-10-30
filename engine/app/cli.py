"""Terminal entry point: python -m app.cli -p "prompt" -f file1 -f file2 -n 10 -o out_dir"""
import argparse
import asyncio
import json
import logging
import time
from pathlib import Path

from .llm import LLM
from .pipeline import Options, Pipeline


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--prompt", required=True)
    ap.add_argument("-f", "--file", action="append", default=[])
    ap.add_argument("-n", "--slides", type=int, default=10)
    ap.add_argument("-o", "--out", default="data/cli")
    ap.add_argument("--lang", default="auto")
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--no-anim", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S")

    llm = LLM(base_url=a.base_url)
    info = await llm.init()
    print("LLM:", info, "vision:", llm.supports_vision)
    t = time.perf_counter()
    res = await Pipeline(llm).run(
        a.prompt, [Path(f) for f in a.file], Path(a.out),
        Options(slide_count=a.slides, language=a.lang, animations=not a.no_anim),
        progress=lambda m, p: print(f"[{p * 100:5.1f}%] {m}", flush=True))
    await llm.close()
    print("\nPPTX:", res.pptx)
    print("slides:", [s.type for s in res.deck.slides])
    print("timings:", res.timings)
    s = res.llm_stats
    print("llm:", s, f"=> {s['completion_tokens'] / max(1e-6, time.perf_counter() - t):.0f} completion tok/s overall")
    for w in res.warnings:
        print("WARN:", w)
    (Path(a.out) / "report.json").write_text(json.dumps(
        {"model": info, "timings": res.timings, "llm": s, "warnings": res.warnings}, indent=1))


if __name__ == "__main__":
    asyncio.run(main())

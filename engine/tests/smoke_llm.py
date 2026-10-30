"""Quick LLM checks: tokens/s (single + parallel), JSON-schema output, vision. python -m tests.smoke_llm"""
import asyncio
import io
import time

from PIL import Image, ImageDraw

from app.llm import LLM, image_part
from app.schema import Kpis


async def main():
    llm = LLM()
    print("model:", await llm.init(), "vision:", llm.supports_vision)

    msgs = [{"role": "user", "content": "Write 250 words about why brand consistency matters for B2B companies."}]
    t = time.perf_counter()
    await llm.chat(msgs, max_tokens=400, temperature=0.7)
    dt = time.perf_counter() - t
    print(f"single stream: {llm.stats['completion_tokens']} tok in {dt:.1f}s = {llm.stats['completion_tokens'] / dt:.0f} tok/s")

    before = llm.stats["completion_tokens"]
    t = time.perf_counter()
    await asyncio.gather(*(llm.chat(msgs, max_tokens=400, temperature=0.7) for _ in range(8)))
    dt = time.perf_counter() - t
    n = llm.stats["completion_tokens"] - before
    print(f"8 parallel: {n} tok in {dt:.1f}s = {n / dt:.0f} tok/s aggregate")

    t = time.perf_counter()
    k = await llm.structured([{"role": "user", "content": "KPI slide: response rate 67% (vs 75% July 2025), eNPS -1 (vs -2), "
                                                          "70% satisfied (vs 72%). Title 'Key insights'."}], Kpis)
    print(f"structured Kpis in {time.perf_counter() - t:.1f}s:", k.model_dump_json()[:400])

    im = Image.new("RGB", (640, 360), "white")
    d = ImageDraw.Draw(im)
    d.text((20, 20), "Leads per quarter", fill="black")
    for i, (q, v) in enumerate([("Q1", 820), ("Q2", 1140), ("Q3", 1625)]):
        h = v / 6
        d.rectangle([80 + i * 180, 330 - h, 180 + i * 180, 330], fill=(41, 217, 194))
        d.text((110 + i * 180, 335 - h - 20), str(v), fill="black")
        d.text((120 + i * 180, 340), q, fill="black")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    t = time.perf_counter()
    out = await llm.chat([{"role": "user", "content": [image_part(buf.getvalue()),
                                                       {"type": "text", "text": "Transcribe the chart data exactly."}]}],
                         max_tokens=200)
    print(f"vision in {time.perf_counter() - t:.1f}s:", out.strip()[:300])
    await llm.close()


asyncio.run(main())

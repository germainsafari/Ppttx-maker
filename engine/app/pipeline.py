"""Prompt + files -> outline -> per-slide content (parallel) -> fact check -> .pptx -> previews."""
import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import prompts
from .config import settings
from .ingest import Source, ingest_file
from .llm import CHARS_PER_TOKEN, LLM, LLMError, approx_tokens, image_part
from .render.builder import render_deck
from .schema import CONTENT_MODELS, DeckSpec, Outline, SlideSpec, outline_model

log = logging.getLogger("pipeline")

NUMERIC_TYPES = {"kpis", "chart", "table"}
SECTIONS_MIN_SLIDES = 12
CRUDE = re.compile(r"\b(dick\w*|fuck\w*|shit\w*|bullshit|crap|asshole|bitch\w*|kurw\w*|chuj\w*|pierdol\w*)\b", re.I)


@dataclass
class Options:
    slide_count: int = 10
    language: str = "auto"
    animations: bool = True


@dataclass
class Result:
    deck: DeckSpec
    pptx: Path
    warnings: list[str] = field(default_factory=list)
    timings: dict = field(default_factory=dict)
    llm_stats: dict = field(default_factory=dict)


Progress = Callable[[str, float], None]


# ------------------------------------------------------------------ source handling
def _chunks(text: str, size: int = 1800) -> list[str]:
    paras = re.split(r"\n(?=\S)", text)
    out, cur = [], ""
    for p in paras:
        if len(cur) + len(p) > size and cur:
            out.append(cur)
            cur = ""
        while len(p) > size:
            out.append(p[:size])
            p = p[size:]
        cur += p + "\n"
    if cur.strip():
        out.append(cur)
    return out


_WORD = re.compile(r"[\w%€$]+", re.U)


def _relevant(chunks: list[str], query: str, budget_tokens: int) -> str:
    """Cheap keyword retrieval: pick the chunks sharing most words with the slide brief, keep document order."""
    if sum(approx_tokens(c) for c in chunks) <= budget_tokens:
        return "\n".join(chunks)
    q = {w.lower() for w in _WORD.findall(query) if len(w) > 2}
    scored = []
    for i, c in enumerate(chunks):
        words = [w.lower() for w in _WORD.findall(c)]
        hits = sum(1 for w in words if w in q)
        nums = sum(1 for w in words if any(ch.isdigit() for ch in w))
        scored.append((hits + 0.05 * nums, i))
    scored.sort(reverse=True)
    picked, used = [], 0
    for score, i in scored:
        t = approx_tokens(chunks[i])
        if used + t > budget_tokens:
            continue
        picked.append(i)
        used += t
    return "\n".join(chunks[i] for i in sorted(picked))


def _numbers(text: str) -> set[str]:
    """All plausible readings of the numbers in a text: '4,57' (decimal comma), '1,140' (thousands) and CSV cells."""
    raw = set(re.findall(r"\d+(?:\.\d+)?", text))
    raw |= {m.replace(",", ".") for m in re.findall(r"\d+,\d{1,2}(?!\d)", text)}
    raw |= {m.replace(",", "").replace(" ", "") for m in re.findall(r"\d{1,3}(?:[, ]\d{3})+(?!\d)", text)}
    return _canonical(raw)


def _canonical(raw) -> set[str]:
    out = set()
    for n in raw:
        try:
            out.add(f"{float(n):g}")
        except ValueError:
            pass
    return out


def _claimed_numbers(text: str) -> set[str]:
    """Numbers as a reader would read them on the slide: '1,140' is one thousand one hundred forty."""
    text = re.sub(r"\d{1,3}(?:,\d{3})+(?!\d)", lambda m: m.group().replace(",", ""), text)
    text = re.sub(r"(\d+),(\d{1,2})(?!\d)", r"\1.\2", text)
    return _canonical(re.findall(r"\d+(?:\.\d+)?", text))


def fact_check(slides: list[SlideSpec], source_text: str, prompt: str) -> list[str]:
    """Flag numbers in data slides that do not appear in the sources (likely hallucinated)."""
    known = _numbers(source_text + " " + prompt)
    trivial = {f"{x:g}" for x in range(0, 13)} | {"100"}
    warnings = []
    for i, s in enumerate(slides, 1):
        if s.type in ("section", "closing"):
            continue
        blob = json.dumps({k: v for k, v in s.content.items() if k not in ("notes", "image_index")},
                          ensure_ascii=False)
        if CRUDE.search(blob):
            warnings.append(f"Slide {i} ({s.type}): contains crude language - review before sharing")
        missing = sorted(n for n in _claimed_numbers(blob) - known - trivial)
        if missing:
            warnings.append(f"Slide {i} ({s.type}): please verify {', '.join(missing[:8])} "
                            f"(not in the sources - derived or invented)")
    return warnings


# ------------------------------------------------------------------ main pipeline
class Pipeline:
    def __init__(self, llm: LLM):
        self.llm = llm

    async def _describe_images(self, sources: list[Source], progress: Progress) -> tuple[list[str], list[bytes]]:
        images = [(label, data) for s in sources for label, data in s.images][:8]
        if not images:
            return [], []
        if not self.llm.supports_vision:
            return [f"{label} (no description: model has no vision)" for label, _ in images], [d for _, d in images]
        progress("Reading images with the vision model", 0.08)

        async def one(label, data):
            msgs = [{"role": "user", "content": [image_part(data, "image/jpeg"),
                                                 {"type": "text", "text": prompts.IMAGE_DESCRIBE}]}]
            try:
                return f"{label}: " + (await self.llm.chat(msgs, max_tokens=220, temperature=0.2)).strip()
            except LLMError as e:
                log.warning("image describe failed: %s", e)
                return label

        descs = await asyncio.gather(*(one(l, d) for l, d in images))
        return list(descs), [d for _, d in images]

    async def _condense(self, text: str, prompt: str, budget: int, progress: Progress, depth: int = 0) -> str:
        """Map step: long documents are reduced to fact sheets that fit the model context."""
        if approx_tokens(text) <= budget:
            return text
        if depth >= 2:
            log.warning("sources still %d tokens after condensing; truncating to %d", approx_tokens(text), budget)
            return text[: int(budget * CHARS_PER_TOKEN)]
        progress("Condensing long documents", 0.12)
        piece_tokens = max(400, min(3000, self.llm.max_model_len - 1500))
        chunks = _chunks(text, int(piece_tokens * CHARS_PER_TOKEN))
        # Each fact sheet gets a share of the budget, so the joined result is guaranteed to shrink.
        per_chunk = max(150, min(900, budget // max(1, len(chunks))))
        notes = await asyncio.gather(*(self.llm.chat(prompts.condense_messages(c, prompt), max_tokens=per_chunk,
                                                     temperature=0.1) for c in chunks))
        return await self._condense("\n".join(notes), prompt, budget, progress, depth + 1)

    async def run(self, prompt: str, files: list[Path], out_dir: Path, options: Options,
                  progress: Progress = lambda m, p: None) -> Result:
        t0 = time.perf_counter()
        timings = {}
        warnings: list[str] = []
        out_dir.mkdir(parents=True, exist_ok=True)

        progress("Reading files", 0.03)
        sources = [ingest_file(f) for f in files]
        image_descs, image_bytes = await self._describe_images(sources, progress)
        raw_text = "\n\n".join(f"=== FILE: {s.name} ===\n{s.text}" for s in sources if s.text.strip())
        if image_descs:
            raw_text += "\n\n=== IMAGES ===\n" + "\n".join(image_descs)
        timings["ingest"] = round(time.perf_counter() - t0, 1)

        ctx = self.llm.max_model_len
        outline_budget = max(800, ctx - 3500)
        slide_budget = max(600, min(6000, ctx - 2600))
        source_text = await self._condense(raw_text, prompt, outline_budget, progress) if raw_text else ""
        chunks = _chunks(source_text) if source_text else []
        timings["condense"] = max(0.0, round(time.perf_counter() - t0 - timings["ingest"], 1))

        # ---- pass 1: outline
        progress("Planning the storyline", 0.2)
        t1 = time.perf_counter()
        allow_sections = options.slide_count >= SECTIONS_MIN_SLIDES
        outline: Outline = await self.llm.structured(
            prompts.outline_messages(prompt, _relevant(chunks, prompt, outline_budget), options.slide_count,
                                     image_descs, options.language, allow_sections),
            outline_model(options.slide_count), max_tokens=min(3000, ctx // 2), temperature=0.5)
        slides_plan = _normalize_outline(outline, has_numbers=bool(_numbers(source_text)), has_images=bool(image_bytes),
                                         max_slides=options.slide_count + 1, allow_sections=allow_sections)
        timings["outline"] = round(time.perf_counter() - t1, 1)
        (out_dir / "outline.json").write_text(json.dumps(
            {"deck_title": outline.deck_title, "deck_subtitle": outline.deck_subtitle,
             "slides": [s.model_dump() for s in slides_plan]}, ensure_ascii=False, indent=1), encoding="utf-8")

        # ---- pass 2: slide contents, in parallel (vLLM batches them on the GPU)
        t2 = time.perf_counter()
        titles = [s.title for s in slides_plan]
        done = 0

        async def fill(i, plan):
            nonlocal done
            if plan.type == "closing":  # fixed brand slide: never let the model invent contact details
                done += 1
                return SlideSpec(type="closing", content={"title": "Thank you", "contact": settings.contact_line})
            if plan.type == "agenda":  # filled after all slides exist, from the final section titles
                done += 1
                return SlideSpec(type="agenda", content={"title": "Agenda", "kicker": "Overview", "notes": "",
                                                         "items": []})
            model = CONTENT_MODELS[plan.type]
            srcs = _relevant(chunks, plan.title + " " + plan.brief, slide_budget) if plan.type not in (
                "cover", "section", "closing") else ""
            msgs = prompts.slide_messages(plan.type, plan.title, plan.brief, outline.deck_title, titles, srcs,
                                          image_descs, options.language, f"slide {i + 1} of {len(slides_plan)}")
            try:
                content = (await self.llm.structured(msgs, model, max_tokens=1200)).model_dump()
            except LLMError as e:
                warnings.append(f"Slide {i + 1}: generation failed ({e}); used the outline instead")
                content = {"title": plan.title, "kicker": "", "notes": "", "bullets": [plan.brief],
                           "illustration": "none"}
                plan = plan.model_copy(update={"type": "bullets"})
            if plan.type == "cover":
                content.setdefault("title", outline.deck_title)
            done += 1
            progress(f"Writing slides ({done}/{len(slides_plan)})", 0.25 + 0.6 * done / len(slides_plan))
            return SlideSpec(type=plan.type, content=content)

        slides = await asyncio.gather(*(fill(i, p) for i, p in enumerate(slides_plan)))
        _fix_sections_and_agenda(slides)
        timings["slides"] = round(time.perf_counter() - t2, 1)

        warnings += fact_check(slides, raw_text, prompt) if raw_text else []
        deck = DeckSpec(title=outline.deck_title, subtitle=outline.deck_subtitle, slides=list(slides))
        (out_dir / "deck.json").write_text(deck.model_dump_json(indent=1), encoding="utf-8")

        progress("Rendering PowerPoint", 0.9)
        t3 = time.perf_counter()
        pptx = render_deck(deck, out_dir / "deck.pptx", images=image_bytes, animations=options.animations)
        timings["render"] = round(time.perf_counter() - t3, 2)
        timings["total"] = round(time.perf_counter() - t0, 1)
        return Result(deck=deck, pptx=pptx, warnings=warnings, timings=timings, llm_stats=dict(self.llm.stats))

    async def revise_slide(self, deck: DeckSpec, index: int, instruction: str, source_text: str) -> SlideSpec:
        s = deck.slides[index]
        model = CONTENT_MODELS[s.type]
        srcs = _relevant(_chunks(source_text), instruction + json.dumps(s.content), 3000) if source_text else ""
        new = await self.llm.structured(prompts.revise_messages(s.type, s.content, instruction, srcs), model)
        return SlideSpec(type=s.type, content=new.model_dump())


def _fix_sections_and_agenda(slides: list[SlideSpec]):
    for i, s in enumerate(slides):
        if s.type != "section":
            continue
        t = (s.content.get("title") or "").strip()
        if not re.search(r"[^\W\d_]", t):  # empty or just a number like "02"
            nxt = next((x for x in slides[i + 1:] if x.type not in ("section", "closing")), None)
            s.content["title"] = (nxt.content.get("kicker") or nxt.content.get("title") or "Overview").title() \
                if nxt else "Overview"
    for s in slides:
        if s.type == "agenda":
            s.content["items"] = [x.content["title"] for x in slides if x.type == "section"][:6]


def _normalize_outline(outline: Outline, has_numbers: bool, has_images: bool, max_slides: int,
                       allow_sections: bool):
    """Enforce deck grammar the small model may forget: cover first, closing last, no data slides without data."""
    from .schema import OutlineSlide

    plan = [s for s in outline.slides if s.type not in ("cover", "closing", "agenda")]
    # Dividers only pay off in longer decks; never back-to-back or at the end.
    if not allow_sections:
        plan = [s for s in plan if s.type != "section"]
    fixed = []
    for s in plan:
        if s.type == "section" and fixed and fixed[-1].type == "section":
            fixed.pop()
        if s.type in NUMERIC_TYPES and not has_numbers:
            s = s.model_copy(update={"type": "cards" if s.type == "kpis" else "bullets"})
        if s.type == "image" and not has_images:
            s = s.model_copy(update={"type": "bullets"})
        if fixed and s.type == "bullets" and fixed[-1].type == "bullets":
            s = s.model_copy(update={"type": "cards"})
        fixed.append(s)
    # drop a trailing section divider with nothing after it
    while fixed and fixed[-1].type == "section":
        fixed.pop()
    fixed = fixed[: max_slides - 2]
    while fixed and fixed[-1].type == "section":
        fixed.pop()
    head = [OutlineSlide(type="cover", title=outline.deck_title, brief=outline.deck_subtitle)]
    sections = [s.title for s in fixed if s.type == "section"]
    if len(sections) >= 2:
        head.append(OutlineSlide(type="agenda", title="Agenda", brief="; ".join(sections)))
    closing = OutlineSlide(type="closing", title="Thank you", brief="Thank-you slide with Admind contact")
    return head + fixed + [closing]

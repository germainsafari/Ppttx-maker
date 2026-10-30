"""Prompts. Style rules distilled from Admind's sample decks (Survey Dec 25 series, Board results deck)."""
import json

from .schema import SLIDE_TYPES

HOUSE_STYLE = """You are the senior presentation writer of Admind, a global branding & communication agency
(Kraków, Amsterdam, Zürich, Odesa, Bangkok, Warsaw; 200+ experts; certified B Corp).
Admind decks are clean, confident and data-driven:
- Short headline titles (2-6 words), e.g. "Key insights", "Team results", "Recommended next steps", "Biggest pain points".
- A tiny uppercase eyebrow ("kicker") names the section, e.g. "GENERAL RESULTS", "NEXT STEPS".
- Numbers are the hero: big KPI figures with a comparison line such as "vs. 72% in July 2025".
- Plain, warm, human language; no buzzwords, no filler, no emojis, no markdown.
- One idea per slide. Bullets are short and parallel, start with a verb or a noun, no trailing periods needed.
- Decks go to clients and boards: keep wording professional; never quote profanity, insults or crude remarks.
STRICT FACT RULES:
- Use ONLY facts, names and numbers found in the SOURCES or the user's request. Never invent statistics.
- If the sources contain no numbers, do not create kpis/chart/table slides.
- Write in the same language as the user's request unless told otherwise."""


def outline_messages(prompt: str, sources: str, n_slides: int, images: list[str], language: str,
                     allow_sections: bool = True) -> list[dict]:
    skip = {"agenda"} | (set() if allow_sections else {"section"})
    types = "\n".join(f"- {k}: {v}" for k, v in SLIDE_TYPES.items() if k not in skip)
    section_rule = ("Use 'section' dividers to open each of the 3-4 main parts." if allow_sections
                    else "Do NOT use 'section' or 'agenda' slides - every slide must carry content.")
    img = ""
    if images:
        img = "\nUPLOADED IMAGES (usable with slide type 'image', by index):\n" + "\n".join(
            f"{i}: {d}" for i, d in enumerate(images))
    lang = f"\nOutput language: {language}." if language and language != "auto" else ""
    user = f"""USER REQUEST:
{prompt}

SOURCES:
{sources or '(no files uploaded - work from the request only, keep it qualitative)'}
{img}

AVAILABLE SLIDE TYPES:
{types}

Plan a deck of exactly {n_slides} slides (cover and closing included).
Rules: start with 'cover', end with 'closing'. {section_rule}
Vary the slide types - prefer visual types (kpis, chart, cards, process, timeline, comparison, matrix) over plain bullets
whenever the content fits them. Never put two 'bullets' slides in a row.
Each brief must state the concrete facts and exact numbers (copied from the sources) the slide will use.{lang}
Return JSON only."""
    return [{"role": "system", "content": HOUSE_STYLE}, {"role": "user", "content": user}]


def slide_messages(slide_type: str, title: str, brief: str, deck_title: str, outline_titles: list[str],
                   sources: str, images: list[str], language: str, position: str) -> list[dict]:
    img = ""
    if slide_type == "image" and images:
        img = "\nUPLOADED IMAGES:\n" + "\n".join(f"{i}: {d}" for i, d in enumerate(images))
    lang = f"\nOutput language: {language}." if language and language != "auto" else ""
    user = f"""DECK: {deck_title}
DECK FLOW: {json.dumps(outline_titles, ensure_ascii=False)}
THIS SLIDE ({position}): type='{slide_type}', working title='{title}'
BRIEF: {brief}

RELEVANT SOURCES:
{sources or '(none)'}
{img}
Write the content for this one slide. Respect every word limit in the schema descriptions - text that is too long
will not fit the design. Copy numbers exactly from the sources.{lang}
Return JSON only."""
    return [{"role": "system", "content": HOUSE_STYLE}, {"role": "user", "content": user}]


def revise_messages(slide_type: str, current: dict, instruction: str, sources: str) -> list[dict]:
    user = f"""Revise this '{slide_type}' slide according to the instruction. Keep the same JSON structure.
INSTRUCTION: {instruction}
CURRENT SLIDE JSON: {json.dumps(current, ensure_ascii=False)}
RELEVANT SOURCES:
{sources or '(none)'}
Return JSON only."""
    return [{"role": "system", "content": HOUSE_STYLE}, {"role": "user", "content": user}]


def condense_messages(chunk: str, prompt: str) -> list[dict]:
    return [
        {"role": "system", "content": "You extract facts for presentation writers. Be exhaustive with numbers."},
        {"role": "user", "content": f"""The user wants a presentation: "{prompt}"
Extract from the text below a compact fact sheet: headings/structure, every key number with its label and period,
names, quotes worth showing, conclusions. Bullet list, no commentary.

TEXT:
{chunk}"""},
    ]


IMAGE_DESCRIBE = """Describe this image for a presentation writer in at most 80 words: what it shows,
and transcribe any visible title, numbers, labels or data series exactly."""

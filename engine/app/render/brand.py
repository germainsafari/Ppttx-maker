"""Admind visual identity, derived from the team's sample decks (Survey Dec 25 series)."""
import json
import math
from functools import lru_cache
from pathlib import Path

from pptx.dml.color import RGBColor

from ..config import settings

CREAM = "EDD9C2"
CREAM_LIGHT = "F6EDE2"
TEAL = "29D9C2"
TEAL_TEXT = "1FA896"
GREEN = "006C5B"
PETROL = "00505A"
CORAL = "FF523D"
ORANGE = "E5734A"
PEACH = "F7B273"
PINK = "ED8787"
BLACK = "000000"
GREY = "5F5F5F"
LIGHT_GREY = "C8C8C8"
WHITE = "FFFFFF"

SERIES_COLORS = [TEAL, CORAL, GREEN, PEACH, PINK, PETROL]

FONT_HEAD = "Acumin Pro"
FONT_BOLD = "Acumin Pro Bold"
FONT_LIGHT = "Acumin Pro Light"

SLIDE_W = 13.333
SLIDE_H = 7.5
MARGIN = 0.5
BODY_TOP = 2.25
BODY_BOTTOM = 7.0


def rgb(hex_: str) -> RGBColor:
    return RGBColor.from_string(hex_)


@lru_cache
def catalog() -> dict:
    with open(settings.assets_dir / "catalog.json") as f:
        return json.load(f)


def asset(key: str) -> Path | None:
    item = catalog().get(key)
    return settings.assets_dir / item["file"] if item else None


def fit_font_size(texts: list[str], width_in: float, height_in: float, max_pt: float, min_pt: float = 9,
                  line_spacing: float = 1.25, char_w: float = 0.50, para_gap_lines: float = 0.35) -> float:
    """Largest font size (pt) at which the paragraphs fit the box. Heuristic: avg glyph width = char_w em."""
    pt = max_pt
    while pt > min_pt:
        chars_per_line = max(1.0, width_in * 72 / (pt * char_w))
        lines = 0.0
        for t in texts:
            words = t.split()
            cur, n = 0, 1
            for w in words:
                if cur and cur + 1 + len(w) > chars_per_line:
                    n += 1
                    cur = len(w)
                else:
                    cur += (1 if cur else 0) + len(w)
            lines += n + para_gap_lines
        if lines * pt * line_spacing / 72 <= height_in:
            return pt
        pt -= 0.5
    return min_pt


def fit_uniform(texts: list[str], width_in: float, height_in: float, max_pt: float, min_pt: float = 9,
                **kw) -> float:
    """One font size for a row of equal boxes (cards, steps): the size at which every box fits."""
    return min([fit_font_size([t], width_in, height_in, max_pt, min_pt, **kw) for t in texts if t] or [max_pt])


def clamp_words(text: str, max_words: int) -> str:
    words = (text or "").split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]).rstrip(",;:") + "…"


def nice_number(v: float) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v)):,}".replace(",", " ")
    return f"{v:,.2f}".rstrip("0").rstrip(".").replace(",", " ")

"""Deck specification: the contract between the LLM and the renderer.

The LLM never writes layout code. It fills these schemas (enforced by vLLM structured outputs),
and the renderer turns them into native, editable PowerPoint objects in the Admind template.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

ICONS = [
    "lightbulb", "teamwork", "diamond", "plant", "crown", "magnifier", "pencil",
    "bowl", "coin", "smiley", "head", "bicycle",
]
Icon = Literal[
    "lightbulb", "teamwork", "diamond", "plant", "crown", "magnifier", "pencil",
    "bowl", "coin", "smiley", "head", "bicycle",
]
Illustration = Literal["none", "stairs", "people_sphere", "hands_heart", "documents", "eyes"]
Sentiment = Literal["positive", "negative", "neutral"]

SLIDE_TYPES = {
    "cover": "Title slide. Always first.",
    "agenda": "List of the deck's sections (3-6 items).",
    "section": "Chapter divider with a number and a short title.",
    "bullets": "Title + 3-6 concise bullet points, optional illustration.",
    "kpis": "2-4 big headline numbers (metrics) with labels and optional change vs. previous.",
    "chart": "One data chart (bar/column/line/pie/doughnut/stacked) built ONLY from numbers in the sources, plus 1-3 takeaways.",
    "cards": "3-4 cards, each with an icon, heading and one or two sentences (pillars, strengths, services, values).",
    "process": "3-6 sequential steps shown as a flow diagram.",
    "timeline": "3-6 dated milestones on a horizontal timeline.",
    "comparison": "Two columns compared side by side (before/after, pros/cons, option A/B).",
    "matrix": "2x2 matrix with two axes and four quadrants.",
    "table": "Compact table (max 6 rows x 5 columns) of exact figures from the sources.",
    "quote": "One impactful quote with author.",
    "statement": "One bold key message on a full-color slide.",
    "image": "Title + bullets next to one of the uploaded images.",
    "closing": "Thank-you / contact slide. Always last.",
}
SlideType = Literal[
    "cover", "agenda", "section", "bullets", "kpis", "chart", "cards", "process", "timeline",
    "comparison", "matrix", "table", "quote", "statement", "image", "closing",
]


# ---------------------------------------------------------------- outline (pass 1)
class OutlineSlide(BaseModel):
    type: SlideType
    title: str = Field(description="Short slide title in words, max 8 words (for 'section': the chapter name)")
    brief: str = Field(description="What this slide must say and which facts/numbers from the sources it uses")


class Outline(BaseModel):
    deck_title: str = Field(description="Max 8 words")
    deck_subtitle: str = Field(description="Max 12 words")
    slides: list[OutlineSlide] = Field(min_length=3, max_length=30)


def outline_model(n_slides: int) -> type[Outline]:
    """Outline schema whose slide count is enforced by the decoder (small models drift from requested counts)."""

    class SizedOutline(Outline):
        slides: list[OutlineSlide] = Field(min_length=max(3, n_slides - 1), max_length=n_slides + 1)

    SizedOutline.__name__ = "Outline"
    return SizedOutline


# ---------------------------------------------------------------- slide content (pass 2)
class Base(BaseModel):
    title: str = Field(description="Max 8 words")
    kicker: str = Field(description="Tiny uppercase eyebrow label above the title, 1-3 words, e.g. section name")
    notes: str = Field(description="Speaker notes, 2-4 sentences")


class Cover(BaseModel):
    title: str = Field(description="Max 8 words")
    subtitle: str = Field(description="Max 12 words")
    date_line: str = Field(description="Period the deck is about, taken from the request or the MOST RECENT period "
                                       "in the sources (e.g. 'Q3 2026', 'December 2025'), or the client name. "
                                       "Never an older comparison period.")


class Agenda(Base):
    items: list[str] = Field(min_length=3, max_length=6, description="Section names, max 5 words each")


class Section(BaseModel):
    title: str = Field(description="Chapter name in words, 2-5 words, never a number")


class Bullets(Base):
    bullets: list[str] = Field(min_length=2, max_length=6, description="Each bullet max 18 words")
    illustration: Illustration


class Kpi(BaseModel):
    value: str = Field(description="The number with unit, e.g. '67%', '-1', '€2.4M', max 7 chars")
    label: str = Field(description="What it measures, max 6 words")
    context: str = Field(description="Comparison or context, e.g. 'vs. 72% in July 2025', max 8 words, or empty")
    sentiment: Sentiment


class Kpis(Base):
    kpis: list[Kpi] = Field(min_length=2, max_length=4)
    takeaway: str = Field(description="One-sentence interpretation, max 25 words")


class Series(BaseModel):
    name: str
    values: list[float]


class Chart(Base):
    chart_type: Literal["bar", "column", "line", "pie", "doughnut", "stacked_bar"]
    categories: list[str] = Field(min_length=2, max_length=12,
                                  description="Category labels, max 5 words each. All categories must share ONE unit "
                                              "and scale - never mix ratings, percentages and counts in one chart")
    series: list[Series] = Field(min_length=1, max_length=3, description="Each series has exactly one value per category")
    unit: str = Field(description="Unit suffix for values like '%' or '' ")
    takeaways: list[str] = Field(min_length=1, max_length=3, description="Insights, max 18 words each")


class Card(BaseModel):
    icon: Icon = Field(description="Icon whose meaning matches the heading")
    heading: str = Field(description="2-4 word label, no numbers")
    text: str = Field(description="Max 22 words; adds evidence or detail (numbers welcome), never repeats the heading")


class Cards(Base):
    cards: list[Card] = Field(min_length=3, max_length=4)


class Step(BaseModel):
    label: str = Field(description="Max 4 words")
    text: str = Field(description="Max 15 words")


class Process(Base):
    steps: list[Step] = Field(min_length=3, max_length=6)


class Milestone(BaseModel):
    date: str = Field(description="Short date or period, e.g. 'Q1 2026'")
    label: str = Field(description="Max 4 words")
    text: str = Field(description="Max 12 words")


class Timeline(Base):
    milestones: list[Milestone] = Field(min_length=3, max_length=6)


class Column(BaseModel):
    heading: str = Field(description="Max 4 words")
    points: list[str] = Field(min_length=2, max_length=5, description="Max 14 words each")


class Comparison(Base):
    left: Column
    right: Column


class Quadrant(BaseModel):
    heading: str = Field(description="Max 4 words")
    text: str = Field(description="Max 14 words")


class Matrix(Base):
    x_axis: str = Field(description="Horizontal axis label, low -> high, max 3 words")
    y_axis: str = Field(description="Vertical axis label, low -> high, max 3 words")
    quadrants: list[Quadrant] = Field(min_length=4, max_length=4, description="Order: top-left, top-right, bottom-left, bottom-right")


class Table(Base):
    columns: list[str] = Field(min_length=2, max_length=5)
    rows: list[list[str]] = Field(min_length=1, max_length=6, description="Each row has one cell per column, cells max 8 words")
    note: str = Field(description="Source or footnote, or empty")


class Quote(BaseModel):
    quote: str = Field(description="Verbatim from the sources, max 35 words, no quotation marks. Pick a "
                                   "representative, constructive quote fit for a client or board audience - never "
                                   "one with profanity, insults or crude language.")
    author: str = Field(description="Name and role, or 'Employee comment'")
    notes: str


class Statement(BaseModel):
    statement: str = Field(description="One bold message, max 16 words")
    notes: str


class ImageSlide(Base):
    bullets: list[str] = Field(min_length=1, max_length=4, description="Max 16 words each")
    image_index: int = Field(description="Index of the uploaded image to show (0-based)")


class Closing(BaseModel):
    title: str = Field(description="e.g. 'Thank you' or a short call to action, max 5 words")
    contact: str = Field(description="Contact line, e.g. 'krk@admindagency.com', or empty")


CONTENT_MODELS: dict[str, type[BaseModel]] = {
    "cover": Cover, "agenda": Agenda, "section": Section, "bullets": Bullets, "kpis": Kpis,
    "chart": Chart, "cards": Cards, "process": Process, "timeline": Timeline,
    "comparison": Comparison, "matrix": Matrix, "table": Table, "quote": Quote,
    "statement": Statement, "image": ImageSlide, "closing": Closing,
}


class SlideSpec(BaseModel):
    type: SlideType
    content: dict


class DeckSpec(BaseModel):
    title: str
    subtitle: str
    slides: list[SlideSpec]

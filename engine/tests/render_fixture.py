"""Render the hand-written fixture deck (no LLM involved): python -m tests.render_fixture [out.pptx]"""
import json
import sys
from pathlib import Path

from app.render.builder import render_deck
from app.schema import DeckSpec

here = Path(__file__).parent
out = Path(sys.argv[1] if len(sys.argv) > 1 else here / "out" / "fixture.pptx")
out.parent.mkdir(parents=True, exist_ok=True)
deck = DeckSpec.model_validate(json.loads((here / "fixture_deck.json").read_text(encoding="utf-8")))
render_deck(deck, out)
print("wrote", out)

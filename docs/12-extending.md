# 12 - Extending and known limitations

## Add a slide type

Example: a "team" slide with photos and names.

1. `schema.py` - add the type to `SLIDE_TYPES` (one-line description the planner sees) and to `SlideType`;
   create a content model with tight field descriptions and limits; register it in `CONTENT_MODELS`.
2. `render/builder.py` - add `r_team(self, c)` using `_new("content")`, `set_title`, `_chrome`, drawing
   helpers, and `_finish(slide, notes, animated_shapes)`.
3. `tests/fixture_deck.json` - add an example; run `render_fixture.py` and look at the result.
4. If the type needs data (like `kpis`), add it to `NUMERIC_TYPES` in `pipeline.py` so it is replaced when the
   sources contain no numbers.

## Change the house style or rules

- Tone and global rules: `HOUSE_STYLE` in `prompts.py`.
- Planning rules (variety, slide count, dividers): `outline_messages` in `prompts.py`, `_normalize_outline` in
  `pipeline.py`.
- Per-field guidance: the `Field(description=...)` texts in `schema.py`.
- Visual rules: `brand.py` (colours, fonts, grid) and the `r_<type>` functions.

Re-render an existing `deck.json` after visual changes to compare without regenerating:

```python
from app.schema import DeckSpec; from app.render.builder import render_deck; import json
render_deck(DeckSpec(**json.load(open("data/x/deck.json", encoding="utf8"))), "tests/out/x.pptx", [], True)
```

## Other brands and templates (e.g. ABB)

Today the Admind identity is compiled into the code: about 77 references to colour/font constants, 13 uses of
Admind artwork, and layout names from the Admind master. Supporting several brands means turning these into a
**brand pack** loaded at run time:

```
engine/brands/abb/
  template.pptx        client master with its layouts
  brand.json           colours (background, surface, accent, positive, negative, series), fonts,
                       layout-name mapping, placeholder indices, decoration rules per slide type,
                       contact line, chart style
  assets/ + catalog.json   icons / illustrations with tags
  style.md             tone of voice appended to the system prompt
```

Work involved:

| Step | Effort |
|---|---|
| One-time refactor: renderer reads a `Brand` object instead of constants; decorations (hands, orbits) become per-brand hooks; `brand` field on jobs, API and a selector in the web app | 2-3 days |
| New brand with an official template and 3-5 example decks | ~1 day (map layouts, extract assets with `tools/`, tune, review renders) |
| New brand from guidelines only (no template) | 2-3 days (build the master first) |
| Optional generic mode: any uploaded .pptx used as template, colours/fonts read from its theme, layouts matched by name and placeholders | ~2 days; good but not designer-level results |

What to collect per brand: the official .pptx template, example decks, brand guidelines (colours, logo rules),
licensed font files, icon/illustration library, tone-of-voice notes. Use third-party brand assets only with the
brand owner's permission (fonts such as SF Pro or Google Sans are not licensed for third-party documents).

## Use another model

Any OpenAI-compatible server with JSON-schema structured output works (vLLM, SGLang, llama.cpp server with
grammar support). Change the model in `infra/docker-compose.yml` (or point `LLM_BASE_URL` elsewhere) - the
engine reads the model name and context size at start-up. For models without vision, images are listed but not
described. Run `tests/smoke_llm.py` and `tests/run_scenarios.ps1` to compare quality before switching.

## Known limitations

- **Judgement errors** - the model can still pick a weaker date for the cover, mix scales in a chart or choose a
  less relevant quote. Prompts and schema rules reduce this; the output is a strong first draft for human review.
- **Fact check is lexical** - it verifies that numbers exist in the sources, not that they are attached to the
  right label; derived numbers are flagged even when correct.
- **Revise keeps the slide type** - "turn this into a chart" rewrites the content but not the type; edit the
  spec for type changes.
- **Retrieval is keyword-based** - fine for typical decks and with a 64k context; very large document sets would
  benefit from embedding search (a small local embedding model could be added to vLLM).
- **Previews** use LibreOffice and fallback fonts until Acumin Pro is installed in the image; no animations in
  previews.
- **One GPU** - two decks generate in parallel; heavier load queues. The model reserves most of the VRAM.
- **Single template** - see "Other brands" above.

## Ideas for next steps

- Brand packs and a brand selector (above).
- Chart sanity rule in code: split or refuse charts whose values differ by more than ~50x.
- Optional "change slide type" in revise (re-plan one slide).
- Speaker-notes export and a "presenter script" mode.
- Usage log (who generated what, duration) for internal reporting.
- Cloudflare Access SSO instead of the shared password.

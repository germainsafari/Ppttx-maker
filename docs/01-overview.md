# 01 - Overview

## The problem

Admind produces many reporting and pitch decks (survey results, campaign reviews, credentials). Writing them is
repetitive: read the data, pick the numbers that matter, lay them out in the Admind style. Cloud assistants
(ChatGPT, Claude, Copilot) can help, but sending client data and internal survey results to a third-party
model is not acceptable.

## Goals

| Goal | How it is met |
|---|---|
| **No data leaves Admind** | The only model is open-weight Qwen3.6, running in vLLM on the office GPU. The engine never calls an external API. |
| **Works for anyone in the team** | Web app: prompt + drag-and-drop files, previews, download. Sign-in with a team password. |
| **Looks like an Admind deck** | Slides are drawn into a master template extracted from the team's own decks, with the real artwork, colours and typography. |
| **Real graphics, not text walls** | 16 slide types including native charts, KPI cards, process flows, timelines, 2x2 matrices, tables, quotes. |
| **Editable output** | Everything is a native PowerPoint object (text boxes, shapes, charts with embedded data, tables), never a flat image. |
| **Fits one 32 GB GPU** | Mixture-of-experts model in NVFP4 (4-bit) precision: 22 GB of weights, 3B parameters active per token. |
| **Reachable from anywhere** | Same pattern as `lt.admindagency.com`: Cloudflare tunnel to a local port, web front end on Vercel. |

## The key idea: the model decides, code draws

Large cloud models produce good-looking slides not because they "draw" but because they write code that
draws. This project applies that idea in a way that is reliable with a much smaller local model:

```
  model:  "slide 4 is a chart: column, categories [Q1, Q2, Q3], values [4.2, 5.8, 7.1], unit M,
           takeaways [...]"                                     <- structured JSON, schema-enforced
  code:   draws a native PowerPoint column chart in Admind colours, numeric format, no gridlines,
          takeaway panel on the right, fade-in animation         <- deterministic Python
```

Letting a 3B-active model write free-form python-pptx code would produce broken layouts and crashes. Asking it
to fill a fixed JSON schema per slide type is something it does almost perfectly, especially because vLLM's
**structured outputs** constrain decoding so the output always parses. All visual quality lives in code that
was tuned once by looking at the rendered result.

Consequences of this split:

- **Brand consistency by construction** - the model cannot pick a wrong colour or font; it never sees them.
- **Predictable layouts** - text is clamped to word limits and fonts are auto-fitted to their boxes.
- **Cheap edits** - revising a slide is one small model call plus a re-render; manual edits to the JSON spec
  re-render without any model call.
- **Model-agnostic** - any OpenAI-compatible model that supports JSON-schema output can be swapped in.

## What was learned from the sample decks

The six sample decks in the repository root (`Survey Dec 25 - ...`, `Annual Survey December 2025 ...`) were
analysed with the scripts in `tools/`:

- **Template** - 40 slide layouts (Cover, Chapter / Divider, Headline only, Big statement, Content and photo,
  Thank you, End main, ...). The master was saved without slides as `engine/templates/admind_master.pptx`.
- **Palette** - cream `#EDD9C2`, light cream `#F6EDE2`, teal `#29D9C2` (text teal `#1FA896`), coral `#FF523D`,
  green `#006C5B`, plus peach/pink/petrol accents.
- **Typography** - Acumin Pro (regular / light / bold), large light headings, tiny uppercase letter-spaced
  "eyebrow" labels, a coral underscore `_` after titles.
- **Artwork** - 3D hands (OK, thumbs-up, pointing finger), glossy spheres, line orbits, line-art icons and
  illustrations; extracted into `engine/assets/` with a tagged catalogue.
- **Geometry** - exact positions/rotations of the cover hands, divider orbit and bar, closing orbits and
  spheres, so generated slides match the originals.
- **Content patterns** - KPI cards with "vs. 72% in July 2025" context lines, eNPS trends, strengths and pain
  points as icon cards, employee quotes, "Recommended next steps".

These patterns became the slide types (see [04](04-slide-schema.md)) and the house-style system prompt
(see [03](03-generation-pipeline.md)).

## Results in numbers

Measured on the RTX 5090 with Qwen3.6-35B-A3B NVFP4:

| Deck | Inputs | Time to .pptx | Time incl. previews |
|---|---|---|---|
| Digital Platforms survey, 14 slides | 1 pptx | 12.9 s | - |
| Agency credentials, 8 slides | 1 txt | 6.2 s | - |
| Campaign review, 9 slides | 1 xlsx | 8.4 s | - |
| Board update, 10 slides | 1 pptx + 1 xlsx | 11.3 s | 14 s |
| Revise one slide | - | 3 s | 3 s |

The previous model (Qwen2.5-VL-7B, 4k context) needed 22 s for 10 slides, produced repetitive layouts and
invented numbers; see [06](06-model-serving.md).

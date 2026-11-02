# 05 - Rendering

Code: `engine/app/render/` - `builder.py` (layouts and drawing), `brand.py` (identity and text fitting),
`animate.py` (transitions and animations). Library: python-pptx, plus raw OOXML where python-pptx has no API.

## Template

`engine/templates/admind_master.pptx` is `Survey Dec 25 - Brand Advisory.pptx` with every slide removed
(`tools/make_template.py`), so it contains the original slide masters, 40 layouts, theme colours and fonts.
Each generated deck starts from it, which is why the output opens in PowerPoint with Admind's own master.

Layouts used (`LAYOUTS` in `builder.py`):

| Key | Layout name in the master | Used by |
|---|---|---|
| cover | Cover | cover |
| section | Chapter / Divider | section |
| content | Headline only | most content slides (title placeholder at top-left) |
| statement | Big statement | statement |
| photo | Content and photo | image |
| closing | Thank you | closing |
| end | End main | logo slide appended to every deck |

## Brand system (`brand.py`)

- **Colours**: `CREAM EDD9C2`, `CREAM_LIGHT F6EDE2`, `TEAL 29D9C2`, `TEAL_TEXT 1FA896`, `CORAL FF523D`,
  `GREEN 006C5B`, accents `PETROL`, `ORANGE`, `PEACH`, `PINK`, greys. Chart series cycle through
  `SERIES_COLORS = [TEAL, CORAL, GREEN, PEACH, PINK, PETROL]`.
- **Fonts**: `Acumin Pro`, `Acumin Pro Light`, `Acumin Pro Bold`.
- **Grid**: 13.333 x 7.5 in slide, 0.5 in margins, body area from y = 2.25 to 7.0 in.
- **Assets**: `catalog()` loads `engine/assets/catalog.json` (30 entries: 13 icons, 6 spheres, 5 hands,
  6 illustrations), `asset("icon/lightbulb")` returns the PNG path.

### Text fitting

The model respects word limits most of the time, but layouts must never overflow:

- `clamp_words(text, n)` cuts text to n words with an ellipsis (a second safety net after the schema limits).
- `fit_font_size(texts, width, height, max_pt, min_pt)` simulates word wrapping with an average glyph width
  (0.5 em by default) and returns the largest size at which all paragraphs fit the box.
- `fit_uniform(...)` returns one size for a row of boxes (cards, steps, milestones) so that siblings share the
  same font size - the smallest that fits all of them.

## Slide anatomy

Every content slide gets the same "chrome", as in the samples (`_chrome`):

- title in the layout's title placeholder, followed by a coral `_` run (`set_title`);
- an uppercase, letter-spaced eyebrow label at the top-left (the slide's kicker, max 4 words, or the current
  section title) with its own coral `_`;
- the slide number at the top-right;
- speaker notes from `notes`;
- empty placeholders removed so nothing says "Click to add text".

Visual groups (a KPI card, a process step) are built as **group shapes**, so a designer can move a card as one
object and the animation reveals them one by one.

## Per-type renderers

`DeckRenderer.render()` calls `r_<type>(content)` for each slide. If a renderer throws, the slide is re-rendered
as bullets built from all its strings, and the error is logged - a deck is always produced.

Notable details:

- **Cover** - hands at the exact positions/rotations measured in the sample covers (OK hand flipped and rotated
  121°, thumbs-up 326°, pointing finger 19°). Title box 7.6 in wide, bottom-anchored and auto-sized (30-60 pt),
  so long titles grow upward and never collide with the artwork. Subtitle skipped if equal to the date line.
- **Section** - divider orbit (9.76 x 5.11 in, rotated 23°), coral bar rotated 345°, cream sphere; number from
  a counter.
- **Bullets** - if the model picked no illustration, `pick_illustration` scores catalogue tags against the
  slide text (fallback "documents"). Up to 26 pt with 3 or fewer bullets.
- **KPIs** - number size fitted to the card width, colour from `sentiment`.
- **Chart** - see below.
- **Cards** - `distinct_icons` keeps the model's icon choice unless it is repeated on the slide; duplicates are
  replaced by the unused icon whose tags best match the card text.
- **Process** - numbered circles; generic labels such as "Step 1" or "01" are replaced by the step text.
- **Matrix** - axes are connectors with triangle arrowheads injected as XML; the y-axis label is a rotated box.
- **Table** - "No Style, No Grid" table style, then borders written as XML in the schema-mandated order
  (`lnL, lnR, lnT, lnB` before the fill - otherwise PowerPoint silently ignores them).

## Charts

`r_chart` builds a native chart with embedded data (editable in PowerPoint via "Edit data"):

1. **Unit sanitising** - units longer than 3 characters or words ("score", "employees") are dropped;
   allowed: `%`, `k`, `m`, `bn`, `pp`, `pts`, currency symbols.
2. **Number format** - decimals detected from the data (0, 1 or 2), thousands separator, `%` suffix, e.g.
   `#,##0.0"%"`.
3. **Type adjustments** - a column chart with long category labels becomes a bar chart; pie/doughnut use only
   the first series.
4. **Styling** (`style_chart`) - no chart title, no gridlines, hidden value axis, data labels on every point,
   category labels kept at the bottom even with negative values (`tick_label_position LOW`), bar charts in
   source order top-to-bottom, Admind series colours, doughnut hole 62%.
5. **Line charts with several series** (`label_line_ends`) - only the last point of each line is labelled, to
   avoid overlapping labels.
6. **Takeaways panel** on the right in light cream.

## Animations (`animate.py`)

python-pptx cannot create animations, so the XML is written directly:

- `add_fade_transition(slide)` - `<p:transition spd="med"><p:fade/></p:transition>` on every slide.
- `add_staggered_entrance(slide, shapes, step_ms=220, dur_ms=500, effect="fade"|"wipe")` - a `<p:timing>` tree
  whose main sequence starts automatically when the slide appears; each shape becomes visible and fades (or
  wipes up) 220 ms after the previous one. Elements are inserted in schema order (`cSld, clrMapOvr, transition,
  timing`), which PowerPoint requires.

What animates: KPI cards, chart and takeaways, cards, process steps, milestones, comparison columns, matrix
quadrants, agenda rows, table, quote; divider and closing orbits wipe in. Verified through PowerPoint's own
object model (`TimeLine.MainSequence.Count`). Animations can be disabled per job (`animations=false`).

## Previews (`preview.py`)

`soffice --headless --convert-to pdf` (with a throw-away LibreOffice profile so parallel conversions do not
clash), then PyMuPDF renders each page to PNG at 960 px. LibreOffice renders charts and shapes very close to
PowerPoint; animations are not shown in previews. Without the Acumin Pro font files in `engine/fonts/`, previews
use a fallback font, while the downloaded pptx still specifies Acumin Pro.

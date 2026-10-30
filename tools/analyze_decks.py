"""Dump structure of sample decks: layouts, fonts, colors, shape types, charts, text."""
import sys
import glob
import collections
from pptx import Presentation
from pptx.util import Emu
from pptx.enum.shapes import MSO_SHAPE_TYPE


def color_of(font):
    try:
        if font.color and font.color.type is not None and font.color.rgb is not None:
            return str(font.color.rgb)
    except Exception:
        pass
    return None


def walk(shapes):
    for s in shapes:
        yield s
        if s.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from walk(s.shapes)


def analyze(path, show_text=True, max_slides=None):
    prs = Presentation(path)
    print("=" * 100)
    print(path)
    print(f"size: {Emu(prs.slide_width).inches:.2f}in x {Emu(prs.slide_height).inches:.2f}in, slides={len(prs.slides)}")
    print("layouts:", [l.name for l in prs.slide_layouts])
    fonts, colors, types, fills = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    for i, slide in enumerate(prs.slides, 1):
        if max_slides and i > max_slides:
            break
        line = []
        for s in walk(slide.shapes):
            types[str(s.shape_type)] += 1
            try:
                if s.fill.type == 1:
                    fills[str(s.fill.fore_color.rgb)] += 1
            except Exception:
                pass
            if s.has_chart if hasattr(s, "has_chart") else False:
                ch = s.chart
                line.append(f"[CHART {ch.chart_type} series={[x.name for x in ch.plots[0].series]} cats={list(ch.plots[0].categories)[:6]}]")
            if s.has_text_frame and s.text_frame.text.strip():
                for p in s.text_frame.paragraphs:
                    for r in p.runs:
                        if r.font.name:
                            fonts[r.font.name] += 1
                        c = color_of(r.font)
                        if c:
                            colors[c] += 1
                t = s.text_frame.text.strip().replace("\n", " | ")
                line.append(t[:120])
            if s.shape_type == MSO_SHAPE_TYPE.PICTURE:
                line.append(f"[PIC {Emu(s.width).inches:.1f}x{Emu(s.height).inches:.1f}]")
            if getattr(s, "has_table", False) and s.has_table:
                line.append(f"[TABLE {len(s.table.rows)}x{len(s.table.columns)}]")
        if show_text:
            print(f"--- slide {i} layout={slide.slide_layout.name!r}")
            for l in line[:12]:
                print("   ", l)
    print("fonts:", fonts.most_common(10))
    print("text colors:", colors.most_common(12))
    print("fill colors:", fills.most_common(12))
    print("shape types:", types.most_common())


if __name__ == "__main__":
    paths = sys.argv[1:] or sorted(glob.glob("*.pptx"))
    for p in paths:
        analyze(p, max_slides=None)

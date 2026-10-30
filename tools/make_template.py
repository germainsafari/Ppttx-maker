"""Create engine/templates/admind_master.pptx: sample deck with all slides removed (keeps masters/layouts/theme).
Also writes a layout preview deck (one slide per layout, placeholders labelled) to tools/renders/layouts.pptx."""
import os
import sys
from pptx import Presentation

SRC = sys.argv[1] if len(sys.argv) > 1 else "Survey Dec 25 - Brand Advisory.pptx"
OUT = "engine/templates/admind_master.pptx"
os.makedirs(os.path.dirname(OUT), exist_ok=True)


def strip_slides(prs):
    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst):
        prs.part.drop_rel(sldId.rId)
        sldIdLst.remove(sldId)


prs = Presentation(SRC)
strip_slides(prs)
prs.save(OUT)
print("template:", OUT, os.path.getsize(OUT) // 1024, "KB")

prs = Presentation(OUT)
for layout in prs.slide_layouts:
    s = prs.slides.add_slide(layout)
    for ph in s.placeholders:
        f = ph.placeholder_format
        if f.type in (13, 15, 16):  # slide number/footer/date
            continue
        try:
            ph.text_frame.text = f"{layout.name} · idx{f.idx}"
        except Exception:
            pass
prs.save("tools/renders/layouts.pptx")
print("layout preview deck written")

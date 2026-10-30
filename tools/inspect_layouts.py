"""Print theme colors/fonts and placeholder geometry of every layout in a deck."""
import re
import sys
import zipfile
from pptx import Presentation
from pptx.util import Emu

path = sys.argv[1]
with zipfile.ZipFile(path) as z:
    themes = [n for n in z.namelist() if re.match(r"ppt/theme/theme\d+\.xml", n)]
    xml = z.read(themes[0]).decode("utf8")
    for tag in ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6"]:
        m = re.search(rf"<a:{tag}>.*?(?:srgbClr val|lastClr)=\"([0-9A-Fa-f]{{6}})\"", xml, re.S)
        print(tag, m.group(1) if m else None)
    print("major font:", re.search(r"<a:majorFont><a:latin typeface=\"([^\"]+)\"", xml).group(1))
    print("minor font:", re.search(r"<a:minorFont><a:latin typeface=\"([^\"]+)\"", xml).group(1))

prs = Presentation(path)
for i, l in enumerate(prs.slide_layouts):
    phs = []
    for ph in l.placeholders:
        f = ph.placeholder_format
        phs.append(f"{f.idx}:{f.type}:{ph.name}@({Emu(ph.left).inches:.1f},{Emu(ph.top).inches:.1f},{Emu(ph.width).inches:.1f}x{Emu(ph.height).inches:.1f})")
    print(f"[{i}] {l.name}: " + "; ".join(phs))

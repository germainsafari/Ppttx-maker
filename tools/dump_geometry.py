"""python tools/dump_geometry.py deck.pptx 1 2 19 -> shape geometry for given slides."""
import hashlib
import sys

from pptx import Presentation
from pptx.util import Emu

prs = Presentation(sys.argv[1])
for n in map(int, sys.argv[2:]):
    s = prs.slides[n - 1]
    print("--- slide", n)
    for sh in s.shapes:
        extra = ""
        if sh.shape_type == 13:
            extra = "img=" + hashlib.md5(sh.image.blob).hexdigest()[:10]
        flip = sh._element.xpath(".//a:xfrm/@flipH | .//a:xfrm/@flipV")
        print(f"  {sh.shape_type} {sh.name!r} x={Emu(sh.left).inches:.2f} y={Emu(sh.top).inches:.2f} "
              f"w={Emu(sh.width).inches:.2f} h={Emu(sh.height).inches:.2f} rot={sh.rotation:.0f} flip={flip} {extra}")

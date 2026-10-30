"""Extract unique pictures from sample decks (dedup by hash) into tools/assets_raw + contact sheet."""
import glob
import hashlib
import io
import os
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

OUT = "tools/assets_raw"
os.makedirs(OUT, exist_ok=True)
seen = {}


def walk(shapes):
    for s in shapes:
        if s.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from walk(s.shapes)
        else:
            yield s


for deck in sorted(glob.glob("*.pptx")):
    prs = Presentation(deck)
    for si, slide in enumerate(prs.slides, 1):
        for s in walk(slide.shapes):
            if s.shape_type != MSO_SHAPE_TYPE.PICTURE:
                continue
            try:
                blob, ext = s.image.blob, s.image.ext
            except Exception:
                continue
            h = hashlib.md5(blob).hexdigest()[:10]
            if h in seen:
                continue
            name = f"{h}.{ext}"
            with open(os.path.join(OUT, name), "wb") as f:
                f.write(blob)
            seen[h] = (deck[:30], si, name)

files = sorted(os.listdir(OUT))
print(len(files), "unique images")
W = 200
cols = 8
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (W * cols, W * rows), (200, 200, 200))
d = ImageDraw.Draw(sheet)
for k, fn in enumerate(files):
    try:
        im = Image.open(os.path.join(OUT, fn)).convert("RGBA")
    except Exception:
        continue
    im.thumbnail((W - 8, W - 20))
    x, y = (k % cols) * W, (k // cols) * W
    sheet.paste(im, (x + 4, y + 16), im)
    d.text((x + 4, y + 2), fn[:14], fill="black")
sheet.save("tools/renders/assets_sheet.png")

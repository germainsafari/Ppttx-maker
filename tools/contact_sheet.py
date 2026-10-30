"""python tools/contact_sheet.py <png_dir> [out.png] [cols]  -> grid of slide thumbnails."""
import glob
import os
import sys

from PIL import Image, ImageDraw

src = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(src, "_sheet.png")
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 3
files = sorted(f for f in glob.glob(os.path.join(src, "*.png")) if not os.path.basename(f).startswith("_"))
W, H = 640, 360
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols * W, rows * H), (90, 90, 90))
d = ImageDraw.Draw(sheet)
for k, f in enumerate(files):
    im = Image.open(f).convert("RGB").resize((W - 6, H - 6))
    x, y = (k % cols) * W, (k // cols) * H
    sheet.paste(im, (x + 3, y + 3))
    d.rectangle([x + 3, y + 3, x + 30, y + 20], fill="black")
    d.text((x + 7, y + 6), str(k + 1), fill="white")
sheet.save(out)
print(out)

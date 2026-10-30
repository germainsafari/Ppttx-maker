"""Copy curated brand assets from tools/assets_raw into engine/assets and write catalog.json."""
import json
import os
import shutil

RAW = "tools/assets_raw"
OUT = "engine/assets"
os.makedirs(OUT, exist_ok=True)

CATALOG = {
    "icon": {
        "lightbulb": ("36eb2be763.png", "idea insight innovation tip learning"),
        "teamwork": ("3ec764738a.png", "collaboration teamwork culture partnership cooperation"),
        "diamond": ("42829d49a3.png", "value quality premium strength excellence"),
        "plant": ("4f4b977c83.png", "growth sustainability development progress environment"),
        "crown": ("68d3bb6b25.png", "leadership best top winner board"),
        "magnifier": ("6a20a68bca.png", "research analysis search insight audit data"),
        "pencil": ("6fe6ffc063.png", "design creative writing content brand"),
        "bowl": ("836de91a70.png", "wellbeing benefits food care health"),
        "coin": ("9a405a830e.png", "finance money budget salary pay cost revenue"),
        "smiley": ("cfa16eec04.png", "satisfaction happiness people engagement experience"),
        "head": ("e3e5aad664.png", "strategy thinking mind mental communication"),
        "bicycle": ("f49e320bfb.png", "mobility journey balance movement transport"),
        "asterisk": ("fbedcb5695.png", "decoration spark"),
    },
    "sphere": {
        "teal": ("2ec4d95641.png", ""),
        "teal2": ("5e0285b8db.png", ""),
        "cream": ("47583b44d6.png", ""),
        "cream2": ("96a0f5773f.png", ""),
        "coral": ("d13bf293f0.png", ""),
        "coral2": ("fb99c961e1.png", ""),
    },
    "hand": {
        "ok_pink": ("4e381439f0.png", ""),
        "finger_red": ("5ab9c7ea13.png", ""),
        "finger_red2": ("ea15b491a9.png", ""),
        "teal_up": ("b0ca0a4902.png", ""),
        "thumb_teal": ("cd38e6f88f.png", ""),
    },
    "illustration": {
        "stairs": ("6bc1b7d575.png", "next steps progress roadmap growth climb plan"),
        "people_sphere": ("10e2a6a9c6.png", "team people community celebration culture"),
        "hands_heart": ("32dcf0a928.png", "care wellbeing love values support"),
        "documents": ("62f5251673.png", "research report documents analysis review"),
        "eyes": ("ccd7423e53.png", "vision perception attention brand awareness"),
        "logo_a": ("41c0162fb4.png", "admind logo"),
    },
}

catalog = {}
for kind, items in CATALOG.items():
    for name, (src, tags) in items.items():
        fn = f"{kind}_{name}{os.path.splitext(src)[1]}"
        shutil.copy(os.path.join(RAW, src), os.path.join(OUT, fn))
        catalog[f"{kind}/{name}"] = {"file": fn, "kind": kind, "tags": tags}

with open(os.path.join(OUT, "catalog.json"), "w") as f:
    json.dump(catalog, f, indent=1)
print(len(catalog), "assets")

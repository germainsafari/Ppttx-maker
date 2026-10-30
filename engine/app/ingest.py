"""Turn uploaded files into plain text (+ images) the LLM can read."""
import io
import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger("ingest")

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


@dataclass
class Source:
    name: str
    text: str = ""
    images: list[tuple[str, bytes]] = field(default_factory=list)  # (label, png/jpeg bytes)
    kind: str = "text"


def ingest_file(path: Path) -> Source:
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            return _pdf(path)
        if ext == ".docx":
            return _docx(path)
        if ext in (".xlsx", ".xlsm", ".xls"):
            return _excel(path)
        if ext == ".csv":
            return _csv(path)
        if ext == ".pptx":
            return _pptx(path)
        if ext in IMAGE_EXT:
            return Source(path.name, images=[(path.name, _normalize_image(path.read_bytes()))], kind="image")
        return Source(path.name, text=path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:  # a broken file should not kill the whole job
        log.exception("failed to ingest %s", path.name)
        return Source(path.name, text=f"[Could not read {path.name}: {e}]")


def _normalize_image(data: bytes, max_side: int = 1280) -> bytes:
    from PIL import Image

    im = Image.open(io.BytesIO(data))
    im = im.convert("RGB")
    im.thumbnail((max_side, max_side))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=85)
    return out.getvalue()


def _pdf(path: Path) -> Source:
    import fitz  # pymupdf

    doc = fitz.open(path)
    parts, images = [], []
    for i, page in enumerate(doc):
        txt = page.get_text("text").strip()
        if len(txt) < 40 and len(images) < 6:
            # Scanned or graphic page: keep a picture for the vision model.
            pix = page.get_pixmap(dpi=110)
            images.append((f"{path.name} p{i + 1}", _normalize_image(pix.tobytes("png"))))
        if txt:
            parts.append(f"--- page {i + 1} ---\n{txt}")
    return Source(path.name, text="\n".join(parts), images=images, kind="pdf")


def _docx(path: Path) -> Source:
    import docx

    d = docx.Document(str(path))
    parts = []
    for p in d.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        style = (p.style.name or "").lower() if p.style is not None else ""
        parts.append(("# " if style.startswith("heading") else "") + t)
    for ti, table in enumerate(d.tables):
        parts.append(f"[table {ti + 1}]")
        for row in table.rows:
            parts.append(" | ".join(c.text.strip() for c in row.cells))
    return Source(path.name, text="\n".join(parts), kind="docx")


def _frame_to_text(name: str, df) -> str:
    import pandas as pd

    df = df.dropna(how="all").dropna(axis=1, how="all")
    lines = [f"[sheet {name}: {df.shape[0]} rows x {df.shape[1]} cols]"]
    if df.shape[0] > 60:
        lines.append(df.head(40).to_csv(index=False))
        num = df.select_dtypes("number")
        if not num.empty:
            lines.append("summary statistics:\n" + num.describe().round(2).to_csv())
    else:
        lines.append(df.to_csv(index=False))
    return "\n".join(lines)


def _excel(path: Path) -> Source:
    import pandas as pd

    sheets = pd.read_excel(path, sheet_name=None)
    return Source(path.name, text="\n\n".join(_frame_to_text(n, df) for n, df in sheets.items()), kind="table")


def _csv(path: Path) -> Source:
    import pandas as pd

    df = pd.read_csv(path, sep=None, engine="python")
    return Source(path.name, text=_frame_to_text(path.stem, df), kind="table")


def _pptx(path: Path) -> Source:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    prs = Presentation(str(path))
    parts = []

    def walk(shapes):
        for s in shapes:
            if s.shape_type == MSO_SHAPE_TYPE.GROUP:
                yield from walk(s.shapes)
            else:
                yield s

    for i, slide in enumerate(prs.slides, 1):
        parts.append(f"--- slide {i} ---")
        for s in walk(slide.shapes):
            if s.has_text_frame and s.text_frame.text.strip():
                parts.append(s.text_frame.text.strip())
            if getattr(s, "has_chart", False) and s.has_chart:
                try:
                    plot = s.chart.plots[0]
                    cats = list(plot.categories)
                    for ser in plot.series:
                        vals = list(ser.values)
                        parts.append(f"[chart series '{ser.name}': " +
                                     ", ".join(f"{c}={round(v, 4):g}" if isinstance(v, float) else f"{c}={v}"
                                               for c, v in zip(cats, vals)) + "]")
                except Exception:
                    pass
            if getattr(s, "has_table", False) and s.has_table:
                for row in s.table.rows:
                    parts.append(" | ".join(c.text.strip() for c in row.cells))
    return Source(path.name, text="\n".join(parts), kind="pptx")

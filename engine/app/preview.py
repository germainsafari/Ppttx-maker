"""Slide thumbnails: LibreOffice (in Docker/Linux) -> PDF -> PNG with PyMuPDF."""
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger("preview")


def soffice_bin() -> str | None:
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe", "/usr/lib/libreoffice/program/soffice"):
        if Path(p).exists():
            return p
    return None


def render_previews(pptx: Path, out_dir: Path, width: int = 960) -> list[Path]:
    exe = soffice_bin()
    if not exe:
        log.info("LibreOffice not found; skipping previews")
        return []
    import fitz

    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        profile = Path(tmp) / "profile"
        cmd = [exe, f"-env:UserInstallation=file:///{profile.as_posix().lstrip('/')}", "--headless",
               "--convert-to", "pdf", "--outdir", tmp, str(pptx)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=180)
        except (subprocess.SubprocessError, OSError) as e:
            log.warning("preview conversion failed: %s", e)
            return []
        pdf = Path(tmp) / (pptx.stem + ".pdf")
        if not pdf.exists():
            return []
        doc = fitz.open(pdf)
        paths = []
        for i, page in enumerate(doc, 1):
            zoom = width / page.rect.width
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            p = out_dir / f"{i:02d}.png"
            pix.save(p)
            paths.append(p)
        doc.close()
        return paths

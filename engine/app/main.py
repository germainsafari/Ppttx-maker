"""HTTP API of the deck engine. Runs next to the GPU; exposed only through the Cloudflare tunnel."""
import asyncio
import json
import logging
import re
import shutil
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .auth import require_auth
from .config import settings
from .llm import LLM
from .pipeline import Options, Pipeline, fact_check
from .preview import render_previews
from .render.builder import render_deck
from .schema import CONTENT_MODELS, DeckSpec

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("engine")

JOBS_DIR = settings.data_dir / "jobs"
ALLOWED_EXT = {".pdf", ".docx", ".pptx", ".xlsx", ".xlsm", ".csv", ".txt", ".md", ".json",
               ".png", ".jpg", ".jpeg", ".webp"}
MAX_JOBS_RUNNING = 2

state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    llm = LLM()
    try:
        info = await llm.init()
        log.info("LLM ready: %s", info)
    except Exception as e:  # engine still starts; /api/health reports the problem
        log.error("LLM not reachable at %s: %s", settings.llm_base_url, e)
    state["llm"] = llm
    state["slots"] = asyncio.Semaphore(MAX_JOBS_RUNNING)
    state["cleanup"] = asyncio.create_task(_cleanup_loop())
    yield
    state["cleanup"].cancel()
    await llm.close()


app = FastAPI(title="Admind Deck Engine", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"],
                   allow_credentials=False)


# ------------------------------------------------------------------ job storage
def _job_dir(job_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        raise HTTPException(404, "job not found")
    d = JOBS_DIR / job_id
    if not d.exists():
        raise HTTPException(404, "job not found")
    return d


def _read(job_id: str) -> dict:
    return json.loads((_job_dir(job_id) / "job.json").read_text(encoding="utf-8"))


def _write(d: Path, data: dict):
    tmp = d / "job.json.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(d / "job.json")


async def _cleanup_loop():
    while True:
        cutoff = time.time() - settings.job_retention_hours * 3600
        for d in JOBS_DIR.glob("*"):
            if d.is_dir() and d.stat().st_mtime < cutoff:
                shutil.rmtree(d, ignore_errors=True)
        await asyncio.sleep(3600)


# ------------------------------------------------------------------ endpoints
@app.get("/api/health")
async def health():
    llm: LLM = state["llm"]
    try:
        info = await llm.init()
        return {"ok": True, "llm": info, "vision": llm.supports_vision}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/jobs")
async def create_job(
    prompt: str = Form(...),
    slide_count: int = Form(10),
    language: str = Form("auto"),
    animations: bool = Form(True),
    files: list[UploadFile] = File(default=[]),
    user: str = Depends(require_auth),
):
    if not prompt.strip():
        raise HTTPException(400, "prompt is required")
    job_id = uuid.uuid4().hex
    d = JOBS_DIR / job_id
    (d / "input").mkdir(parents=True)
    saved = []
    total = 0
    for f in files:
        name = Path(f.filename or "file").name
        if Path(name).suffix.lower() not in ALLOWED_EXT:
            shutil.rmtree(d, ignore_errors=True)
            raise HTTPException(400, f"unsupported file type: {name}")
        data = await f.read()
        total += len(data)
        if total > settings.max_upload_mb * 1024 * 1024:
            shutil.rmtree(d, ignore_errors=True)
            raise HTTPException(413, f"upload larger than {settings.max_upload_mb} MB")
        p = d / "input" / name
        p.write_bytes(data)
        saved.append(p)
    job = {"id": job_id, "status": "queued", "progress": 0.0, "message": "Queued", "created": time.time(),
           "user": user, "prompt": prompt, "files": [p.name for p in saved],
           "options": {"slide_count": max(3, min(25, slide_count)), "language": language, "animations": animations},
           "warnings": [], "timings": {}, "previews": 0}
    _write(d, job)
    asyncio.create_task(_run_job(job_id))
    return {"id": job_id}


async def _run_job(job_id: str):
    d = JOBS_DIR / job_id
    job = _read(job_id)

    def progress(msg: str, p: float):
        job.update(message=msg, progress=round(p, 3), status="running")
        _write(d, job)

    async with state["slots"]:
        try:
            progress("Starting", 0.01)
            llm: LLM = state["llm"]
            await llm.init()
            opts = Options(**job["options"])
            files = [d / "input" / n for n in job["files"]]
            res = await Pipeline(llm).run(job["prompt"], files, d, opts, progress)
            job.update(warnings=res.warnings, timings=res.timings, model=llm.model)
            if settings.render_previews:
                progress("Rendering previews", 0.95)
                pngs = await asyncio.to_thread(render_previews, res.pptx, d / "previews")
                job["previews"] = len(pngs)
            job.update(status="done", progress=1.0, message="Ready", finished=time.time())
        except Exception as e:
            log.exception("job %s failed", job_id)
            job.update(status="error", message=f"{type(e).__name__}: {e}"[:500])
        _write(d, job)


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str, user: str = Depends(require_auth)):
    job = _read(job_id)
    job.pop("user", None)
    return job


@app.get("/api/jobs/{job_id}/deck.pptx")
async def download(job_id: str, user: str = Depends(require_auth)):
    d = _job_dir(job_id)
    p = d / "deck.pptx"
    if not p.exists():
        raise HTTPException(404, "deck not ready")
    title = "presentation"
    try:
        title = json.loads((d / "deck.json").read_text(encoding="utf-8"))["title"]
    except Exception:
        pass
    safe = re.sub(r"[^\w\- ]+", "", title).strip().replace(" ", "_")[:60] or "presentation"
    return FileResponse(p, filename=f"{safe}.pptx",
                        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")


@app.get("/api/jobs/{job_id}/previews/{n}.png")
async def preview(job_id: str, n: int, user: str = Depends(require_auth)):
    p = _job_dir(job_id) / "previews" / f"{n:02d}.png"
    if not p.exists():
        raise HTTPException(404, "no preview")
    return FileResponse(p, media_type="image/png")


@app.get("/api/jobs/{job_id}/spec")
async def get_spec(job_id: str, user: str = Depends(require_auth)):
    p = _job_dir(job_id) / "deck.json"
    if not p.exists():
        raise HTTPException(404, "spec not ready")
    return json.loads(p.read_text(encoding="utf-8"))


class ReviseBody(BaseModel):
    slide: int  # 1-based
    instruction: str


@app.post("/api/jobs/{job_id}/revise")
async def revise(job_id: str, body: ReviseBody, user: str = Depends(require_auth)):
    """Rewrite one slide with an instruction ("make it shorter", "turn into a chart"...), then re-render."""
    d = _job_dir(job_id)
    deck = DeckSpec.model_validate_json((d / "deck.json").read_text(encoding="utf-8"))
    idx = body.slide - 1
    if not 0 <= idx < len(deck.slides):
        raise HTTPException(400, "bad slide number")
    if deck.slides[idx].type not in CONTENT_MODELS:
        raise HTTPException(400, "slide type cannot be revised")
    from .ingest import ingest_file

    source_text = "\n".join(ingest_file(p).text for p in (d / "input").glob("*"))
    llm: LLM = state["llm"]
    await llm.init()
    deck.slides[idx] = await Pipeline(llm).revise_slide(deck, idx, body.instruction, source_text)
    prompt = _read(job_id)["prompt"]
    warnings = [w.replace("Slide 1 ", f"Slide {body.slide} ", 1)
                for w in fact_check([deck.slides[idx]], source_text, prompt + " " + body.instruction)]
    await _rerender(d, deck)
    return {"ok": True, "slide": deck.slides[idx].model_dump(), "warnings": warnings}


@app.put("/api/jobs/{job_id}/spec")
async def put_spec(job_id: str, deck: DeckSpec, user: str = Depends(require_auth)):
    """Manual edits: save an edited spec and re-render without calling the LLM."""
    d = _job_dir(job_id)
    await _rerender(d, deck)
    return {"ok": True}


async def _rerender(d: Path, deck: DeckSpec):
    job = json.loads((d / "job.json").read_text(encoding="utf-8"))
    (d / "deck.json").write_text(deck.model_dump_json(indent=1), encoding="utf-8")
    from .ingest import ingest_file

    images = [img for p in (d / "input").glob("*") for _, img in ingest_file(p).images][:8]
    await asyncio.to_thread(render_deck, deck, d / "deck.pptx", images, job["options"].get("animations", True))
    if settings.render_previews:
        shutil.rmtree(d / "previews", ignore_errors=True)
        job["previews"] = len(await asyncio.to_thread(render_previews, d / "deck.pptx", d / "previews"))
    job["revision"] = job.get("revision", 0) + 1
    _write(d, job)

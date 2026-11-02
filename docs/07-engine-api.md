# 07 - Engine API

FastAPI app in `engine/app/main.py`, served by uvicorn on port 8090. Interactive OpenAPI docs are available at
`http://localhost:8090/docs`.

## Authentication (`auth.py`)

Every endpoint except `/api/health` requires one of:

| Method | How | Used by |
|---|---|---|
| API key | header `X-API-Key: <key>`; keys listed comma-separated in `ENGINE_API_KEYS` | scripts, server-to-server |
| Signed token | header `Authorization: Bearer <token>` or query `?token=<token>` | the web app's browser code (the query form is needed for `<img>` previews and download links) |

Token format: `base64url(JSON{"sub": "...", "exp": unix_seconds}) + "." + base64url(HMAC-SHA256(secret, payload))`
with `secret = ENGINE_TOKEN_SECRET`. The web app mints tokens valid for 2 hours. Verification uses a
constant-time comparison and checks expiry.

If neither `ENGINE_API_KEYS` nor `ENGINE_TOKEN_SECRET` is set, the engine runs **without authentication**
(local development only). Unauthenticated requests otherwise get `401`.

CORS: browser origins allowed by `CORS_ORIGINS` (comma-separated), e.g. the Vercel domain and
`http://localhost:3000`.

## Endpoints

### `GET /api/health`
```json
{"ok": true, "llm": {"model": "qwen3.6-35b-a3b", "max_model_len": 65536}, "vision": true}
```
`ok: false` with an error message if vLLM is unreachable.

### `POST /api/jobs`
Multipart form:

| Field | Default | |
|---|---|---|
| `prompt` | required | the brief |
| `slide_count` | 10 | clamped to 3-25 |
| `language` | `auto` | `auto` = language of the prompt, or e.g. `English`, `Polish` |
| `animations` | `true` | transitions and entrance animations |
| `files` | none | repeatable; allowed: pdf, docx, pptx, xlsx, xlsm, csv, txt, md, json, png, jpg, jpeg, webp; total max `MAX_UPLOAD_MB` (50) |

Returns `{"id": "<32 hex chars>"}` immediately; generation runs in the background.

### `GET /api/jobs/{id}`
```json
{
  "id": "48cd92...", "status": "done", "progress": 1.0, "message": "Ready",
  "prompt": "...", "files": ["Survey Dec 25 - Brand Advisory.pptx"],
  "options": {"slide_count": 10, "language": "auto", "animations": true},
  "warnings": ["Slide 3 (chart): please verify 69 (not in the sources - derived or invented)"],
  "timings": {"ingest": 0.4, "condense": 0.0, "outline": 6.4, "slides": 4.3, "render": 0.15, "total": 11.3},
  "previews": 12, "model": "qwen3.6-35b-a3b", "revision": 1
}
```
`status`: `queued` -> `running` -> `done` | `error` (then `message` holds the error).
Progress messages: Reading files, Reading images with the vision model, Condensing long documents, Planning the
storyline, Writing slides (k/n), Rendering PowerPoint, Rendering previews, Ready.

### `GET /api/jobs/{id}/deck.pptx`
The PowerPoint file, with a download name derived from the deck title.

### `GET /api/jobs/{id}/previews/{n}.png`
1-based slide preview, 960 px wide.

### `GET /api/jobs/{id}/spec` / `PUT /api/jobs/{id}/spec`
Read the `DeckSpec` JSON ([04](04-slide-schema.md)); write an edited one to re-render the pptx and previews
without calling the model.

### `POST /api/jobs/{id}/revise`
```json
{"slide": 3, "instruction": "Make it shorter and focus on the eNPS change"}
```
Rewrites one slide (same type) with the model, fact-checks it, re-renders. Returns
`{"ok": true, "slide": {...}, "warnings": [...]}`. Increments `revision` in the job so clients can bust image
caches. `400` for a slide number outside the deck.

## Job storage

```
/data/jobs/<id>/
  job.json          status, options, warnings, timings (written atomically via job.json.tmp)
  input/            uploaded files
  outline.json      normalised outline
  deck.json         DeckSpec
  deck.pptx
  previews/01.png ...
```

`/data` is the `engine-data` Docker volume. A background loop deletes job folders older than
`JOB_RETENTION_HOURS` (72) every hour. Job ids are random UUID4 hex strings and validated by regex before any
filesystem access.

## Limits and queueing

- 2 jobs generate concurrently (`MAX_JOBS_RUNNING`); more wait as `queued`.
- Within a job, slide calls run in parallel up to `LLM_CONCURRENCY`.
- Cloudflare's free plan caps request bodies at 100 MB; the engine caps uploads at 50 MB.

## Calling it from a script

```python
import httpx, time
c = httpx.Client(base_url="https://slides-api.admindagency.com", headers={"X-API-Key": "ak_..."}, timeout=120)
job = c.post("/api/jobs", data={"prompt": "Board summary", "slide_count": "8"},
             files=[("files", ("survey.pptx", open("survey.pptx", "rb")))]).json()
while (j := c.get(f"/api/jobs/{job['id']}").json())["status"] not in ("done", "error"):
    time.sleep(1)
open("deck.pptx", "wb").write(c.get(f"/api/jobs/{job['id']}/deck.pptx").content)
```

`engine/tests/e2e_api.py` is a complete example (including token minting and revise).

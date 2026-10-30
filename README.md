# Admind Deck Builder

Upload files + write a brief -> get an editable, on-brand PowerPoint. Everything runs on the Admind GPU
workstation (RTX 5090, 32 GB). No document or prompt is ever sent to OpenAI, Anthropic or any other cloud model.

```
 Browser ──(1) page + short-lived token──> Vercel (web/, Next.js)        holds no data, no model
    │
    └──(2) files + prompt, direct upload──> slides-api.admindagency.com   Cloudflare tunnel (same as lt.admindagency.com)
                                               │
                                               ▼
                                   deck-engine :8090 (engine/, FastAPI)   parsing, planning, rendering, previews
                                               │ OpenAI-compatible API, local only
                                               ▼
                                   vllm :8080  Qwen3.6-35B-A3B (NVFP4)    the only "AI" in the system
```

## How a deck is made

1. **Ingest** - PDF, Word, PowerPoint (text, tables *and chart data*), Excel/CSV, text, images. Scanned pages and
   images are read by the model's vision.
2. **Plan** - the model returns a storyline as JSON (slide types: kpis, chart, cards, process, timeline,
   comparison, matrix, table, quote, statement, image, ...). vLLM *structured outputs* force valid JSON matching
   our schema, so a small local model cannot "break" the format.
3. **Write** - every slide is filled in parallel, again schema-constrained (8 slides ~ 3 s).
4. **Check** - code fixes deck grammar (cover / agenda / dividers / closing), and every number on a slide is
   checked against the sources; anything not found is shown as a warning ("please verify 69 ...").
5. **Render** - Python code draws the slides into the Admind master (`engine/templates/admind_master.pptx`,
   extracted from the team's decks): native editable charts, tables, KPI cards, icons, the hands/spheres
   artwork, coral `_` titles, fade transitions and staggered entrance animations.

This is the "Claude approach" adapted to a small model: the LLM never draws, it only decides *what* to say and
*which* visual to use; deterministic code does the graphics. That is why a 3B-active-parameter model gives
consistent, brand-correct output.

## Model choice (measured on this GPU)

| | Qwen2.5-VL-7B (previous) | **Qwen3.6-35B-A3B NVFP4 (now)** |
|---|---|---|
| VRAM | 7B in bf16 | ~28 GB incl. 412k-token KV cache |
| Context | 4 096 (sources had to be summarised first) | 65 536 (up to 262k possible) |
| Speed | 77 tok/s effective in the deck pipeline | 185 tok/s single, 660 tok/s with 8 parallel |
| 10-slide deck | 22 s, repetitive, invented numbers | 6-13 s, varied layouts, real numbers |
| Vision | yes | yes |

NVFP4 is the RTX 50-series native 4-bit format, so the 35B mixture-of-experts model fits in 32 GB and runs as
fast as a 3B model. Alternatives if needed: `Qwen/Qwen3-VL-8B-Instruct-FP8` (lighter, ~12 GB, weaker planning),
`google/gemma-3-27b-it` (no NVFP4, slower).

## Run it (GPU workstation)

```powershell
cd infra
copy .env.example .env        # fill ENGINE_TOKEN_SECRET (+ CORS_ORIGINS with the Vercel domain)
docker compose up -d --build  # vllm (first start downloads ~22 GB) + deck-engine
curl http://localhost:8090/api/health
```

Both containers have `restart: unless-stopped`, so they come back after a reboot once Docker Desktop starts.

CLI without the web app: `cd engine; .venv\Scripts\python -m app.cli -p "brief..." -f file.pptx -n 10 -o out`

## Expose through Cloudflare (same as LanguageTool)

The workstation already runs the `Cloudflared` Windows service (dashboard-managed tunnel that serves
lt.admindagency.com). In Cloudflare Zero Trust -> Networks -> Tunnels -> that tunnel -> **Public hostname -> Add**:

- Subdomain `slides-api`, domain `admindagency.com`
- Service `HTTP`, URL `localhost:8090`
- Additional settings -> HTTP settings: no change needed. Uploads up to 100 MB pass on the Free plan.

Do **not** publish port 8080 (vLLM has no authentication). Only the engine is public, and it requires a token.

## Deploy the web app on Vercel

- Import the repo, **Root directory: `web`**, framework Next.js.
- Environment variables:
  - `ENGINE_URL=https://slides-api.admindagency.com`
  - `ENGINE_TOKEN_SECRET=` same value as in `infra/.env`
  - `APP_PASSWORD=` team password (basic auth; any username)
- Add the Vercel domain (e.g. `https://slides.admindagency.com`) to `CORS_ORIGINS` in `infra/.env`, then
  `docker compose up -d engine`.

Files go from the browser straight to the tunnel, so Vercel's 4.5 MB body limit does not apply and Vercel never
sees the content. For company SSO, put Cloudflare Access (Microsoft Entra / Google) in front of both hostnames
instead of `APP_PASSWORD`.

## Security model

- Engine accepts either `X-API-Key` (scripts, `ENGINE_API_KEYS`) or a 2-hour HMAC token minted by the web app.
  With neither configured it runs open - local development only.
- Uploads: extension allow-list, 50 MB cap, jobs deleted after 72 h (`JOB_RETENTION_HOURS`).
- The model has no internet access and no tools; it only returns JSON.

## Fonts

Decks specify Acumin Pro (Admind's font). PowerPoint on Admind machines shows it correctly. For identical
server-side previews, copy the licensed `.otf` files into `engine/fonts/` and rebuild the engine.

## Tests

```powershell
cd engine
$env:PYTHONPATH="."; .venv\Scripts\python tests\render_fixture.py          # every slide type, no LLM
powershell -File tests\run_scenarios.ps1                                   # 3 real briefs in parallel
.venv\Scripts\python tests\e2e_api.py --secret <ENGINE_TOKEN_SECRET> -f "..\Survey Dec 25 - Brand Advisory.pptx"
```

## Rollback to the previous model

```powershell
docker compose -f infra/docker-compose.yml stop vllm
wsl -e bash ~/serve_qwen25vl7b.sh      # original Qwen2.5-VL-7B on :8080
```

The engine reads the model name and context size from `/v1/models` and adapts its budgets automatically.

## Repository map

- `engine/app/` - `pipeline.py` (plan/write/check), `prompts.py` (house style), `schema.py` (slide types),
  `render/` (brand, layouts, animation XML), `main.py` (API), `ingest.py`
- `engine/templates`, `engine/assets` - master and artwork extracted from the sample decks (`tools/`)
- `web/` - Next.js front end; `infra/` - compose, WSL scripts

# 11 - Code map

Every file in the repository and its role. Generated folders (`engine/.venv`, `engine/data`, `engine/tests/out`,
`web/node_modules`, `web/.next`, `tools/renders`) are ignored by git.

## Root

| File | |
|---|---|
| `README.md` | What the project does and how to run it |
| `docs/` | This documentation; `docs/img/` screenshots and contact sheets |
| `*.pptx` (6 files) | The team's sample decks; source of the template, artwork and style rules. Read-only inputs. |
| `.gitignore` | Excludes secrets (`.env`, `.env.local`), virtualenvs, build output, job data |
| `.gitattributes` | Forces LF line endings for `*.sh` and Dockerfiles (they run in Linux), marks pptx as binary |

## `engine/` - Python service

| File | Responsibility |
|---|---|
| `Dockerfile` | Python 3.12 slim + LibreOffice + fonts; runs `uvicorn app.main:app` on 8090 |
| `.dockerignore` | Keeps `.venv`, job data, test outputs and bytecode out of the image |
| `requirements.txt` | fastapi, uvicorn, python-multipart, httpx, pydantic, python-pptx, pymupdf, python-docx, openpyxl, pandas, pillow, lxml |
| `fonts/README.txt` | Where to drop licensed Acumin Pro files |
| `templates/admind_master.pptx` | Admind master (40 layouts, theme), no slides |
| `assets/*.png`, `assets/catalog.json` | 30 brand images (icons, spheres, hands, illustrations) with tags |

### `engine/app/`

| File | Key contents |
|---|---|
| `config.py` | `Settings` read from environment variables (see [09](09-deployment.md)) |
| `main.py` | FastAPI app: lifespan (LLM init, cleanup loop), job endpoints, `_run_job`, revise, spec, re-render, job storage helpers |
| `auth.py` | `mint_token`, `verify_token` (HMAC), `require_auth` dependency (API key or token) |
| `cli.py` | Terminal entry point wrapping `Pipeline.run` |
| `llm.py` | `LLM` client for vLLM: `init` (model + context), `chat` (JSON-schema response format, thinking off), `structured` (validate + retry), stats; `image_part`, `approx_tokens` |
| `ingest.py` | `ingest_file` -> `Source(text, images)` for pdf/docx/xlsx/csv/pptx/images/text |
| `prompts.py` | `HOUSE_STYLE` system prompt; `outline_messages`, `slide_messages`, `revise_messages`, `condense_messages`, `IMAGE_DESCRIBE` |
| `schema.py` | Slide types, outline models, the 16 content models, `CONTENT_MODELS`, `SlideSpec`, `DeckSpec` |
| `pipeline.py` | `Pipeline.run` (ingest -> images -> condense -> outline -> slides -> fact check -> render), `revise_slide`, retrieval (`_chunks`, `_relevant`), `_normalize_outline`, `_fix_sections_and_agenda`, `fact_check` |
| `preview.py` | LibreOffice -> PDF -> PNG previews |
| `render/brand.py` | Colours, fonts, grid constants, asset catalogue, `fit_font_size`, `fit_uniform`, `clamp_words` |
| `render/builder.py` | Drawing helpers (`text_box`, `rect`, `line`, `picture`, `orbit`, `set_title`), `pick_illustration`, `distinct_icons`, `DeckRenderer` with `r_<type>` per slide type, chart/table styling, `render_deck` |
| `render/animate.py` | Fade transition and staggered entrance animation XML |

### `engine/tests/`

| File | |
|---|---|
| `fixture_deck.json` | Hand-written DeckSpec with every slide type |
| `render_fixture.py` | Renders the fixture (no model) |
| `smoke_llm.py` | Speed, JSON-schema and vision checks against vLLM |
| `make_inputs.py` | Creates `inputs/campaign_q3.xlsx` (fictional Northwind Energy campaign) |
| `inputs/admind_website.txt` | Public website text for the credentials scenario |
| `run_scenarios.ps1` | Three parallel CLI runs + PowerPoint PNG export + contact sheets |
| `e2e_api.py` | End-to-end HTTP test incl. auth and revise |

## `web/` - Next.js front end

| File | |
|---|---|
| `package.json`, `tsconfig.json`, `next.config.mjs`, `next-env.d.ts` | Project setup (Next 15, React 19, TypeScript) |
| `.env.example` | `ENGINE_URL`, `ENGINE_TOKEN_SECRET`, `APP_PASSWORD` |
| `middleware.ts` | Session gate: redirect to `/login` or 401 |
| `lib/session.ts` | Signed session cookie (Web Crypto HMAC) |
| `app/layout.tsx` | HTML shell, title |
| `app/globals.css` | Admind-styled UI |
| `app/page.tsx` | Builder UI: form, upload, progress, previews, revise |
| `app/login/page.tsx` | Password form |
| `app/api/login/route.ts` | Sign in / sign out |
| `app/api/token/route.ts` | Mints engine tokens |

## `infra/`

| File | |
|---|---|
| `docker-compose.yml` | `vllm`, `engine`, optional `cloudflared`; volumes `hf-cache`, `engine-data` |
| `.env.example` | Secrets and options for compose (`.env` is the real, uncommitted file) |
| `wsl/serve_qwen25vl7b.sh` | Original Qwen2.5-VL-7B command (rollback) |
| `wsl/serve_qwen36.sh` | Qwen3.6 in WSL with stable vLLM (does not work with vLLM 0.19; reference) |
| `wsl/hf_download_ipv4.py` | Model download forcing IPv4 and disabling Xet (WSL networking workaround) |
| `wsl/download_model.sh` | Earlier download attempt (superseded by the Python script) |

## `tools/` - analysis and asset extraction (run once, from the repo root)

| File | |
|---|---|
| `analyze_decks.py` | Dumps layouts, fonts, colours, shape types, charts and text of the sample decks -> `analysis.txt` |
| `inspect_layouts.py` | Theme colours/fonts and placeholder geometry per layout |
| `dump_geometry.py` | Exact position/size/rotation of shapes on given slides (used to copy cover/divider/closing art) |
| `make_template.py` | Builds `engine/templates/admind_master.pptx` (+ a labelled layout preview deck) |
| `extract_assets.py` | Extracts unique pictures from all sample decks into `assets_raw/` with a contact sheet |
| `build_asset_catalog.py` | Copies the curated images to `engine/assets/` with names, kinds and tags -> `catalog.json` |
| `render_pptx_windows.ps1` | Exports every slide to PNG with desktop PowerPoint (COM) |
| `contact_sheet.py` | Grid image of slide PNGs |
| `lf.py` | Converts files to LF / UTF-8 (shell scripts edited on Windows) |
| `analysis.txt` | Output of the deck analysis |
| `assets_raw/` | All pictures found in the sample decks, named by hash |

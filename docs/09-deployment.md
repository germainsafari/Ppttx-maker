# 09 - Deployment and operations

## Target setup

```
https://slides.admindagency.com      -> Vercel (web/)                     public, password / SSO
https://slides-api.admindagency.com  -> Cloudflare tunnel -> localhost:8090 (deck-engine)   token required
localhost:8080                        vLLM - never published
```

This mirrors the existing LanguageTool setup (`lt.admindagency.com` -> tunnel -> `localhost:8081`).

## 1. GPU workstation: Docker stack

Prerequisites: Docker Desktop with the WSL 2 backend and GPU support (`docker run --gpus all ...` works),
NVIDIA driver supporting the RTX 5090.

```powershell
cd infra
copy .env.example .env
```

`infra/.env`:

| Variable | Value |
|---|---|
| `ENGINE_TOKEN_SECRET` | random, e.g. `python -c "import secrets;print(secrets.token_urlsafe(48))"`. Same value goes to Vercel. |
| `ENGINE_API_KEYS` | optional comma-separated keys for scripts |
| `CORS_ORIGINS` | `https://slides.admindagency.com,http://localhost:3000` |
| `CLOUDFLARE_TUNNEL_TOKEN` | only if you use the compose `cloudflared` service (not needed with the existing Windows service) |
| `VLLM_MAX_MODEL_LEN`, `VLLM_GPU_UTIL` | optional overrides (65536, 0.88) |

```powershell
docker compose up -d --build          # vllm + engine
docker compose ps                     # both "healthy" after the model has loaded
curl http://localhost:8090/api/health
```

Services (`infra/docker-compose.yml`, project name `admind-decks`):

| Service | Container | Port | Volume | Restart |
|---|---|---|---|---|
| `vllm` | `vllm` | 8080 -> 8000 | `hf-cache` (weights) | unless-stopped |
| `engine` | `deck-engine` | 8090 | `engine-data` (jobs) | unless-stopped |
| `cloudflared` | - | - | - | optional, profile `tunnel` |

With `restart: unless-stopped`, both come back after a reboot as soon as Docker Desktop starts (enable "Start
Docker Desktop when you sign in", or run it as a service).

The engine image (`engine/Dockerfile`): Python 3.12 slim + LibreOffice Impress + fallback fonts, the Python
requirements, `engine/fonts/*` installed as system fonts, the app, the template and the assets.

### Fonts

Put Admind's licensed Acumin Pro `.otf` files into `engine/fonts/` and rebuild (`docker compose up -d --build
engine`) for pixel-accurate previews. The generated pptx references Acumin Pro regardless; it displays correctly
on any machine that has the font.

## 2. Cloudflare tunnel

The workstation already runs the **Cloudflared** Windows service with a dashboard-managed tunnel (token in
`C:\ProgramData\cloudflared`). Add a hostname to that tunnel:

1. Cloudflare dashboard -> Zero Trust -> Networks -> Tunnels -> the existing tunnel -> **Public Hostname** ->
   **Add a public hostname**.
2. Subdomain `slides-api`, domain `admindagency.com`, type `HTTP`, URL `localhost:8090`.
3. Save. `https://slides-api.admindagency.com/api/health` should answer within a minute.

Do not add a hostname for port 8080.

Alternative without the Windows service: put the tunnel token in `infra/.env` and run
`docker compose --profile tunnel up -d`; then the service URL is `http://engine:8090`.

## 3. Vercel

1. New project from the repository, **Root Directory = `web`**, framework preset Next.js.
2. Environment variables: `ENGINE_URL=https://slides-api.admindagency.com`, `ENGINE_TOKEN_SECRET` (same as the
   engine), `APP_PASSWORD`.
3. Domain: add `slides.admindagency.com` (CNAME to Vercel), and make sure it is in the engine's `CORS_ORIGINS`
   (`docker compose up -d engine` after editing `.env`).

## 4. Optional: single sign-on with Cloudflare Access

Zero Trust -> Access -> Applications -> add a self-hosted application for `slides.admindagency.com`
(and `slides-api.admindagency.com`), identity provider Microsoft Entra ID or Google, policy "emails ending in
@admindagency.com". If the web app is on Vercel, protect it with Vercel's own password/SSO or move it behind
the tunnel too (`npm run build && npm start` on the workstation, hostname -> `localhost:3000`).

## Configuration reference (engine)

| Variable | Default | |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:8080/v1` | |
| `LLM_MODEL` | first served model | |
| `LLM_CONCURRENCY` | 6 | |
| `LLM_DISABLE_THINKING` | 1 | |
| `LLM_TIMEOUT` | 600 | seconds |
| `ENGINE_API_KEYS` | empty | |
| `ENGINE_TOKEN_SECRET` | empty | both empty = no auth |
| `CORS_ORIGINS` | `http://localhost:3000` | |
| `DATA_DIR` | `engine/data` (Docker: `/data`) | |
| `TEMPLATE_PATH` | `engine/templates/admind_master.pptx` | |
| `ASSETS_DIR` | `engine/assets` | |
| `MAX_UPLOAD_MB` | 50 | |
| `JOB_RETENTION_HOURS` | 72 | |
| `RENDER_PREVIEWS` | 1 | |
| `CONTACT_LINE` | `admindagency.com` | text on the closing slide |

## Day-to-day operations

```powershell
cd infra
docker compose ps
docker compose logs -f engine                 # job logs, every LLM call with token counts and duration
docker compose logs -f vllm
docker compose up -d --build engine           # deploy engine code changes (about 10 s)
docker compose restart vllm                   # model server restart (1-3 min to load)
docker compose down                           # stop everything (volumes kept)
```

Updating vLLM: `docker compose pull vllm && docker compose up -d vllm`. Nightly images can change behaviour;
pin a digest (`vllm/vllm-openai@sha256:...`) once a version is validated.

Disk: weights ~22 GB in `hf-cache`; jobs are small (a few MB each) and expire after 72 h.

## Security checklist

- [ ] `ENGINE_TOKEN_SECRET` set (engine refuses unauthenticated requests).
- [ ] Only port 8090 published through the tunnel; 8080 not exposed.
- [ ] `CORS_ORIGINS` lists only your domains.
- [ ] `APP_PASSWORD` set on Vercel, or Cloudflare Access configured.
- [ ] `infra/.env` and `web/.env.local` never committed (`.gitignore` covers them).
- [ ] Windows firewall: if the office LAN is not trusted, block inbound 8080/8090 (the tunnel connects outbound
      and does not need them open).

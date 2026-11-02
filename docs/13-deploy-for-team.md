# Deploy for your team (checklist)

This is the recommended production layout. **Vercel hosts only the web UI.** The model and engine stay on the
GPU PC. **Render is not a substitute for that PC** unless you abandon local LLM and pay for GPU hosting elsewhere.

## Architecture (what goes where)

| Piece | Host | Public URL | Why |
|---|---|---|---|
| Web app (`web/`) | **Vercel** (or Render as static/Node) | `https://slides.admindagency.com` | No GPU, no client files stored |
| Engine (`engine/`) | **Office GPU PC** (Docker) | `https://slides-api.admindagency.com` via **Cloudflare tunnel** | Parses uploads, calls vLLM, renders pptx |
| vLLM | Same PC, **not public** | none (`localhost:8080` only) | 32 GB GPU, data never leaves |

Browsers upload files **directly to the engine URL** (with a short-lived token from Vercel). Vercel never sees
the file contents.

---

## Phase A - GPU workstation (once)

1. Install Docker Desktop with GPU support; confirm `docker compose` works from `infra/`.
2. Generate a secret (save it in a password manager):

   ```powershell
   cd engine; .venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

3. Create `infra/.env` from `infra/.env.example`:
   - `ENGINE_TOKEN_SECRET=<that secret>`
   - `CORS_ORIGINS=https://slides.YOURDOMAIN.com,http://localhost:3000` (use your real Vercel domain)
4. Start stack:

   ```powershell
   cd infra
   docker compose up -d --build
   curl http://localhost:8090/api/health
   ```

5. Keep the PC on (or wake on LAN), Docker set to start at login, `restart: unless-stopped` on containers.

---

## Phase B - Cloudflare tunnel (once)

Same pattern as `lt.admindagency.com`:

1. Zero Trust -> Networks -> Tunnels -> your existing tunnel -> **Public Hostname** -> Add.
2. Subdomain e.g. `slides-api`, domain `admindagency.com`, service **HTTP** `localhost:8090`.
3. Test: `curl https://slides-api.admindagency.com/api/health` (should return JSON with `"ok": true` when vLLM is up).

**Do not** tunnel port 8080 (vLLM has no auth).

Optional: put **Cloudflare Access** on `slides-api.*` so only `@admindagency.com` can hit the API even with a
token (defence in depth).

---

## Phase C - Vercel (recommended for the web app)

1. Push this repo to GitHub/GitLab (or connect Vercel to your git host).
2. Vercel -> **Add Project** -> import repo.
3. **Root Directory**: `web` (important).
4. Framework: Next.js (auto-detected).
5. **Environment variables** (Production + Preview if you want previews to work against a dev engine):

   | Name | Value |
   |---|---|
   | `ENGINE_URL` | `https://slides-api.admindagency.com` |
   | `ENGINE_TOKEN_SECRET` | same as `infra/.env` |
   | `APP_PASSWORD` | team shared password (or leave empty only for experiments) |

6. Deploy. Add custom domain e.g. `slides.admindagency.com` in Vercel -> Domains.
7. Update `CORS_ORIGINS` on the engine to include that exact `https://` origin, then:

   ```powershell
   cd infra; docker compose up -d engine
   ```

8. Open `https://slides.admindagency.com/login`, sign in, generate a test deck.

### If previews or upload fail in the browser

- Open DevTools -> Network: calls to `slides-api...` must not be blocked by CORS (wrong origin in `CORS_ORIGINS`).
- Engine must require auth: unauthenticated `POST /api/jobs` should return **401**.
- Tunnel must reach the PC: if the GPU machine is off, health shows offline.

---

## Phase D - Stronger team access (recommended)

Pick one or combine:

1. **APP_PASSWORD** on Vercel (simple; share password in 1Password).
2. **Cloudflare Access** on `slides.admindagency.com` (and optionally `slides-api`): Microsoft Entra / Google,
   policy `@admindagency.com` only.
3. **ENGINE_API_KEYS** for automation scripts only; browsers still use tokens from `/api/token`.

---

## Using Render instead of Vercel

| Use Render for | Works? |
|---|---|
| **Web app only** (`web/`, build `npm run build`, start `npm start`) | Yes - same env vars as Vercel |
| **Engine + vLLM** | **No** for this project - you need the local RTX 5090 and ~28 GB VRAM for the current model |
| **Engine without GPU** pointing at a remote LLM | Possible but **not** your privacy requirement |

If you still put the web app on Render:

1. New **Web Service**, connect repo, root `web`, build `npm install && npm run build`, start `npm start`.
2. Set `ENGINE_URL`, `ENGINE_TOKEN_SECRET`, `APP_PASSWORD` like Vercel.
3. Add custom domain; add that origin to `CORS_ORIGINS` on the engine.

You still need Phase A + B on the office GPU machine.

---

## Rollout to the team

1. Send link: `https://slides.admindagency.com`
2. Send password (or tell them to use company SSO via Cloudflare Access).
3. One-pager: upload PDF/Excel/pptx + write the brief + slide count; wait ~10 s; download pptx; yellow warnings =
   verify numbers before sending to clients.
4. Name one **on-call** for "Engine offline" (GPU PC asleep, Docker stopped, tunnel down).

---

## Quick verification script (from any PC)

```powershell
curl https://slides-api.admindagency.com/api/health
curl -I https://slides.admindagency.com
```

See also [09-deployment.md](09-deployment.md) for operations, logs, and security checklist.

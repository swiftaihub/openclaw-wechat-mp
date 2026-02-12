# OpenClaw WeChat MP Gateway

FastAPI gateway that connects a WeChat Official Account (gong zhong hao) with LLM running on Ollama.

This repo provides:
- WeChat callback verification (`GET /wechat`)
- WeChat message handling (`POST /wechat`)
- LLM reply generation via Ollama
- Docker Compose deployment for both `wechat-mp` app and `cloudflared` service

## Architecture

- `wechat-mp` container:
  - FastAPI app
  - receives WeChat callbacks
  - validates WeChat signature
  - calls Ollama and returns passive sync reply
- `cloudflared` container:
  - publish tunnel and running in a container for exposing local webhook to WeChat

Request flow:
1. WeChat sends message callback to `/wechat`.
2. App validates signature using `WECHAT_TOKEN`.
3. App sends prompt to Ollama (`OLLAMA_BASE_URL` + `OLLAMA_MODEL`).
4. App returns XML reply to WeChat.

## Project Structure

```text
.
|-- app/
|   |-- main.py
|   |-- wechat.py
|   |-- wechat_token.py
|   |-- llm_core.py
|   |-- ollama_client.py
|   |-- prompt_runtime.py
|   `-- guardrail.py
|-- config/
|   `-- prompt.example.yaml
|-- cloudflared/
|   |-- config.yml
|   |-- credentials.json
|-- docs/
|   `-- prompt-guardrail-security.md
|-- tests/
|   |-- test_prompt_runtime.py
|   `-- test_guardrail.py
|-- docker-compose.yml
|-- Dockerfile
`-- requirements.txt
```

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- A WeChat Official Account with server callback configuration access
- Cloudflare account
- `cloudflared` CLI (for exposing local webhook to WeChat)

## Environment Variables

Create `.env` in repo root:

```dotenv
WECHAT_TOKEN=replace_with_your_token
WECHAT_APPID=replace_with_your_appid
WECHAT_SECRET=replace_with_your_secret
EncodingAESKey=replace_with_your_encoding_aes_key

OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
OLLAMA_NUM_PREDICT=180
OLLAMA_TEMPERATURE=0.2
OLLAMA_TOP_P=0.9
OLLAMA_KEEP_ALIVE=30m
OLLAMA_WARMUP_ON_STARTUP=1
OLLAMA_WARMUP_TIMEOUT_SECONDS=15

PROMPT_PROFILE=wechat
PROMPT_CONFIG_PATH=config/prompt.private.yaml
PROMPT_EXAMPLE_PATH=config/prompt.example.yaml

PORT=8787
OPENCLAW_REPLY_TIMEOUT_SECONDS=5
WECHAT_SYNC_TIMEOUT_TEXT=回复生成超时，请稍后再试。
WECHAT_SYNC_ERROR_TEXT=服务暂时繁忙，请稍后再试。
```

Notes:
- `WECHAT_TOKEN` must exactly match the token configured in WeChat platform.
- This code currently handles plain text callback mode (not encrypted callback decryption).
- If your current model name in `.env` does not exist in Ollama, pull an available model and update `OLLAMA_MODEL`.

## Prompt and Guardrail Separation

This project supports runtime-loaded prompt and guardrail policies:

- Private config file: `config/prompt.private.yaml` (git ignored)
- Public template file: `config/prompt.example.yaml` (safe to commit)
- Runtime config loader: `app/prompt_runtime.py`
- Guardrail pipeline: `app/guardrail.py`

Setup:

```bash
cp config/prompt.example.yaml config/prompt.private.yaml
```

Fill only your local `config/prompt.private.yaml` with private prompt content and policy patterns.
Do not commit this file.

See `docs/prompt-guardrail-security.md` for architecture, lifecycle, and CI/CD protections.

## Run Tests

Run all tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run Guardrail tests only:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_guardrail -v
```

Run prompt runtime tests only:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_prompt_runtime -v
```

Run local private prompt config test (`config/prompt.private.yaml`):

```powershell
$env:RUN_PRIVATE_PROMPT_TEST="1"
.\.venv\Scripts\python.exe -m unittest tests.test_prompt_runtime.PromptRuntimeTests.test_load_runtime_from_local_private_config -v
Remove-Item Env:RUN_PRIVATE_PROMPT_TEST
```

## Deploy with Docker

`docker-compose.yml` mounts `./config` into `/srv/config` as read-only, so local updates to
`prompt.private.yaml` can be applied without rebuilding the image.

### 1. Build and start services

```bash
docker compose up -d --build
```

### 2. Check containers

```bash
docker compose ps
docker compose logs -f openclaw
```

### 3. Verify app health

```bash
curl http://localhost:8787/health
```

Expected:

```json
{"ok": true}
```

## Ollama in Docker: Pull and Manage Models

After containers are up, install at least one model in the `ollama` container.

### Pull a model

```bash
docker compose exec ollama ollama pull qwen2.5:32b-instruct-q4_K_M
```

### List models

```bash
docker compose exec ollama ollama list
```

### Test Ollama API from host

```bash
curl http://localhost:11434/api/tags
```

If you change `OLLAMA_MODEL` in `.env`, recreate app container:

```bash
docker compose up -d --force-recreate openclaw
```

## Where to Use Cloudflare Tunnel (Important)

Use Cloudflare Tunnel **after** local containers are healthy and before configuring WeChat callback URL.

Recommended order:
1. `docker compose up -d --build`
2. Confirm `http://localhost:8787/health` works
3. Start `cloudflared` for `http://localhost:8787`
4. Copy Cloudflare Tunnel HTTPS URL into WeChat server config

### Install cloudflared on Windows Command Prompt

```bat
winget install --id Cloudflare.cloudflared -e
```

If `winget` is unavailable, download the Windows binary from Cloudflare and add it to your `PATH`.

### Start Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:8787
```

You will get an HTTPS forwarding URL like:

```text
https://random-subdomain.trycloudflare.com
```

WeChat callback URL should be:

```text
https://random-subdomain.trycloudflare.com/wechat
```

Keep the tunnel running during WeChat callback verification and testing.

## Tunnel for production with owned domain
- register your cloudflared account at https://dash.cloudflare.com
- Add a exisitng site -> rename Nameserver
```bash
cloudflared login
cloudflared tunnel create your-tunnel-name
cloudflared tunnel route dns your-tunnel-name wx.yourdomain.com
cloudflared tunnel run your-tunnel-name
```
- To update cloudflared:
```bash
winget upgrade Cloudflare.cloudflared
```

## Finding your own cloudflared credentials.json:
- C:\Users\<your-username>\.cloudflared\<uuid>.json
- Add this file into /cloudflared/credentials.json
- change your own dns in config.yml

## Configure WeChat Official Account

In WeChat platform server configuration:

- URL: `https://<your-cloudflare-domain>/wechat`
- Token: value of `WECHAT_TOKEN`
- EncodingAESKey: value of `EncodingAESKey`
- Message encryption mode: use plain text mode for this codebase

Save/submit to trigger WeChat verification request.

## Optional: Create WeChat Menu

After app is running and `WECHAT_APPID` / `WECHAT_SECRET` are correct:

```bash
curl -X POST http://localhost:8787/wechat/menu
```

## API Endpoints

- `GET /health`: health check
- `GET /wechat`: WeChat URL verification
- `POST /wechat`: WeChat message callback
- `POST /wechat/menu`: create custom menu via WeChat API

## Troubleshooting

### `403 Invalid signature`

- `WECHAT_TOKEN` in `.env` does not match WeChat platform token
- callback URL is not exactly `/wechat`
- tunnel URL changed, but WeChat config still points to old URL

### `500 WECHAT_TOKEN not set`

- missing or empty `WECHAT_TOKEN` in `.env`
- restart container after env changes:

```bash
docker compose up -d --force-recreate openclaw
```

### Reply fallback / timeout message from bot

- Ollama container is not ready
- model not pulled
- `OLLAMA_MODEL` name does not exist
- reply exceeded WeChat passive window, reduce latency with:
  - smaller `OLLAMA_MODEL`
  - lower `OLLAMA_NUM_PREDICT` (e.g. `120-180`)
  - keep model loaded with `OLLAMA_KEEP_ALIVE=30m`
  - ensure warmup enabled with `OLLAMA_WARMUP_ON_STARTUP=1`
  - for large models, increase warmup timeout with `OLLAMA_WARMUP_TIMEOUT_SECONDS` (e.g. `15`)
  - tune `OPENCLAW_REPLY_TIMEOUT_SECONDS`

### Docker build/start issues

- ensure Docker daemon is running
- check compose config:

```bash
docker compose config
```

## Security Notes

- Do not commit `.env` to git.
- Do not commit `config/prompt.private.yaml` to git.
- `.dockerignore` excludes private prompt files from Docker build context.
- Rotate WeChat secrets if they are ever exposed.
- In production, restrict exposed ports and add authentication for admin endpoints like `/wechat/menu`.

## Start the server:
Powershell run startup.ps1

## Stop the server:
Powershell run shutdown.ps1

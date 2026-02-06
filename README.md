# OpenClaw WeChat MP Gateway

FastAPI gateway that connects a WeChat Official Account (gong zhong hao) with OpenClaw running on Ollama.

This repo provides:
- WeChat callback verification (`GET /wechat`)
- WeChat message handling (`POST /wechat`)
- LLM reply generation via Ollama
- Docker Compose deployment for both `openclaw` app and `ollama` service

## Architecture

- `openclaw` container:
  - FastAPI app
  - receives WeChat callbacks
  - validates WeChat signature
  - calls Ollama chat API
- `ollama` container:
  - local LLM runtime
  - model storage in Docker volume `ollama_data`

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
|   |-- openclaw_core.py
|   `-- ollama_client.py
|-- docker-compose.yml
|-- Dockerfile
`-- requirements.txt
```

## Prerequisites

- Docker Desktop (or Docker Engine + Compose plugin)
- A WeChat Official Account with server callback configuration access
- `ngrok` account and CLI (for exposing local webhook to WeChat)

## Environment Variables

Create `.env` in repo root:

```dotenv
WECHAT_TOKEN=replace_with_your_token
WECHAT_APPID=replace_with_your_appid
WECHAT_SECRET=replace_with_your_secret
EncodingAESKey=replace_with_your_encoding_aes_key

OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:7b-instruct

PORT=8787
OPENCLAW_REPLY_TIMEOUT_SECONDS=4.5
```

Notes:
- `WECHAT_TOKEN` must exactly match the token configured in WeChat platform.
- This code currently handles plain text callback mode (not encrypted callback decryption).
- If your current model name in `.env` does not exist in Ollama, pull an available model and update `OLLAMA_MODEL`.

## Deploy with Docker

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
docker compose exec ollama ollama pull qwen2.5:7b-instruct
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

## Where to Use ngrok (Important)

Use `ngrok` **after** local containers are healthy and before configuring WeChat callback URL.

Recommended order:
1. `docker compose up -d --build`
2. Confirm `http://localhost:8787/health` works
3. Start `ngrok` for port `8787`
4. Copy ngrok HTTPS URL into WeChat server config

### Start ngrok

```bash
ngrok http 8787
```

You will get an HTTPS forwarding URL like:

```text
https://abcd-1234.ngrok-free.app
```

WeChat callback URL should be:

```text
https://abcd-1234.ngrok-free.app/wechat
```

Keep ngrok running during WeChat callback verification and testing.

## Configure WeChat Official Account

In WeChat platform server configuration:

- URL: `https://<your-ngrok-domain>/wechat`
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
- ngrok URL changed, but WeChat config still points to old URL

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
- choose a smaller model or increase timeout with `OPENCLAW_REPLY_TIMEOUT_SECONDS`

### Docker build/start issues

- ensure Docker daemon is running
- check compose config:

```bash
docker compose config
```

## Security Notes

- Do not commit `.env` to git.
- Rotate WeChat secrets if they are ever exposed.
- In production, restrict exposed ports and add authentication for admin endpoints like `/wechat/menu`.

## Stop Services

```bash
docker compose down
```

To also remove Ollama model volume:

```bash
docker compose down -v
```


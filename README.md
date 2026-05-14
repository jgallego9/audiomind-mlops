# AudioMind MLOps Platform

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-42%20passed-brightgreen.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)]()
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A portfolio-grade MLOps platform that accepts audio URLs, transcribes them with a mocked Whisper STT worker, indexes transcripts into a Qdrant vector store, and exposes a semantic search API — all wired with OpenTelemetry tracing, rate-limiting, and JWT auth.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client / Browser                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │  REST  (port 8000)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       api-gateway (FastAPI)                     │
│                                                                 │
│  POST /auth/token    →  JWT bearer token                        │
│  POST /transcribe    →  enqueue job, return job_id              │
│  GET  /jobs/{id}     →  poll job status + result                │
│  POST /search        →  semantic vector search (RAG)            │
│  GET  /health        →  liveness probe                          │
│  GET  /ready         →  readiness probe (Redis + Qdrant)        │
└────────────────┬──────────────────────┬────────────────────────┘
                 │ Redis Streams         │ Qdrant HTTP
                 ▼                       ▼
┌───────────────────────┐   ┌──────────────────────────────────┐
│   Redis 7 (streams +  │   │   Qdrant (vector store)          │
│   rate-limit store)   │   │   • BAAI/bge-small-en-v1.5       │
└───────────┬───────────┘   │   • FastEmbed (local inference)  │
            │ xreadgroup     └──────────────────────────────────┘
            ▼                                ▲
┌─────────────────────────────────────────────────────────────────┐
│                    worker (async consumer)                       │
│                                                                 │
│  1. xreadgroup — pop job from stream                            │
│  2. mock_transcribe — simulated Whisper ASR                     │
│  3. index_transcription — embed + upsert to Qdrant              │
│  4. hset — write result back to Redis                           │
└─────────────────────────────────────────────────────────────────┘

Observability:  Jaeger (OTel OTLP traces)
Experiment tracking (--profile mlops):  MLflow + PostgreSQL
Model serving (--profile models):  Whisper ASR + Ollama LLM
```

---

## Features

| Feature | Status |
|---|---|
| FastAPI service with lifespan, `Annotated` deps | ✅ |
| JWT authentication (PyJWT 2.12) | ✅ |
| SlowAPI rate-limiting (per-route) | ✅ |
| Redis Streams async job pipeline | ✅ |
| Qdrant + FastEmbed RAG search | ✅ |
| OpenTelemetry traces (OTLP → Jaeger) | ✅ |
| pytest suite — 42 tests, 90 % coverage | ✅ |
| Docker Compose multi-profile stack | ✅ |
| End-to-end demo script | ✅ |

---

## Quickstart

### Prerequisites

- Docker ≥ 24 with Compose V2
- `jq` (demo script only)

### 1 — Clone and configure

```bash
git clone <repo-url>
cd audiomind-mlops
cp .env.example .env        # edit JWT_SECRET_KEY
```

### 2 — Start the core stack

```bash
docker compose up -d
```

Services started: `api-gateway`, `worker`, `redis`, `qdrant`, `jaeger`.

### 3 — Verify readiness

```bash
curl -s http://localhost:8000/ready | jq .
```

```json
{
  "status": "ready",
  "checks": {
    "redis":  { "status": "ok", "latency_ms": 0.4 },
    "qdrant": { "status": "ok", "latency_ms": 2.1 }
  }
}
```

### 4 — Run the demo

```bash
bash scripts/demo.sh
```

The script logs in, submits a transcription job, polls until completion, then runs a semantic search against the indexed result.

---

## API Reference

All authenticated endpoints require `Authorization: Bearer <token>`.

### Authentication

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/token` | Login — returns JWT bearer token |

**Request body:**
```json
{ "username": "admin", "password": "demo-password" }
```

**Response:**
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

### Jobs

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/transcribe` | ✅ | Submit an audio URL for transcription |
| `GET` | `/jobs/{job_id}` | ✅ | Poll job status |

**POST /transcribe body:**
```json
{ "audio_url": "https://example.com/audio.mp3", "language": "en" }
```

**GET /jobs/{job_id} response:**
```json
{
  "job_id": "abc-123",
  "status": "completed",
  "audio_url": "https://...",
  "language": "en",
  "created_at": "2026-01-01T00:00:00",
  "completed_at": "2026-01-01T00:00:05",
  "result": {
    "transcript": "Hello world",
    "language": "en",
    "duration": 3.5
  }
}
```

### Search

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/search` | ✅ | Semantic search over the user's transcripts |

**Request body:**
```json
{ "query": "music and rhythm", "limit": 5 }
```

`limit` must be between 1 and 20 (default: 5).

**Response:**
```json
{
  "results": [
    {
      "job_id": "abc-123",
      "score": 0.91,
      "transcript": "Hello world",
      "language": "en",
      "audio_url": "https://...",
      "created_at": "2026-01-01T00:00:00"
    }
  ],
  "total": 1
}
```

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness — always 200 while process is running |
| `GET` | `/ready` | Readiness — checks Redis + Qdrant connectivity |

---

## Configuration

All settings are read from environment variables (or `.env` file).

### api-gateway

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET_KEY` | **required** | HMAC signing secret (≥ 32 chars) |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token TTL |
| `RATE_LIMIT_DEFAULT` | `100/minute` | Default rate limit |
| `RATE_LIMIT_AUTH` | `10/minute` | Login endpoint limit |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant connection URL |
| `QDRANT_COLLECTION` | `transcriptions` | Vector collection name |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | FastEmbed model |
| `OTEL_ENABLED` | `false` | Enable OTel tracing |
| `OTEL_OTLP_ENDPOINT` | `http://jaeger:4318` | OTLP collector endpoint |

### worker

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant connection URL |
| `QDRANT_COLLECTION` | `transcriptions` | Vector collection name |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | FastEmbed model |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Development

### Setup

```bash
# Install uv (https://docs.astral.sh/uv/)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all deps (workspace + dev)
uv sync --all-packages --dev
```

### Lint + type-check

```bash
uv run ruff check services/
uv run ruff format --check services/

# Per-service mypy (strict)
cd services/api-gateway && uv run mypy app/
cd services/worker      && uv run mypy app/
```

### Tests

```bash
# All services — combined coverage report
uv run pytest services/

# Single service
uv run pytest services/api-gateway/tests/
uv run pytest services/worker/tests/
```

Coverage target: **80 %** (currently 90 %).

### Docker Compose profiles

```bash
# Core only
docker compose up -d

# + MLflow experiment tracking + PostgreSQL
docker compose --profile mlops up -d

# + Whisper ASR + Ollama LLM
docker compose --profile mlops --profile models up -d
```

### Observability

Jaeger UI: [http://localhost:16686](http://localhost:16686) — view distributed traces.  
MLflow UI (mlops profile): [http://localhost:5001](http://localhost:5001)

---

## Project Structure

```
audiomind-mlops/
├── docker-compose.yml          # Multi-profile Compose stack
├── pyproject.toml              # Workspace root — dev tooling config
├── scripts/
│   └── demo.sh                 # End-to-end demo script
├── services/
│   ├── api-gateway/            # FastAPI REST service
│   │   ├── app/
│   │   │   ├── config.py
│   │   │   ├── main.py
│   │   │   ├── dependencies/   # auth, redis, qdrant
│   │   │   ├── middleware/     # rate-limit, telemetry
│   │   │   ├── models/         # Pydantic request/response models
│   │   │   └── routes/         # health, auth, jobs, search
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   └── worker/                 # Async Redis Streams consumer
│       ├── app/
│       │   ├── config.py
│       │   ├── main.py
│       │   ├── consumer.py     # Stream consumer loop
│       │   ├── indexer.py      # Qdrant indexing (best-effort)
│       │   └── processors/
│       │       └── transcribe.py  # Mock Whisper STT
│       ├── tests/
│       ├── Dockerfile
│       └── pyproject.toml
└── BACKLOG.md
```

---

## License

MIT © 2026


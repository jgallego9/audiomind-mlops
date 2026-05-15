# AudioMind MLOps Platform

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Inferflow-based MLOps platform for step-driven AI pipelines.

The platform is split into 3 layers:
1. Step layer: KServe V2 model steps (single responsibility, reusable).
2. Pipeline layer: YAML pipeline definitions wiring steps by task.
3. Runtime layer: API gateway + worker + Redis streams + Qdrant + Helm deployment.

## Architecture (3 Layers)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                               Runtime Layer                                │
│  api-gateway (FastAPI) + worker + Redis Streams + Qdrant + Helm/K8s       │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ executes pipeline definitions
┌───────────────────────────────▼─────────────────────────────────────────────┐
│                               Pipeline Layer                               │
│  pipelines/<name>/pipeline.yaml (audio-rag, image-search, ...)             │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ routes payloads by task contracts
┌───────────────────────────────▼─────────────────────────────────────────────┐
│                                 Step Layer                                 │
│  steps/<task>-<impl>/ exposing KServe V2 /v2/models/* endpoints            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Install Inferflow CLI

```bash
uv tool install ./tools/inferflow-cli
```

To upgrade after pulling changes:

```bash
uv tool install --upgrade ./tools/inferflow-cli
```

## Setup in 2 Steps

### 1) Clone

```bash
git clone <repo-url>
cd audiomind-mlops
```

### 2) Initialize

```bash
inferflow init
```

`inferflow init` creates `inferflow.yaml` and `.env` (with a generated `JWT_SECRET_KEY`) if missing, or validates prerequisites if they already exist.

## End-to-End Workflow (5 Stages)

### 1) Setup

```bash
inferflow init
```

### 2) Run demo pipeline

```bash
inferflow pipeline list
inferflow pipeline validate audio-rag
```

### 3) Create a custom pipeline

```bash
inferflow pipeline validate image-search
```

### 4) Add a new step

```bash
inferflow step list
inferflow task list
```

### 5) Deploy

```bash
# Helm chart supports N pipelines from values.yaml with no template edits
helm lint infra/helm/audiomind -f infra/helm/audiomind/values-dev.yaml
```

## CLI Commands Available Today

```text
inferflow init [--non-interactive]

inferflow task list

inferflow step list

inferflow pipeline list
inferflow pipeline validate <pipeline>
```

## Built-in Tasks and Schemas

All task contracts live in `tasks/<task>/schema.json`.

| Task | Purpose | Main Input | Main Output |
|---|---|---|---|
| `audio-transcribe` | Speech-to-text | `audio_url` | `text` |
| `text-embed` | Text embeddings | `text` | `embedding` |
| `vector-index` | Store vectors in Qdrant | `vector` | `status` |
| `vector-search` | Retrieve nearest vectors | `vector` | `results` |
| `vision-embedding` | Image embeddings for search | `image_url` | `vector` |

## Available Steps

| Step | Task | Impl | Version | Key Env Vars |
|---|---|---|---|---|
| `audio-transcribe-whisper` | `audio-transcribe` | `whisper` | `1` | `WHISPER_STEP_MODEL_SIZE`, `WHISPER_STEP_DEVICE` |
| `text-embed-fastembed` | `text-embed` | `fastembed` | `1` | `EMBED_STEP_EMBED_MODEL`, `EMBED_STEP_MODEL_CACHE_DIR` |
| `vector-index-qdrant` | `vector-index` | `qdrant` | `1` | `INDEX_STEP_QDRANT_URL`, `INDEX_STEP_QDRANT_COLLECTION` |
| `vector-search-qdrant` | `vector-search` | `qdrant` | `1` | `SEARCH_STEP_QDRANT_URL`, `SEARCH_STEP_QDRANT_COLLECTION` |
| `vision-clip` | `vision-embedding` | `clip` | `1` | `VISION_STEP_VISION_MODEL`, `VISION_STEP_MODEL_CACHE_DIR` |

## Generic Helm Pipelines

`infra/helm/audiomind/templates/steps/` renders, per step and per enabled pipeline:
- Deployment
- Service
- Optional HPA
- PodDisruptionBudget
- Shared `models-cache` PVC mount when `modelVolume` is set

Add a new pipeline by editing only values and pipeline YAML:
1. Add `pipelines/<name>/pipeline.yaml`.
2. Add `.Values.pipelines.<name>` in `infra/helm/audiomind/values.yaml`.

No template edits are required.

## Development

```bash
uv sync --all-packages --dev
make ci
```

## Current Status

Completed in Phase 7:
- F7-4: Generic Helm chart per pipeline.
- F7-5: Second pipeline demo (`image-search`) with new `vision-clip` step.
- F7-6: Per-step CI workflow with dynamic matrix and `steps/<name>/VERSION` tags.
- F7-7: Initial `inferflow` CLI package at `tools/inferflow-cli`.

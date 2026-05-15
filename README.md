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
- Optional for Kubernetes work: `kind`, `kubectl`, and Helm 3

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

### Kubernetes + Helm

#### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Docker | ≥ 24 | [docs.docker.com](https://docs.docker.com/get-docker/) |
| kind | ≥ 0.23 | `brew install kind` |
| kubectl | ≥ 1.30 | `brew install kubectl` |
| Helm | ≥ 4.0 | `brew install helm` |

#### Local cluster

```bash
# Create a multi-node kind cluster (1 control-plane + 2 workers)
make kind-up

# Inspect nodes and namespaces
make kind-status

# Delete the cluster
make kind-down
```

Host ports `8080` (HTTP) and `8443` (HTTPS) are mapped to the control-plane node
for use with ingress-nginx.

#### Full local infra bootstrap

Run these once after `make kind-up`:

```bash
# Apply ResourceQuota + LimitRange to the audiomind namespace
make infra-namespaces

# Install ingress-nginx + cert-manager (self-signed TLS)
make helm-ingress-install

# Install kube-prometheus-stack + Loki + Jaeger
make helm-monitoring-install

# Install KEDA (event-driven autoscaler)
make helm-keda-install

# Install External Secrets Operator
make helm-eso-install

# Install the main audiomind chart (api-gateway + worker + Redis + Qdrant)
make helm-install

# Or bootstrap everything in one command:
make infra-up
```

#### Chart overview

| Chart | Path | What it installs |
|---|---|---|
| `audiomind` | `infra/helm/audiomind/` | api-gateway, worker, Redis, Qdrant, vLLM (optional) |
| `audiomind-monitoring` | `infra/helm/monitoring/` | kube-prometheus-stack, Loki, Promtail, Jaeger |
| `gpu-operator` | `infra/helm/gpu-operator/` | NVIDIA driver, device plugin, DCGM exporter |
| `keda` | `infra/helm/keda/` | KEDA autoscaler |
| `audiomind-ingress` | `infra/helm/ingress/` | ingress-nginx, cert-manager |
| `external-secrets` | `infra/helm/external-secrets/` | External Secrets Operator |

Each chart has a `values.yaml` (base) and `values-dev.yaml` (kind overlay).
Override the target values file with `HELM_VALUES=...`:

```bash
# Example: install with production overlay
HELM_VALUES=infra/helm/audiomind/values-prod.yaml make helm-upgrade
```

#### GPU / vLLM

vLLM is disabled by default. Enable it on a GPU-capable cluster:

```bash
# 1. Install GPU Operator first
make helm-gpu-install

# 2. Enable vLLM in the audiomind chart
helm upgrade audiomind infra/helm/audiomind \
  --namespace audiomind \
  --reuse-values \
  --set vllm.enabled=true \
  --set vllm.model=mistralai/Mistral-7B-Instruct-v0.3
```

GPU nodes must be labelled `nvidia.com/gpu.present=true` (done automatically
by the GPU Operator + Node Feature Discovery).

### Observability

#### Tracing

Jaeger UI: [http://localhost:16686](http://localhost:16686) — view distributed traces sent via OTLP from the api-gateway.  
MLflow UI (mlops profile): [http://localhost:5001](http://localhost:5001)

#### Metrics (Phase 4 — Prometheus)

The platform ships full Prometheus observability:

| Component | Scrape method | Metrics exposed |
|---|---|---|
| `api-gateway` | ServiceMonitor (`port: http`, `/metrics`) | HTTP request count, duration, status codes (prometheus_fastapi_instrumentator) |
| `worker` | PodMonitor (`port: metrics`, port 9090) | `audiomind_worker_jobs_processed_total`, `audiomind_worker_jobs_failed_total`, `audiomind_worker_job_duration_seconds` |
| `vLLM` | ServiceMonitor (`port: http`, `/metrics`) | `vllm:e2e_request_latency_seconds`, `vllm:num_requests_waiting`, `vllm:gpu_cache_usage_perc`, etc. |
| DCGM Exporter | ServiceMonitor (`port: metrics`) | `DCGM_FI_DEV_GPU_UTIL`, `DCGM_FI_DEV_FB_USED`, `DCGM_FI_DEV_GPU_TEMP`, `DCGM_FI_DEV_POWER_USAGE` |

All monitoring manifests are in `infra/k8s/monitoring/`:

| File | Kind | Purpose |
|---|---|---|
| `servicemonitor-audiomind.yaml` | ServiceMonitor | Scrape api-gateway |
| `podmonitor-audiomind-worker.yaml` | PodMonitor | Scrape worker (no Service needed) |
| `servicemonitor-vllm.yaml` | ServiceMonitor | Scrape vLLM |
| `servicemonitor-dcgm.yaml` | ServiceMonitor | Scrape DCGM Exporter |
| `prometheusrule-audiomind.yaml` | PrometheusRule | SLO alerts (latency, error rate, worker backlog) |
| `prometheusrule-vllm.yaml` | PrometheusRule | vLLM SLO alerts (latency, queue, KV-cache) |
| `prometheusrule-gpu.yaml` | PrometheusRule | GPU alerts (util, VRAM, temperature, power) |
| `grafana-dashboard-llm-inference.yaml` | ConfigMap | Grafana: vLLM latency, tokens, KV-cache |
| `grafana-dashboard-gpu-utilization.yaml` | ConfigMap | Grafana: GPU util, VRAM, temp, power |
| `grafana-dashboard-system-overview.yaml` | ConfigMap | Grafana: pod health, CPU/mem, error rates |

Grafana is available at [http://localhost:3000](http://localhost:3000) after `make helm-monitoring-install`.

---

## MLOps Workflow (Phase 5)

### Components

| Component | Purpose | Location |
|---|---|---|
| MLflow tracking server | Experiment tracking, model registry, artifact store | `infra/helm/mlflow/` |
| Argo Rollouts canary | Progressive model delivery (10 % → 50 % → 100 %) | `infra/k8s/argo-rollouts/` |
| `AnalysisTemplate` | Prometheus-backed automated quality gate | `infra/k8s/argo-rollouts/analysis-template-vllm.yaml` |
| `scripts/promote-model.sh` | One-command model promotion + canary trigger | `scripts/promote-model.sh` |
| Drift detector CronJob | Evidently PSI drift detection every 6 h | `services/drift-detector/` + `infra/k8s/monitoring/cronjob-drift-detector.yaml` |
| MLflow inference logger | Per-job metrics (latency, tokens/s, errors) from worker | `services/worker/app/mlflow_logger.py` |

### Canary deploy — 10 % → 50 % → 100 %

```
scripts/promote-model.sh
        │  ① MLflow: model-version → Production
        │  ② kubectl argo rollouts set image
        ▼
  setWeight: 10  →  pause 5 min
  setWeight: 50  →  pause 10 min  ◄── AnalysisRun starts here
  setWeight: 100 (full promotion)
        │
  Every 5 min (background analysis):
    vllm:request_success_rate ≥ 99 %  ✓
    p95 latency < 2 s                 ✓
    failureLimit: 3 → auto-rollback   ✗
```

### Model deployment steps

```bash
# 1 — Register model in MLflow (after training)
python training/register_model.py --name audiomind-whisper --version 7

# 2 — Build and push Docker image (done by CI, or manually)
docker build -t ghcr.io/jgallego9/audiomind-mlops/worker:v2.0.0 services/worker/
docker push ghcr.io/jgallego9/audiomind-mlops/worker:v2.0.0

# 3 — Promote model + start canary rollout
export MLFLOW_TRACKING_URI=http://mlflow.mlflow.svc.cluster.local:80
./scripts/promote-model.sh \
  --model-name audiomind-whisper \
  --model-version 7 \
  --image ghcr.io/jgallego9/audiomind-mlops/worker:v2.0.0

# 4 — Watch canary progress
kubectl argo rollouts get rollout audiomind-vllm -n audiomind --watch

# 5 — Abort if needed (auto-rollback to stable)
kubectl argo rollouts abort audiomind-vllm -n audiomind
```

Full runbook: [`docs/model-deploy-workflow.md`](docs/model-deploy-workflow.md)

### MLflow inference evaluation metrics

The worker logs a MLflow run for every completed inference job:

| Metric | Description |
|---|---|
| `duration_seconds` | Wall-clock time for the job |
| `tokens_per_second` | Throughput (when token count is available) |
| `success` | `1.0` = completed, `0.0` = failed |
| Tags | `model.name`, `model.version`, `job.id`, `job.status` |

### Drift detection metrics (Prometheus)

| Metric | Description |
|---|---|
| `audiomind_embedding_drift_share` | Fraction of drifted embedding dimensions (Evidently PSI) |
| `audiomind_embedding_drift_detected` | `1` if dataset-level drift threshold crossed |

Alert `EmbeddingDriftDetected` fires when `drift_share > 0.5` for 15 min.

---

## CI/CD — GitHub Actions + ArgoCD GitOps

[![CI](https://github.com/jgallego9/audiomind-mlops/actions/workflows/ci.yml/badge.svg)](https://github.com/jgallego9/audiomind-mlops/actions/workflows/ci.yml)
[![GHCR api-gateway](https://ghcr.io/jgallego9/audiomind-mlops/api-gateway)](https://github.com/jgallego9/audiomind-mlops/pkgs/container/audiomind-mlops%2Fapi-gateway)

### Pipeline overview

```
 git push / PR
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│  Job 1 — lint-test  (every event)                               │
│  ruff · mypy · pytest --cov 80% · helm lint · yamllint          │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ success (push only)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  Job 2 — build-push  (matrix: api-gateway, worker)             │
│  docker buildx · push to GHCR · trivy scan (CRITICAL exit-1)   │
│  upload SARIF → GitHub Security                                 │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ success (main push only)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  Job 3 — bump-tag                                               │
│  yq update values.yaml image tags · git commit [skip ci]       │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  ArgoCD ApplicationSet  (polls repo every 3 min)               │
│  audiomind-auto-sync → dev   (automated prune + selfHeal)       │
│  audiomind-manual-sync → staging / prod (manual approval)       │
└─────────────────────────────────────────────────────────────────┘
```

Images are published to GHCR with these tags:

| Tag | When |
|---|---|
| `sha-<short_sha>` | Every push |
| `<branch>` | Every push |
| `latest` | Push to `main` |

### ArgoCD bootstrap (local kind cluster)

```bash
# 1. Start the cluster and install core infra
make kind-up
make infra-up           # includes helm-argocd-install

# 2. Apply App-of-apps pattern (idempotent)
make argocd-bootstrap

# 3. Open the UI
make argocd-port-forward        # → http://localhost:8080
# Admin password:
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d && echo
```

ArgoCD version: **3.4.2** (Helm chart `argo/argo-cd` **9.5.14**).

### Adding a new environment

The ApplicationSet uses the [List generator](https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-List/).
To add a new environment:

1. Add an entry to the appropriate ApplicationSet in [infra/k8s/argocd/applicationset.yaml](infra/k8s/argocd/applicationset.yaml).
2. Create the overlay file `infra/helm/audiomind/values-<env>.yaml`.
3. Commit and push — ArgoCD syncs within 3 minutes.

No changes to the ApplicationSet controller or the CI pipeline are required.

---

## Infrastructure as Code (Terraform)

The `infra/terraform/` directory contains a cloud-agnostic Terraform layout with a shared interface module and three concrete environments.

### Environments

| Environment | Provider | Cluster | Extras |
|-------------|----------|---------|--------|
| `envs/local` | [tehcyx/kind ~> 0.11](https://registry.terraform.io/providers/tehcyx/kind/latest) | kind (1.32.0) | MetalLB LoadBalancer |
| `envs/aws` | [terraform-aws-modules/eks ~> 21.0](https://registry.terraform.io/modules/terraform-aws-modules/eks/aws/latest) | EKS 1.33 + VPC | ECR with lifecycle policies, IRSA |
| `envs/gcp` | [terraform-google-modules/kubernetes-engine ~> 44.1](https://registry.terraform.io/modules/terraform-google-modules/kubernetes-engine/google/latest) | GKE (REGULAR channel) | Workload Identity, Artifact Registry |

### Directory layout

```
infra/terraform/
├── modules/
│   └── k8s-cluster/           # Cloud-agnostic interface (variables + validation + outputs)
└── envs/
    ├── local/                 # kind + MetalLB
    ├── aws/                   # EKS + VPC + ECR
    └── gcp/                   # GKE + Artifact Registry
```

### Multi-cloud quickstart

```bash
# 1. Choose your environment (local | aws | gcp)
ENV=local   # or aws / gcp

# 2. Copy and edit the example vars file
cp infra/terraform/envs/$ENV/terraform.tfvars.example \
   infra/terraform/envs/$ENV/terraform.tfvars
# Edit the file with your values

# 3. Init, plan, apply via Makefile
make terraform-init-$ENV
make terraform-plan-$ENV   # skip for local env
make terraform-apply-$ENV
```

> **GPU nodes** — both `envs/aws` and `envs/gcp` support GPU node groups.  
> Set `gpu_node_count >= 1` in your `terraform.tfvars` to enable them. GPU nodes are tainted `nvidia.com/gpu=true:NoSchedule`.
>
> **GCP deletion** — `deletion_protection` defaults to `true`.  
> Set `deletion_protection = false` in your tfvars before running `terraform destroy`.

---

## Project Structure

```
audiomind-mlops/
├── docker-compose.yml              # Multi-profile Compose stack
├── pyproject.toml                  # Workspace root — dev tooling config
├── Makefile                        # All dev + infra targets
├── infra/
│   ├── kind/
│   │   └── cluster.yaml            # Local multi-node Kubernetes cluster
│   ├── helm/
│   │   ├── audiomind/              # Main chart: api-gateway, worker, Redis, Qdrant, vLLM
│   │   │   ├── templates/
│   │   │   │   ├── api-gateway/    # Deployment, Service, HPA, PDB, Ingress
│   │   │   │   ├── worker/         # Deployment, PDB
│   │   │   │   ├── vllm/           # Deployment, Service, PVC (GPU-optional)
│   │   │   │   └── serviceaccount.yaml
│   │   │   ├── Chart.yaml
│   │   │   ├── values.yaml         # Base values
│   │   │   └── values-dev.yaml     # kind overlay
│   │   ├── monitoring/             # kube-prometheus-stack + Loki + Promtail + Jaeger
│   │   ├── mlflow/                 # (F5) MLflow tracking server wrapper chart
│   │   ├── gpu-operator/           # NVIDIA GPU Operator
│   │   ├── keda/                   # KEDA event-driven autoscaler
│   │   ├── ingress/                # ingress-nginx + cert-manager
│   │   └── external-secrets/       # External Secrets Operator
│   └── k8s/
│       ├── cert-manager/           # ClusterIssuer (self-signed dev, ACME prod)
│       ├── external-secrets/       # SecretStore + ExternalSecret manifests
│       ├── gpu/                    # time-slicing ConfigMap
│       ├── keda/                   # ScaledObjects (api-gateway, worker)
│       ├── namespaces/
│       │   └── audiomind/          # ResourceQuota + LimitRange
│       ├── argocd/                 # (F3) ApplicationSet, app-of-apps
│       ├── argo-rollouts/          # (F5) Rollout + AnalysisTemplate (canary vLLM)
│       └── monitoring/             # (F4) ServiceMonitors, PrometheusRules, Grafana dashboards
│                                   # (F5) CronJob drift-detector
├── scripts/
│   ├── demo.sh                     # End-to-end demo script
│   └── promote-model.sh            # (F5) MLflow promotion + canary trigger
├── docs/
│   └── model-deploy-workflow.md    # (F5) Step-by-step model deploy runbook
├── services/
│   ├── api-gateway/                # FastAPI REST service
│   │   ├── app/
│   │   │   ├── config.py
│   │   │   ├── main.py
│   │   │   ├── dependencies/       # auth, redis, qdrant
│   │   │   ├── middleware/         # rate-limit, telemetry
│   │   │   ├── models/             # Pydantic request/response models
│   │   │   └── routes/             # health, auth, jobs, search
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   └── worker/                     # Async Redis Streams consumer
│       ├── app/
│       │   ├── config.py
│       │   ├── main.py
│       │   ├── consumer.py         # Stream consumer loop + MLflow metrics logging
│       │   ├── mlflow_logger.py    # (F5) Per-job MLflow run logger
│       │   ├── indexer.py          # Qdrant indexing
│       │   └── processors/
│       │       └── transcribe.py   # Mock Whisper STT
│       ├── tests/
│       ├── Dockerfile
│       └── pyproject.toml
├── services/
│   └── drift-detector/             # (F5) Evidently drift detection job
│       ├── app/
│       │   ├── settings.py
│       │   └── main.py             # Qdrant sample → Evidently PSI → Pushgateway
│       ├── Dockerfile
│       └── pyproject.toml
└── BACKLOG.md
```

---

## License

MIT © 2026

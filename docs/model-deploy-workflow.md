# Model Deploy Workflow

Step-by-step guide for deploying a new model version to production using the
Inferflow MLOps platform.

---

## Overview

```
Train / fine-tune model
        │
        ▼
Register in MLflow Model Registry
        │
        ▼
Build & push Docker image (CI)
        │
        ▼
scripts/promote-model.sh  ──────────────────────┐
        │  1. Transitions model version          │
        │     to "Production" in MLflow           │
        │  2. Updates Rollout image via           │
        │     kubectl argo rollouts set image     │
        └────────────────────────────────────────┘
        │
        ▼
Argo Rollouts canary (pod-ratio)
  10 % traffic  →  wait 5 min
  50 % traffic  →  wait 10 min
  100 % traffic (full promotion)
        │
  AnalysisTemplate runs continuously
  (Prometheus metrics every 5 min):
    • request success rate ≥ 99 %
    • p95 latency < 2 s
        │
  PASS ──────────────► full rollout
  FAIL ──────────────► automatic rollback
        │
        ▼
Drift detection CronJob (every 6 h)
  Evidently DataDriftPreset (PSI)
  Pushes drift_share to Prometheus
  Grafana alert if drift > threshold
```

---

## Prerequisites

| Tool | Purpose |
|------|---------|
| `kubectl` | K8s cluster access |
| `kubectl argo rollouts` plugin | Canary management |
| `curl` + `jq` | MLflow REST API calls |
| Docker / buildx | Image build & push |

---

## Step 1 — Register the model in MLflow

After training, log and register the model:

```python
import mlflow

mlflow.set_tracking_uri("http://mlflow.mlflow.svc.cluster.local:80")
mlflow.set_experiment("inferflow-inference")

with mlflow.start_run():
    # log params, metrics ...
    mlflow.log_param("model_type", "whisper-large-v3")
    mlflow.log_metric("wer", 0.045)

    # register — creates a new version automatically
    mlflow.pytorch.log_model(
        model,
        artifact_path="model",
        registered_model_name="inferflow-whisper",
    )
```

Note the **version number** printed by MLflow (e.g., `Version 7`).

---

## Step 2 — Build and push the Docker image

The CI pipeline (`.github/workflows/ci.yml`, job `build-push`) triggers on every
commit to `main` and:

1. Builds the image with `docker buildx bake`.
2. Pushes to `ghcr.io/jgallego9/inferflow-mlops/worker:<sha>`.
3. Scans with Trivy (fails on CRITICAL CVEs).
4. Bumps the image tag in `infra/helm/inferflow/values.yaml` via `yq`.

For a manual build:

```bash
docker build \
  -t ghcr.io/jgallego9/inferflow-mlops/worker:v2.0.0 \
  services/worker/

docker push ghcr.io/jgallego9/inferflow-mlops/worker:v2.0.0
```

---

## Step 3 — Promote the model

```bash
export MLFLOW_TRACKING_URI=http://mlflow.mlflow.svc.cluster.local:80
export ROLLOUT_NAMESPACE=inferflow
export ROLLOUT_NAME=inferflow-vllm
export CONTAINER_NAME=vllm

./scripts/promote-model.sh \
  --model-name inferflow-whisper \
  --model-version 7 \
  --image ghcr.io/jgallego9/inferflow-mlops/worker:v2.0.0
```

The script:
1. Calls `POST /api/2.0/mlflow/model-versions/transition-stage` to move the
   version to **Production** (archives previous Production versions).
2. Runs `kubectl argo rollouts set image` to start the canary rollout.
3. Prints monitoring instructions.

---

## Step 4 — Monitor the canary

```bash
# Watch rollout progress in real time
kubectl argo rollouts get rollout inferflow-vllm \
  -n inferflow --watch

# Check analysis run results
kubectl get analysisrun -n inferflow

# Inspect a specific run
kubectl describe analysisrun <name> -n inferflow
```

Grafana dashboards:
- **LLM Inference** — p95 latency, throughput, KV-cache utilisation
- **System Overview** — pod health, error rate, canary vs stable traffic

---

## Step 5 — Manual promotion or rollback

If the rollout is paused at an `indefinite` step (no `duration`):

```bash
# Promote to next step
kubectl argo rollouts promote inferflow-vllm -n inferflow

# Full promotion (skip remaining steps)
kubectl argo rollouts promote inferflow-vllm -n inferflow --full

# Abort and roll back to previous stable version
kubectl argo rollouts abort inferflow-vllm -n inferflow
kubectl argo rollouts undo inferflow-vllm -n inferflow
```

---

## Step 6 — Verify drift detection

The `cronjob-drift-detector` CronJob runs every 6 hours.  To trigger it
manually for verification:

```bash
kubectl create job --from=cronjob/drift-detector \
  drift-detector-manual-$(date +%s) \
  -n inferflow
```

Check the result:

```bash
# Latest job logs
kubectl logs job/<name> -n inferflow

# Prometheus metric
curl -s http://localhost:9090/api/v1/query \
  --data-urlencode 'query=inferflow_embedding_drift_share' \
  | jq '.data.result'
```

Grafana alert `EmbeddingDriftDetected` fires when `drift_share > 0.5` for
more than 15 minutes.

---

## Rollback Runbook

| Scenario | Action |
|----------|--------|
| Analysis fails during canary | Argo Rollouts auto-aborts and rolls back to stable |
| Drift detected after full rollout | Run `kubectl argo rollouts undo inferflow-vllm -n inferflow` |
| MLflow promotion error | Re-run `promote-model.sh` — idempotent |
| Image pull error | Check GHCR credentials: `kubectl get secret ghcr-secret -n inferflow` |

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `MLFLOW_TRACKING_URI` | — | MLflow server URL (required) |
| `ROLLOUT_NAMESPACE` | `inferflow` | K8s namespace of the Rollout |
| `ROLLOUT_NAME` | `inferflow-vllm` | Name of the Argo Rollout resource |
| `CONTAINER_NAME` | `vllm` | Container name inside the Rollout pod spec |
| `DRIFT_PUSHGATEWAY_URL` | `http://prometheus-pushgateway…` | Push Gateway for drift metrics |
| `DRIFT_MLFLOW_TRACKING_URI` | `http://mlflow.mlflow…` | MLflow for drift detector |
| `DRIFT_THRESHOLD` | `0.5` | PSI threshold above which drift is reported |

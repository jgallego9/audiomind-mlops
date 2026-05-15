# AudioMind MLOps Platform — Backlog

> **Objetivo**: Portfolio project que posiciona como Senior MLOps Engineer.
> **Caso de uso**: Audio → Whisper (STT) → LLM analysis → Embeddings → RAG search
> **Estado actual**: Configuración inicial
> **Python**: 3.13 · **Licencia**: MIT

> **Workflow de commits**: tras cada tarea numerada se proporciona un mensaje de commit en formato Conventional Commits para mantener un historial granular y legible.

---

## Estándares de código

> Estos estándares son **no negociables** en todas las tareas. Cada tarea se considera incompleta si no los cumple.

### Calidad general

- Toda adición de código debe pasar el gate `make ci` (`lint` + `typecheck` + `test`) antes de considerarse lista.
- No se admite código muerto: campos de configuración declarados deben conectarse a su uso real.
- Las constantes "mágicas" numéricas o de cadena deben provenir de `Settings` cuando afecten al comportamiento en producción.
- Errores capturados con `except Exception` solo se permiten con `# noqa: BLE001` documentado y `exc_info=True` cuando hay logging.

### Linter — ruff

| Parámetro | Valor |
|---|---|
| Versión mínima | `>=0.15` (pin en pre-commit al exact rev) |
| Reglas activas | `E, W, F, I, N, UP, B, A, C4, SIM, RUF` (ver `[tool.ruff.lint]` en `pyproject.toml`) |
| Auto-fix | `ruff check --fix` en pre-commit y `make lint-fix` |
| Formatter | `ruff format` — equivalente Black, line-length 88 |
| Ejecución local | `make lint` / `make lint-fix` / `make format` |
| Pre-commit hook | `ruff` + `ruff-format` del repo `astral-sh/ruff-pre-commit` |

Reglas clave aplicadas:
- `I` (isort): imports ordenados en tres bloques (stdlib / third-party / local)
- `UP` (pyupgrade): sintaxis Python 3.12+ (`datetime.UTC`, `X | Y`, `list[...]`)
- `B` (flake8-bugbear): patrones comunes de bugs (e.g. mutable defaults)
- `A` (shadowing builtins), `C4` (comprensiones), `SIM` (simplificaciones)
- `RUF` (Ruff-specific): reglas propias de Ruff

### Type checker — mypy

| Parámetro | Valor |
|---|---|
| Versión mínima | `>=2.0` |
| Modo | `strict = true` (incluye `warn_unused_ignores`, `disallow_untyped_defs`, `no_implicit_optional`, etc.) |
| Plugin | `pydantic.mypy` |
| Invocación | **Por servicio** desde su directorio: `cd services/<svc> && uv run mypy app/` |
| Alias de tipos genéricos | `Redis` sin parámetro (no genérico en redis-py 7.x); `# type: ignore[misc]` sólo para métodos con union-return en stubs de redis |
| Overrides permitidos | `slowapi.*`, `opentelemetry.*` → `ignore_missing_imports = true` |
| `# type: ignore` | Solo cuando mypy tiene falso positivo documentado; **nunca** `[import-untyped]` en paquetes con stubs propios |

### Tests — pytest

| Parámetro | Valor |
|---|---|
| Versión mínima | `pytest>=8`, `pytest-asyncio>=0.24`, `pytest-cov>=5` |
| Modo asyncio | `asyncio_mode = "auto"` — todos los `async def test_*` corren sin decorador extra |
| Coverage mínimo | **80%** (gate de CI, falla el build si no se alcanza) |
| Configuración | `addopts = "--cov=services --cov-report=term-missing --cov-report=xml"` |
| Estructura | `services/<svc>/tests/` con `__init__.py`; tests unitarios en `test_<módulo>.py` |
| Mocking | `pytest-mock` / `unittest.mock`; dependencias FastAPI via `app.dependency_overrides` |
| Fixtures de Redis | `fakeredis[aioredis]` para tests sin infraestructura real |
| Fixtures de settings | `get_settings.cache_clear()` en `autouse` fixture para aislar settings entre tests |
| Nombrado | `test_<qué>_<condición>_<resultado_esperado>` — e.g. `test_transcribe_missing_auth_returns_401` |
| Cobertura de ramas críticas | Auth (401/403), health checks, job lifecycle (pending→processing→completed/failed) |

### Pre-commit

Hooks en orden de ejecución:

1. `ruff --fix` — lint con auto-fix
2. `ruff-format` — formato
3. `mypy (api-gateway)` — `bash -c "cd services/api-gateway && uv run --frozen mypy app/"`
4. `mypy (worker)` — `bash -c "cd services/worker && uv run --frozen mypy app/"`
5. `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`, `check-merge-conflict`, `detect-private-key`

Instalar: `make pre-commit-install`. Ejecutar en todos los ficheros: `make pre-commit-run`.

### Seguridad

- Sin `# nosec` sin justificación documentada.
- Sin credenciales en código; secrets vía `SecretStr` + variables de entorno.
- Dependencias auditadas: sin paquetes unmaintained ni con CVEs activos (passlib → bcrypt; python-jose → PyJWT).
- Trivy target: **0 critical** (gate en CI, fase 3).

---

## Épicas y tareas

### FASE 1 — Core Services (Docker Compose local)

- [x] **F1-1** Scaffold del proyecto: estructura de carpetas, `Makefile`, `.gitignore`, `.pre-commit-config.yaml`, `pyproject.toml` (Python 3.13, ruff + mypy con plugin `pydantic.mypy`)
- [x] **F1-2** `services/api-gateway/`: FastAPI con JWT auth (python-jose), rate limiting (slowapi), health check `/health` y `/ready`
- [x] **F1-3** Integración OpenTelemetry en api-gateway: tracing con Jaeger exporter, middleware para span automático por request
- [x] **F1-4** `docker-compose.yml` local completo: api-gateway, Redis, Qdrant, Jaeger; profiles `mlops` (Postgres + MLflow) y `models` (Whisper CPU + Ollama)
- [x] **F1-5** Async inference pipeline vía Redis Streams: api-gateway publica job, worker consume, respuesta via polling o WebSocket
- [x] **F1-6** RAG pipeline: indexar transcripciones en Qdrant, búsqueda semántica `/search`
- [x] **F1-7** `scripts/demo.sh`: sube audio → transcribe → analiza → almacena → busca semánticamente
- [x] **F1-8** Tests unitarios + integración con pytest (coverage > 80%)
- [x] **F1-README** README profesional base: descripción del proyecto, diagrama de arquitectura, quickstart Docker Compose, badges: CI (GitHub Actions) · Coverage (Codecov) · Python 3.13 · License MIT

---

### FASE 2 — Kubernetes + Helm

- [x] **F2-1** kind cluster local con `cluster.yaml` (multi-node: 1 control-plane + 2 workers)
- [x] **F2-2** Helm chart `infra/helm/audiomind/`: subchart por componente, `values.yaml` base + overlays por entorno
- [x] **F2-3** NVIDIA GPU Operator desplegado via Helm (`infra/helm/gpu-operator/`)
  - Gestiona drivers, container toolkit, device plugin, DCGM automáticamente
  - Configuración time-slicing para entornos sin GPU dedicada
- [x] **F2-4** Pods vLLM con recursos GPU correctos: `nvidia.com/gpu: 1`, `nodeSelector`, `tolerations`
- [x] **F2-5** HPAs para api-gateway basados en latencia (custom metrics via KEDA o Prometheus Adapter)
- [x] **F2-6** PodDisruptionBudgets, resource quotas y limit ranges por namespace
- [x] **F2-7** Helm chart `infra/helm/monitoring/`: kube-prometheus-stack + Loki + Grafana + Jaeger
- [x] **F2-8** External Secrets Operator + Ingress NGINX + cert-manager (self-signed local)
- [x] **F2-9** `Makefile` targets: `make kind-up`, `make helm-install`, `make helm-upgrade`, `make kind-down` (base añadida; pendiente completar Helm tras F2-2)
- [x] **F2-README** Actualizar README: sección Kubernetes + Helm, diagrama de despliegue en kind, badge versión Helm chart

---

### FASE 3 — GitOps CI/CD

- [x] **F3-1** ArgoCD instalado en namespace `argocd`, UI expuesta via port-forward o Ingress
  - Helm wrapper chart `infra/helm/argocd/` con dependencia `argo/argo-cd 9.5.14` (ArgoCD v3.4.2)
  - `values.yaml` base (Ingress nginx, `argocd.audiomind.local`) + `values-dev.yaml` (NodePort 30880)
- [x] **F3-2** `infra/k8s/argocd/applicationset.yaml`: dos ApplicationSets con List generator
  - `audiomind-auto-sync` → dev (automated prune + selfHeal)
  - `audiomind-manual-sync` → staging, prod (manual approval)
  - `goTemplate: true`, `goTemplateOptions: ["missingkey=error"]`
- [x] **F3-3** GitHub Actions workflow `.github/workflows/ci.yml`:
  - Job 1 `lint-test`: ruff · mypy · pytest --cov 80% · helm lint · yamllint
  - Job 2 `build-push` (matrix: api-gateway, worker): buildx → GHCR → Trivy (CRITICAL exit-1) → SARIF
  - Job 3 `bump-tag`: yq bump image tags in `values.yaml` → `[skip ci]` commit
  - All action versions pinned to SHA-equivalent semver tags
- [x] **F3-4** ArgoCD auto-sync en rama `main` (dev), manual approval en staging/prod
- [x] **F3-5** `infra/k8s/argocd/app-of-apps.yaml`: root Application `audiomind-root` gestiona AppProject + ApplicationSets
  - `infra/k8s/argocd/project.yaml`: AppProject `audiomind` con source repo + destination namespaces
- [x] **F3-6** Gestión de secretos en CI: `GITHUB_TOKEN` para GHCR (mismo repo); OIDC pattern documentado para cloud providers
  - Makefile targets: `helm-argocd-deps`, `helm-argocd-install`, `argocd-bootstrap`, `argocd-port-forward`
- [x] **F3-README** README actualizado: sección CI/CD + GitOps, badges workflow + GHCR, diagrama del pipeline ASCII, instrucciones ArgoCD bootstrap

---

### FASE 4 — Observabilidad

- [x] **F4-1** Métricas vLLM nativas en Prometheus:
  - `vllm:num_requests_running`, `vllm:gpu_cache_usage_perc`, `vllm:e2e_request_latency_seconds`
  - ServiceMonitor `infra/k8s/monitoring/servicemonitor-vllm.yaml`
- [x] **F4-2** Métricas GPU via DCGM Exporter:
  - `DCGM_FI_DEV_GPU_UTIL`, `DCGM_FI_DEV_FB_USED` (VRAM), `DCGM_FI_DEV_GPU_TEMP`
  - ServiceMonitor `infra/k8s/monitoring/servicemonitor-dcgm.yaml`
- [x] **F4-3** Grafana dashboards en `infra/k8s/monitoring/` (sidecar ConfigMaps con `grafana_dashboard: "1"`):
  - `grafana-dashboard-llm-inference.yaml`: latencia p50/p95/p99, throughput, KV-cache, TTFT
  - `grafana-dashboard-gpu-utilization.yaml`: utilización GPU, VRAM, temperatura, potencia (DCGM)
  - `grafana-dashboard-system-overview.yaml`: resumen end-to-end, pod health, error rates, logs Loki
- [x] **F4-4** PrometheusRules SLO en `infra/k8s/monitoring/`:
  - `prometheusrule-audiomind.yaml`: P95 latency > 2s, 5xx error rate > 5%, worker no jobs processed
  - `prometheusrule-vllm.yaml`: vLLM latency, queue depth, KV-cache high, preemption rate
  - `prometheusrule-gpu.yaml`: GPU util, VRAM > 90%, temperature, power draw
- [x] **F4-5** Instrumentación de servicios Python:
  - `api-gateway`: `prometheus-fastapi-instrumentator>=7.0` — expone `/metrics` en puerto 8000
  - `worker`: `prometheus-client>=0.21` — `start_http_server(9090)`, counters + histogram en `consumer.py`
  - Worker Helm Deployment: puerto `metrics: 9090` añadido; PodMonitor selecciona pods directamente
- [x] **F4-6** Prometheus configurado para recoger PrometheusRules de todos los namespaces:
  - `monitoring/values.yaml`: `ruleSelectorNilUsesHelmValues: false` + `ruleNamespaceSelector: {}`
- [x] **F4-README** Actualizar README: tabla de métricas por componente, tabla de manifests en `infra/k8s/monitoring/`

---

### FASE 5 — MLOps Avanzado

- [x] **F5-1** MLflow configurado en Kubernetes: tracking server con PostgreSQL backend + S3/Minio artifact store
- [x] **F5-2** Logging automático de métricas de inferencia por versión de modelo (latencia, tokens/s, error rate) a MLflow
- [x] **F5-3** `scripts/promote-model.sh`: registra modelo en MLflow → actualiza `infra/helm/audiomind/values.yaml` con nuevo tag → ArgoCD sync
- [x] **F5-4** Argo Rollouts canary en `infra/k8s/argo-rollouts/`:
  - Rollout de nueva versión de modelo: 10% → 50% → 100%
  - `AnalysisTemplate` que valida `vllm:request_success_ratio > 0.99` y `p95_latency < 2s`
  - Auto-rollback si métricas fallan durante la ventana de análisis
- [x] **F5-5** Evidently en `services/drift-detector/`:
  - CronJob Kubernetes: ejecuta drift detection cada 6h en transcripciones recientes
  - Publica métricas de drift a Prometheus → alerta en Grafana si drift > umbral
- [x] **F5-6** Documentación del workflow completo: "cómo hacer un deploy de un nuevo modelo"
- [x] **F5-README** Actualizar README: sección MLOps workflow, diagrama canary deploy (10% → 50% → 100%), tabla de métricas de evaluación automática

---

### FASE 6 — Terraform IaC ✅ commit `8f591bf`

- [x] **F6-1** `infra/terraform/modules/k8s-cluster/`: módulo cloud-agnostic con variables `cluster_name`, `node_count`, `gpu_node_count`, `gpu_instance_type`
- [x] **F6-2** `infra/terraform/envs/local/`: kind cluster + MetalLB (tehcyx/kind ~> 0.11)
- [x] **F6-3** `infra/terraform/envs/aws/`: EKS `~> 21.0` + VPC `~> 6.6` + managed node groups (CPU: `t3.xlarge`, GPU: `g4dn.xlarge`), IRSA, ECR con lifecycle policies
- [x] **F6-4** `infra/terraform/envs/gcp/`: GKE `~> 44.1` + Workload Identity + Artifact Registry + GPU pool (T4)
- [x] **F6-5** `terraform.tfvars` excluidos de git; `.tfvars.example` incluidos en todos los envs
- [x] **F6-6** `make terraform-{init,plan,apply,destroy}-{local,aws,gcp}` targets en `Makefile`
- [x] **F6-README** README: sección IaC con tabla de clouds, quickstart multi-cloud

---

### FASE 7 — Generic Inference Platform

> **Objetivo**: convertir el repo en una plataforma reutilizable donde cualquier pipeline de ML/AI (no solo Audio→Whisper→RAG) se define como código, se despliega con un único comando y sus steps escalan de forma independiente. Inspirado en el [V2 Inference Protocol de KServe](https://kserve.github.io/website/), los inference graphs de [Seldon Core 2](https://docs.seldon.ai/seldon-core-2), y el modelo de deployment composition de [Ray Serve](https://docs.ray.io/en/latest/serve/).

**Concepto central — tres capas desacopladas** (hoy fundidas en código):

| Capa | Qué es | Dónde vive |
|---|---|---|
| **Step** | Unidad atómica de inferencia: imagen Docker + contrato `/predict` V2 | `steps/<name>/` |
| **Pipeline** | Grafo de steps declarado en YAML, sin lógica de negocio | `pipelines/<name>/pipeline.yaml` |
| **Runtime** | Api-gateway + worker router genéricos; ejecutan cualquier pipeline sin recompilarse | `services/` (refactorizado) |

**Fricciones identificadas en el código actual** que esta fase debe eliminar antes de añadir nuevas capas:

| Fricción | Fichero(s) afectados | Impacto |
|---|---|---|
| `_STREAM_KEY` y `_JOB_KEY_PREFIX` duplicados sin fuente de verdad | `consumer.py` + `routes/jobs.py` | Jobs silenciosamente perdidos si las constantes divergen |
| `qdrant_collection` es `"transcriptions"` en api-gateway/worker pero `"audiomind"` en drift-detector | `config.py` ×2, `settings.py` | Drift-detector monitoriza una colección vacía; error silencioso |
| Modelo de embeddings descargado y bakeado en imagen Docker (`BAAI/bge-small-en-v1.5`) | `Dockerfile` ×2 | Cambiar modelo = rebuild de la imagen (~2 min); no es configuración, es código |
| `mock_transcribe` llamado directamente desde `consumer.py` sin abstracción | `consumer.py`, `processors/transcribe.py` | Sustituir por Whisper real requiere refactor del consumer, no solo cambiar un env var |
| Tipo de job `"transcribe"` hardcodeado en la ruta; sin schema del payload | `routes/jobs.py` | Añadir un campo al job (prioridad, dominio) exige editar enqueue y consumer coordinadamente |
| Tags `latest` en docker-compose para Whisper y Ollama | `docker-compose.yml` | Builds no reproducibles; cambio de comportamiento silencioso tras `docker pull` |
| Sin `.env.example`; variables requeridas solo visibles leyendo código | `docker-compose.yml`, `config.py` ×3 | First-time setup por ensayo y error |

- [x] **F7-0** Limpieza de deuda técnica previa a la refactorización — prerequisito bloqueante para F7-1+:
  - Extraer `STREAM_KEY`, `CONSUMER_GROUP` y `JOB_KEY_PREFIX` a un módulo compartido `services/shared/streams.py` importado por api-gateway y worker; eliminar duplicados
  - Alinear `qdrant_collection` en los tres servicios al mismo valor por defecto (`"transcriptions"`); añadir test de integración que valide que los tres apuntan al mismo nombre
  - Fijar tags de Whisper ASR (`ahmetoner/whisper-asr-webservice:v1.5.0` o último tag estable) y Ollama (`ollama/ollama:0.6.x`) en `docker-compose.yml`; nunca `latest` en servicios que afectan al pipeline
  - Crear `.env.example` en la raíz con todas las variables requeridas agrupadas por servicio, con comentarios que expliquen el impacto de cada una y un valor seguro de ejemplo
  - Definir `JobPayload` como modelo Pydantic en `services/shared/schemas.py`; api-gateway lo serializa a Redis Streams, consumer lo deserializa y valida; errores de schema visibles en lugar de silenciosos

- [x] **F7-1** Step SDK y protocolo — biblioteca interna `services/step-sdk/` (Python package):
  - Convención de nombrado: `step-{tarea}-{implementación}` — la tarea define el contrato (schema.json compartido), la implementación es intercambiable; ejemplos: `step-stt-whisper`, `step-stt-faster-whisper`, `step-embed-fastembed`, `step-embed-openai`. Cambiar de Whisper a faster-whisper es cambiar una línea en `pipeline.yaml`, el grafo no cambia
  - **Task registry**: `tasks/<nombre>/schema.json` como fuente de verdad de los contratos I/O; 7 tareas built-in incluidas en el repo:
    - `stt`: `{audio_url, language}` → `{text, language, duration_s}`
    - `embed`: `{text}` → `{vector: float[], model}`
    - `llm-chat`: `{messages: [{role, content}], parameters}` → `{content, usage}`
    - `vector-index`: `{id, vector: float[], metadata}` → `{indexed: bool}`
    - `vector-search`: `{vector: float[], top_k, filters}` → `{results: [{id, score, metadata}]}`
    - `vision-embed`: `{image_url}` → `{vector: float[], model}`
    - `rerank`: `{query, documents: [str]}` → `{ranked: [{index, score}]}`
  - **Tareas custom**: el usuario define sus propias tareas creando `tasks/<nombre>/schema.json`; `inferflow task new <nombre>` lanza un prompt interactivo para definir los campos I/O; cualquier step que implemente esa tarea es automáticamente intercambiable con los demás
  - Contrato HTTP: `POST /predict` con body `{inputs: [{name, shape, datatype, data}], parameters: {}}` y respuesta `{outputs: [...]}` (V2 Inference Protocol)
  - `GET /health/ready` y `GET /health/live` obligatorios; `ready` devuelve `503` con `{"status": "downloading_model", "progress": 0.42}` mientras el modelo se descarga en el primer arranque — evita que el router encole requests hacia un step no listo
  - Clase base `BaseStep` con validación de schema JSON automática, `@step` decorator, logging estructurado y métricas Prometheus estándar: `step_request_duration_seconds`, `step_requests_total{status}`
  - `GET /info` obligatorio: devuelve `{name, task, implementation, version, schema_input, schema_output, model_id}`; permite al router introspeccionar el step sin leer el filesystem

- [x] **F7-2** Step registry — `steps/` como catálogo organizado por tarea e implementación:
  - `steps/stt-whisper/` — tarea: speech-to-text; impl: OpenAI Whisper; `STT_MODEL` configurable (`base`/`small`/`medium`/`large-v3`); pesos descargados en primer arranque a volumen `/models`, no bakeados en imagen
  - `steps/stt-faster-whisper/` — misma tarea, misma `schema.json`; impl: faster-whisper (CPU-friendly, 4× más rápido que Whisper en CPU); drop-in replacement de `step-stt-whisper` cambiando solo la `image:` en `pipeline.yaml`
  - `steps/embed-fastembed/` — tarea: embeddings; impl: FastEmbed; `EMBED_MODEL` como env var en runtime; modelo descargado a `/models`, sin rebuild
  - `steps/llm-chat-vllm/` — tarea: chat completion; impl: vLLM OpenAI-compatible API; `LLM_BASE_URL` + `LLM_MODEL` como env vars; stateless (no descarga pesos, delega en servidor vLLM externo)
  - `steps/llm-chat-ollama/` — misma tarea, misma `schema.json`; impl: Ollama; permite swap a modelo local sin vLLM
  - `steps/vector-index-qdrant/` — tarea: indexar vectores; impl: Qdrant; `QDRANT_URL`, `QDRANT_COLLECTION`, `QDRANT_VECTOR_SIZE`; crea la colección si no existe (elimina el error silencioso actual)
  - `steps/vector-search-qdrant/` — tarea: buscar vectores; impl: Qdrant; mismas variables + `SEARCH_LIMIT`, `SCORE_THRESHOLD`
  - Cada step: `Dockerfile`, `predict.py` (hereda `BaseStep`), `schema.json` (idéntico para todos los steps de la misma tarea), `VERSION`, `README.md` con tabla de env vars y ejemplo de pipeline.yaml, tests unitarios con mock del modelo

- [x] **F7-3** Pipeline-as-code — `pipelines/<name>/pipeline.yaml` define el grafo:
  ```yaml
  name: audio-rag
  version: "1.0"
  trigger:
    type: redis-stream
    stream: "pipelines:audio-rag:jobs"   # ← derivado del name, nunca hardcodeado
  env:                                    # ← defaults compartidos por todos los steps
    QDRANT_COLLECTION: "transcriptions"
    EMBED_MODEL: "BAAI/bge-small-en-v1.5"
  steps:
    - id: transcribe
      image: ghcr.io/jgallego9/step-stt-whisper:1.0.0
      env:
        STT_MODEL: "small"               # ← override por step
      resources: {gpu: "1"}
    - id: embed
      image: ghcr.io/jgallego9/step-embed-fastembed:1.0.0
      input_from: transcribe.outputs.text
    - id: index
      image: ghcr.io/jgallego9/step-vector-index-qdrant:1.0.0
      input_from: embed.outputs.vector
  ```
  Cambiar a faster-whisper (sin GPU) es una sola línea:
  ```yaml
      image: ghcr.io/jgallego9/step-stt-faster-whisper:1.0.0  # misma schema.json, drop-in
  ```
  - `env` a nivel de pipeline actúa como defaults; cada step puede sobreescribir con su propio `env`; env vars del host tienen prioridad sobre ambos
  - El nombre del stream Redis se deriva del nombre del pipeline (`pipelines:{name}:jobs`); elimina el `_STREAM_KEY` hardcodeado actual
  - Worker se convierte en **router genérico**: carga `pipeline.yaml` al inicio, construye el grafo en memoria, valida los schemas de input/output de steps contiguos antes de arrancar, y espera a que `GET /health/ready` de cada step responda 200 antes de procesar el primer job
  - Api-gateway expone `POST /v1/pipelines/{pipeline_id}/jobs` y `GET /v1/pipelines` (lista pipelines activos con su schema de input); elimina la ruta `/jobs` hardcodeada a `"transcribe"`
  - El router valida el payload de entrada contra el `schema.json` del primer step antes de encolar; errores de validación devuelven 422 con campo exacto

- [x] **F7-4** Helm chart genérico por pipeline — el chart principal instala runtime compartido; por cada pipeline en `pipelines/` el chart genera Deployments para sus steps vía `range`:
  ```yaml
  # values.yaml
  pipelines:
    audio-rag:
      enabled: true
      env:                              # ← hereda pipeline.yaml env, sobreescribible por entorno
        QDRANT_COLLECTION: "transcriptions"
        EMBEDDING_MODEL: "BAAI/bge-small-en-v1.5"
      steps:
        transcribe:
          image: "ghcr.io/jgallego9/step-stt-whisper:1.0.0"
          gpu: 1
          replicas: 1
          modelVolume: "/models"        # ← monta PVC para no re-descargar modelos en restart
        embed:
          image: "ghcr.io/jgallego9/step-embed-fastembed:1.0.0"
          replicas: 2
        index:
          image: "ghcr.io/jgallego9/step-vector-index-qdrant:1.0.0"
          replicas: 1
  ```
  - Cada step obtiene su propio Deployment, Service, HPA y PodDisruptionBudget generados automáticamente
  - Steps con `modelVolume` montan un PVC compartido (`models-cache`) para evitar descargar el mismo modelo en cada pod y en cada restart
  - Añadir un pipeline nuevo = añadir una entrada en `values.yaml` + el `pipeline.yaml`; cero cambios en templates

- [x] **F7-5** Demo de segundo pipeline — `pipelines/image-search/`: Image→CLIP→Qdrant, sin modificar runtime ni templates Helm. Valida que la plataforma es realmente genérica: el único código nuevo son `steps/vision-clip/` (nueva tarea: vision-embedding) y `pipelines/image-search/pipeline.yaml`; `step-vector-index-qdrant` y `step-vector-search-qdrant` se reutilizan sin cambios

- [x] **F7-6** CI por step — `steps/<name>/VERSION` como fuente de verdad del tag; GitHub Actions `step-ci.yml` con path filter: build + test + trivy scan + push a GHCR únicamente para los steps cuyos ficheros cambiaron en el PR; matriz dinámica generada con `git diff --name-only` para no buildear steps no modificados

- [ ] **F7-7** `inferflow` CLI — herramienta de developer experience dedicada, moderna y visualmente cuidada:
  > **Por qué no `make`**: Make no tiene discoverabilidad real, no hace tab-completion, no valida argumentos, es difícil en Windows y no permite prompts interactivos. Las herramientas del ecosistema ML más exitosas (BentoML, Modal, Replicate/Cog, ZenML) usan CLI dedicadas por la misma razón. `make` se conserva únicamente para targets de CI.

  **Stack técnico** — validado contra referentes directos del ecosistema ML:
  | Librería | Rol | Usado también en |
  |---|---|---|
  | `typer[all]` | Framework CLI (sobre Click, type hints como API) | `fastapi-cli` (mismo autor) |
  | `rich` | UI: paneles, tablas, progress, syntax highlight, spinners | `pip` ≥21, `hatch`, `bentoml`, `zenml`, `prefect`, `dvc` |
  | `questionary` | Wizard interactivo en `inferflow init` (select, texto, confirm) | `hatch init`, `cookiecutter` |
  | `httpx` | Llamadas a la API del runtime (pipeline run, status) | httpx es el cliente HTTP async estándar en el ecosistema FastAPI |
  | `pydantic` | Parsing y validación de `inferflow.yaml` y `pipeline.yaml` | Coherente con el resto del repo |
  | `python-dotenv` | Lectura y generación de `.env` | Estándar |
  | `docker` SDK | Operaciones locales (compose up, logs, volumes) | |
  | `kubernetes` SDK | Operaciones en cluster (port-forward, pod status, logs) | |

  Package en `tools/inferflow-cli/`; instalación: `uv tool install ./tools/inferflow-cli`.

  **Diseño visual** — inspirado en GitHub CLI + uv + BentoML:
  - Cabecera con panel Rich en cada comando principal: `╭─ Pipeline: audio-rag ──────────╮`
  - Spinners animados para operaciones asíncronas (`rich.status`)
  - Barras de progreso para descargas con velocidad y ETA (`rich.progress`)
  - Tablas con colores semánticos: ✔ verde (ready), ● amarillo (en progreso), ✗ rojo (error)
  - Syntax highlighting para output YAML/JSON (`rich.syntax`)
  - Todos los errores incluyen la siguiente acción sugerida en un panel separado
  - Paleta consistente: éxito=verde, advertencia=amarillo, error=rojo, info=azul/cyan

  **`inferflow.yaml`** — fichero de proyecto en la raíz del repo; fuente de verdad única para entornos y registry; elimina la dispersión de config actual:
  ```yaml
  name: inferflow-mlops
  registry: ghcr.io/jgallego9
  environments:
    local:
      context: docker-compose
      values: .env
    dev:
      context: kubernetes
      kubeconfig: ~/.kube/config
      namespace: audiomind-dev
      helm_values: infra/helm/audiomind/values-dev.yaml
      deploy: helm            # helm upgrade directo (iteración rápida)
    prod:
      namespace: audiomind-prod
      helm_values: infra/helm/audiomind/values.yaml
      deploy: argocd          # commit values.yaml → push → ArgoCD sync
      argocd_app: audiomind-prod
  pipelines_dir: pipelines/
  steps_dir:     steps/
  tasks_dir:     tasks/
  ```
  Precedencia de config (una sola regla que aprender): `.env` (secretos) > `pipeline.yaml` (config de pipeline) > `inferflow.yaml` (defaults de entorno). El usuario **nunca edita** `docker-compose.yml`, `values.yaml` ni manifests K8s directamente — la CLI los gestiona.

  **Superficie de comandos completa** (subcomandos por objeto, igual que `git`/`docker`/`kubectl`):
  ```
  inferflow init                              # wizard si no existe inferflow.yaml;
                                              # validación de prereqs si existe
                                              # (docker, kubectl, helm, .env, registry auth)

  inferflow task list                         # tabla: nombre, descripción, input/output, steps disponibles
  inferflow task new <nombre>                 # prompt interactivo → tasks/<nombre>/schema.json
  inferflow task show <nombre>                # schema completo + steps compatibles

  inferflow step list                         # tabla: nombre, tarea, versión, estado (built/not built)
  inferflow step new <tarea> <impl>           # scaffoldea steps/{tarea}-{impl}/; copia schema.json de la tarea
  inferflow step test <tarea>-<impl>          # pytest del step con output Rich
  inferflow step build <tarea>-<impl>         # docker buildx; muestra digest al finalizar
  inferflow step push <tarea>-<impl>          # push a GHCR; actualiza VERSION
  inferflow step show <tarea>-<impl>          # llama /info del step en vivo y formatea el output

  inferflow pipeline list                     # tabla: nombre, steps, entorno activo, estado
  inferflow pipeline new <nombre>             # genera pipeline.yaml comentado con ejemplos
  inferflow pipeline validate <nombre>        # YAML schema + compat. I/O entre steps + imágenes en GHCR
  inferflow pipeline dev <nombre>             # docker compose con solo los steps del pipeline
  inferflow pipeline run <nombre> \
    --input @audio.mp3 [--detach]             # bloquea con progreso por step por defecto;
                                              # --detach devuelve job ID inmediatamente
  inferflow pipeline deploy <nombre> \
    --env <env>                               # dev → helm upgrade directo;
                                              # staging/prod → commit values + ArgoCD sync + wait
  inferflow pipeline status <nombre> \
    [--env <env>]                             # tabla: step, estado, pods, modelo activo, p95 latencia
  inferflow pipeline logs <nombre> \
    --step <step> [--env <env>] [--follow]
  inferflow pipeline scale <nombre> \
    --step <step> --replicas N --env <env>
  inferflow pipeline rollback <nombre> \
    --env <env>                               # helm rollback o ArgoCD rollback según entorno
  inferflow pipeline metrics <nombre> \
    [--env <env>]                             # p50/p95/p99 latencia + throughput desde Prometheus

  inferflow models prefetch <pipeline>        # arranca steps, espera /health/ready, muestra progreso
  inferflow models status <pipeline>          # tabla: step, modelo, tamaño, origen (caché/descargando)
  inferflow models clear <pipeline>           # limpia volumen de modelos del pipeline

  inferflow job status <job-id>               # estado de un job concreto (para flujos --detach)
  inferflow job result <job-id>               # output del job con syntax highlighting
  ```

  **Comportamiento de `inferflow init`**:
  - Si no existe `inferflow.yaml` — **wizard interactivo** (`questionary`): nombre del proyecto, registry, entornos; al terminar genera `inferflow.yaml` **y** un `.env` con `JWT_SECRET_KEY` autogenerado (`secrets.token_urlsafe(32)`) y el resto de variables con defaults locales seguros; el usuario no necesita copiar ni editar ningún fichero manualmente
  - Si existe `inferflow.yaml` — **modo validación**: comprueba Docker, kubectl, helm disponibles; verifica auth en registry; valida sintaxis del fichero; imprime tabla de estado de entornos con prereqs satisfechos/faltantes
  - En ambos casos termina con panel Rich "Next steps" con los 2–3 comandos más relevantes según el estado detectado
  - Para staging/prod los secretos reales se inyectan vía External Secrets Operator (ya implementado en F2-8); el `.env` solo aplica a entorno local y nunca se commitea

  **Shell completion**: `inferflow --install-completion` instala completion para bash/zsh/fish; tab-complete en nombres de pipelines, steps y tareas del proyecto actual

  **Endpoints de runtime** (en api-gateway, usados internamente por la CLI):
  - `GET /v1/pipelines` — lista pipelines activos
  - `GET /v1/pipelines/{id}/schema` — schema de input del pipeline
  - `GET /v1/pipelines/{id}/status` — estado de cada step en tiempo real

- [ ] **F7-README** Actualizar README: flujo de setup en **2 pasos** (`git clone` + `inferflow init`, sin edición manual de ficheros); flujo completo de 5 etapas (setup → demo → custom pipeline → nuevo step → deploy) usando únicamente comandos `inferflow`; tabla de tareas built-in con schemas I/O; diagrama de arquitectura de tres capas (step / pipeline / runtime); tabla de steps disponibles con tarea, impl, versión y env vars clave; sección de instalación de la CLI (`uv tool install`); captura o GIF del output visual de la CLI

---

## Métricas de éxito del portfolio

| Métrica | Target |
|---|---|
| P95 latencia transcripción (30s audio) | < 5s con GPU |
| P95 latencia LLM (análisis) | < 2s con GPU |
| Test coverage | > 80% |
| Trivy vulnerabilities (critical) | 0 |
| Tiempo de deploy canary completo | < 10 min |
| Rollback automático | < 2 min |

---

## Decisiones técnicas registradas

| Decisión | Alternativa descartada | Motivo |
|---|---|---|
| vLLM como motor de inferencia | FastAPI + HuggingFace Transformers | vLLM es el estándar de mercado (80k stars), ya incluye Prometheus, Helm charts y soporte Whisper |
| GPU Operator | Instalación manual de drivers | Gestión automática en Kubernetes, estándar NVIDIA |
| Argo Rollouts para canary | Istio traffic splitting | Menos complejidad, integración nativa con Prometheus |
| ArgoCD ApplicationSet | Flux | Mejor UI, más adopción en job listings |
| Evidently para drift | Custom scripts | Framework maduro, integración Prometheus nativa |
| Redis Streams para queue | Kafka | Menor overhead para escala de portfolio |
| mypy + plugin pydantic.mypy | ty (Astral, beta 0.0.x) | ty sin soporte Pydantic; mypy es lo que usa FastAPI en producción |
| Codecov | shields.io custom badge | Estándar de la industria para portfolios Python públicos, gratuito para repos open source |
| Python 3.13 | 3.12 | Última versión estable, mejoras de rendimiento GIL-optional y mejor error messages |
| V2 Inference Protocol para steps | API custom por step | Interoperabilidad con KServe/Seldon; contratos explícitos facilitan testing y swap |
| Pipeline-as-code (YAML grafo) | Pipeline hardcodeado en Python | Añadir un pipeline nuevo no requiere recompilar el runtime; el grafo es auditable en git |
| Step como imagen Docker independiente | Monolito worker con todos los modelos | Cada step versiona, escala y despliega de forma autónoma; CI por step evita rebuilds innecesarios |
| `release-please` para semantic versioning | `semantic-release` | Soporte nativo de monorepo con componentes independientes; sin dependencia de npm; genera GitHub Releases + CHANGELOG automáticamente desde Conventional Commits |
| Naming convention `step-{tarea}-{impl}` | `step-{impl}` (e.g. `step-whisper`) | Separar tarea de implementación garantiza que todos los steps de la misma tarea comparten `schema.json`; cambiar de Whisper a faster-whisper es una línea en `pipeline.yaml`, no un refactor |
| Modelos descargados en runtime a volumen `/models` | Modelos bakeados en imagen Docker | Cambiar modelo es un env var, no un rebuild; imágenes más pequeñas y builds más rápidos; volumen persiste entre restarts evitando re-descarga |
| CLI Typer (`inferflow`) para DX de usuario | Targets `make` | Make sin discoverabilidad real, sin tab-completion, sin prompts interactivos y problemático en Windows; mismo patrón que BentoML, Modal, Replicate/Cog y ZenML; `make` se conserva sólo para CI |
| Task registry (`tasks/<nombre>/schema.json`) | Schema por step | Desacopla el contrato I/O de la implementación; permite tareas custom sin tocar código de plataforma; steps de la misma tarea son drop-in replacements garantizados |
| `inferflow.yaml` como fuente de verdad única de entornos | Config dispersa en docker-compose + Helm values + k8s envs | Un fichero; precedencia de config explícita; usuario nunca edita Helm ni docker-compose directamente; mismo patrón que `prefect.yaml` y ZenML stacks |
| `pipeline deploy` → Helm directo en dev, ArgoCD en staging/prod | Un solo mecanismo para todos los entornos | Dev necesita iteración rápida (helm upgrade directo); staging/prod requiere GitOps auditado (commit + ArgoCD sync); la CLI abstrae la diferencia con `--env` |
| `pipeline run` bloquea con progreso por defecto + `--detach` | Siempre async | DX más limpia para demos y testing; `--detach` + `inferflow job status/result` cubre casos de jobs largos |
| `rich` para UI de la CLI | Click sin formato, colorama | Rich es el estándar actual para CLIs Python modernas (uv, Hatch, BentoML, ZenML, Prefect, DVC, `pip` ≥21); paneles, tablas, spinners y progress bars de forma nativa |
| `typer` sobre Click raw | Click directo, argparse | Menos boilerplate; type hints como API; coherencia con FastAPI ya presente en el repo; misma combinación que `fastapi-cli` |
| `questionary` para wizard interactivo | `typer.prompt()` básico | Select lists, confirmaciones y texto con validación; misma librería que usa `hatch init` (gestor oficial de proyectos Python de PyPA) |
| `inferflow init` autogenera `.env` | Usuario copia `.env.example` manualmente | Elimina el único paso de setup que no tienen los referentes (Modal, BentoML, ZenML); JWT secret generado con `secrets.token_urlsafe(32)`; defaults locales seguros sin intervención humana |

---

### FASE 8 — Branding, Community & Launch

> **Objetivo**: convertir el repo en un proyecto de portfolio público de primer nivel — con identidad visual clara, documentación que entre por los ojos y toda la infraestructura de comunidad para que otros desarrolladores puedan explorar, reportar issues y contribuir.

#### Rename del repositorio

> `audiomind-mlops` describe el caso de uso original (audio → Whisper → RAG) pero ya no representa el proyecto tras la Fase 7, que lo convierte en una plataforma genérica de inferencia ML.

**Nombre propuesto**: `inferflow-mlops` — *"inference" + "workflow"*, captura la esencia de pipelines componibles de ML.

**Descripción propuesta**: *"A production-ready, pipeline-as-code ML inference platform. Define your AI pipeline in YAML, deploy with one command, scale each step independently."*

**Topics (GitHub)**: `mlops` · `inference` · `pipeline-as-code` · `kubernetes` · `helm` · `argocd` · `fastapi` · `redis-streams` · `vllm` · `python` · `docker` · `gitops` · `rag` · `llm`

- [ ] **F8-1** Rename del repositorio y actualización de referencias
  - Renombrar repo a `inferflow-mlops` y actualizar descripción + topics en GitHub Settings
  - Actualizar todas las referencias a `audiomind` en `values.yaml`, `applicationset.yaml`, namespaces, Helm charts, Makefile, CI workflows y README
  - Actualizar imágenes GHCR: `ghcr.io/jgallego9/inferflow-*`
  - La redirección automática de GitHub mantiene URLs antiguas funcionando; documentar el cambio en `CHANGELOG.md`

- [ ] **F8-2** README — identidad visual y demo rápida
  - Logo / banner de cabecera (1200×400, dark-mode friendly) generado con Figma o Canva; almacenado en `docs/assets/`
  - GIF animado de demo end-to-end: `scripts/demo.sh` en acción grabado con [`vhs`](https://github.com/charmbracelet/vhs) o `asciinema` → gif
  - Screenshots de los tres Grafana dashboards (GPU utilization, LLM inference, system overview) con datos reales
  - Screenshot de la ArgoCD UI mostrando el app-of-apps sincronizado
  - Diagrama de arquitectura de tres capas (Step / Pipeline / Runtime, Fase 7) como imagen SVG en `docs/assets/architecture.svg`
  - Diagrama de canary deploy (10% → 50% → 100%) en `docs/assets/canary-deploy.svg`

- [ ] **F8-3** README — contenido y estructura
  - Sección "Why this project" — elevator pitch de 3 bullets (problema → solución → diferencial competitivo)
  - Sección "Add a pipeline in 3 steps" con fragmento real de `pipeline.yaml` y los comandos de despliegue
  - Tabla "Available Steps": nombre, descripción, input/output schema, versión, badge CI individual
  - Sección "Tech Stack" con badges `shields.io` / `simple-icons` por categoría (runtime, infra, observability, MLOps)
  - Sección "Performance benchmarks" con tabla de métricas de éxito medidas (latencia, cobertura, Trivy)
  - Sección "Roadmap" enlazando al GitHub Project board
  - Carpeta `docs/` con guías detalladas: `architecture.md`, `adding-a-pipeline.md`, `adding-a-step.md`, `local-setup.md`

- [ ] **F8-4** Infraestructura de issues y PRs
  - `.github/ISSUE_TEMPLATE/bug_report.yml` — pasos de reproducción, logs, entorno (OS, k8s version, Python)
  - `.github/ISSUE_TEMPLATE/feature_request.yml` — problema, solución propuesta, alternativas consideradas
  - `.github/ISSUE_TEMPLATE/new_step.yml` — template específico: nombre del step, modelo base, schema input/output, caso de uso
  - `.github/ISSUE_TEMPLATE/config.yml` — deshabilita issues en blanco; redirige preguntas a Discussions
  - `.github/PULL_REQUEST_TEMPLATE.md` — checklist: tipo de cambio, issue relacionado, tests añadidos, docs actualizados, `make ci` pasado

- [ ] **F8-5** Guías de comunidad
  - `CONTRIBUTING.md` — fork → branch naming (`feat/`, `fix/`, `step/`) → commit convention → pre-commit setup → PR flow
  - `CODE_OF_CONDUCT.md` — Contributor Covenant v2.1
  - `.github/SECURITY.md` — política de disclosure: reporte privado via GitHub Security Advisories, SLA de respuesta 72h
  - `CHANGELOG.md` — bootstrapeado manualmente con el historial por fases; a partir de F8-7 lo mantiene `release-please` de forma automática

- [ ] **F8-6** GitHub project hygiene
  - Labels: `bug` · `enhancement` · `new-step` · `new-pipeline` · `documentation` · `good first issue` · `help wanted` · `breaking-change` · `performance`; creados con `scripts/setup-labels.sh` usando `gh label create`
  - GitHub Project board (kanban) enlazado al repo: columnas Backlog / In Progress / In Review / Done
  - GitHub Discussions activado: categorías Q&A, Ideas, Show and Tell
  - Añadir sección "Contributing" al README con enlace al label `good first issue` para onboarding de nuevos colaboradores

- [ ] **F8-7** Semantic versioning automático con `release-please`
  - Añadir `.github/workflows/release.yml` con el job `release-please-action` (Google `release-please-action@v4`)
  - Estrategia `simple` con `release-type: python`; `version-file: version.txt` en raíz del repo como fuente de verdad
  - Flujo resultante:
    1. Cada push a `main` con commits Conventional Commits (`feat:`, `fix:`, `feat!:`) actualiza automáticamente un PR de release con el `CHANGELOG.md` generado y la versión bumpeada (`semver`: `feat` → minor, `fix` → patch, `feat!` / `BREAKING CHANGE` → major)
    2. Al hacer merge del PR de release, `release-please` crea el git tag `v*.*.*` y el GitHub Release con release notes
    3. Job `build-push` del CI existente reacciona al tag `v*.*.*` y publica imágenes con ese tag en GHCR (añadir `type=semver,pattern={{version}}` en `docker/metadata-action`)
    4. Job `bump-tag` actualiza `values.yaml` con el tag semver en lugar del SHA: `apiGateway.image.tag: "v1.2.0"`
  - Step versioning (F7-6): cada `steps/<name>/VERSION` actúa como `component` de `release-please` con su propio ciclo semver independiente; el workflow `step-ci.yml` usa ese tag para publicar `ghcr.io/jgallego9/inferflow-step-<name>:v*.*.*`
  - El `CHANGELOG.md` de raíz agregará entradas de todos los componentes (runtime + steps); cada step tendrá su propio `CHANGELOG.md` en `steps/<name>/`
  - Añadir entrada en tabla "Decisiones técnicas": `release-please` vs `semantic-release` (motivo: soporte nativo de monorepo con componentes independientes y sin necesidad de npm)

- [ ] **F8-README** Revisión final del README — lectura completa desde perspectiva de recruiter nuevo: todos los assets en su lugar, todos los enlaces verificados, tiempo de lectura ≤ 5 min hasta el primer `docker compose up`

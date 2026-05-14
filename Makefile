.DEFAULT_GOAL := help

KIND_CLUSTER_NAME   ?= audiomind
KIND_CONFIG         ?= infra/kind/cluster.yaml
HELM_RELEASE        ?= audiomind
HELM_NAMESPACE      ?= audiomind
HELM_CHART          ?= infra/helm/audiomind
HELM_VALUES         ?= $(HELM_CHART)/values-dev.yaml

# Infrastructure charts
HELM_MONITORING_CHART   ?= infra/helm/monitoring
HELM_MONITORING_VALUES  ?= $(HELM_MONITORING_CHART)/values-dev.yaml
HELM_MONITORING_NS      ?= monitoring

HELM_GPU_CHART          ?= infra/helm/gpu-operator
HELM_GPU_VALUES         ?= $(HELM_GPU_CHART)/values-dev.yaml
HELM_GPU_NS             ?= gpu-operator

HELM_KEDA_CHART         ?= infra/helm/keda
HELM_KEDA_NS            ?= keda

HELM_INGRESS_CHART      ?= infra/helm/ingress
HELM_INGRESS_VALUES     ?= $(HELM_INGRESS_CHART)/values-dev.yaml
HELM_INGRESS_NS         ?= ingress-nginx

HELM_ESO_CHART          ?= infra/helm/external-secrets
HELM_ESO_NS             ?= external-secrets

.PHONY: help install lock lint lint-fix format typecheck test test-fast ci \
        pre-commit-install pre-commit-run \
        up up-mlops up-all down logs ps build \
        kind-up kind-status kind-down \
        helm-deps helm-lint helm-install helm-upgrade \
        helm-monitoring-deps helm-monitoring-install helm-monitoring-upgrade \
        helm-gpu-deps helm-gpu-install \
        helm-keda-deps helm-keda-install \
        helm-ingress-deps helm-ingress-install \
        helm-eso-deps helm-eso-install \
        infra-up infra-namespaces

# ---------------------------------------------------------------------------
# Dev setup
# ---------------------------------------------------------------------------
install:  ## Install workspace deps + dev tools (run once after clone)
	uv sync --all-packages --dev

lock:  ## Regenerate uv.lock after editing any pyproject.toml
	uv lock

pre-commit-install:  ## Install git pre-commit hooks
	uv run pre-commit install

# ---------------------------------------------------------------------------
# Code quality
# ---------------------------------------------------------------------------
lint:  ## Run ruff linter
	uv run ruff check .

lint-fix:  ## Run ruff linter with auto-fix
	uv run ruff check --fix .

format:  ## Run ruff formatter
	uv run ruff format .

typecheck:  ## Run mypy type checker per service (avoids dual-app namespace conflict)
	cd services/api-gateway && uv run mypy app/
	cd services/worker && uv run mypy app/

pre-commit-run:  ## Run pre-commit on all files
	uv run pre-commit run --all-files

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
test:  ## Run pytest with coverage
	uv run pytest

test-fast:  ## Run pytest without coverage (faster)
	uv run pytest --no-cov

# ---------------------------------------------------------------------------
# Docker Compose
# ---------------------------------------------------------------------------
build:  ## Build Docker images
	docker compose build

up:  ## Start core services (api-gateway, redis, qdrant, jaeger)
	docker compose up -d

up-mlops:  ## Start core + MLOps services (+ postgres, mlflow)
	docker compose --profile mlops up -d

up-all:  ## Start all services including AI models (+ whisper, ollama)
	docker compose --profile mlops --profile models up -d

down:  ## Stop and remove containers (preserves volumes)
	docker compose down

logs:  ## Tail logs for all running services
	docker compose logs -f

ps:  ## Show status of all services
	docker compose ps

# ---------------------------------------------------------------------------
# Kubernetes + Helm
# ---------------------------------------------------------------------------
kind-up:  ## Create the local multi-node kind cluster
	@command -v kind >/dev/null 2>&1 || { echo "ERROR: kind is required. Install it from https://kind.sigs.k8s.io/docs/user/quick-start/"; exit 127; }
	@command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker is required before creating the kind cluster."; exit 127; }
	kind create cluster --name $(KIND_CLUSTER_NAME) --config $(KIND_CONFIG)

kind-status:  ## Show local kind cluster nodes and namespaces
	@command -v kubectl >/dev/null 2>&1 || { echo "ERROR: kubectl is required. Install it from https://kubernetes.io/docs/tasks/tools/"; exit 127; }
	kubectl cluster-info --context kind-$(KIND_CLUSTER_NAME)
	kubectl get nodes -o wide
	kubectl get namespaces

kind-down:  ## Delete the local kind cluster
	@command -v kind >/dev/null 2>&1 || { echo "ERROR: kind is required. Install it from https://kind.sigs.k8s.io/docs/user/quick-start/"; exit 127; }
	kind delete cluster --name $(KIND_CLUSTER_NAME)

helm-deps:  ## Download and extract Helm subchart dependencies (run once after clone)
	@command -v helm >/dev/null 2>&1 || { echo "ERROR: helm is required. Install it from https://helm.sh/docs/intro/install/"; exit 127; }
	helm dependency build $(HELM_CHART)
	@cd $(HELM_CHART)/charts && for f in *.tgz; do tar xzf "$$f"; done

helm-lint:  ## Lint the Helm chart
	@command -v helm >/dev/null 2>&1 || { echo "ERROR: helm is required."; exit 127; }
	helm lint $(HELM_CHART) -f $(HELM_VALUES)

helm-install:  ## Install the AudioMind Helm release
	@test -f $(HELM_CHART)/Chart.yaml || { echo "ERROR: Helm chart not found at $(HELM_CHART). Complete F2-2 before running this target."; exit 2; }
	@command -v helm >/dev/null 2>&1 || { echo "ERROR: helm is required. Install it from https://helm.sh/docs/intro/install/"; exit 127; }
	helm dependency build $(HELM_CHART)
	@cd $(HELM_CHART)/charts && for f in *.tgz; do tar xzf "$$f"; done
	helm install $(HELM_RELEASE) $(HELM_CHART) \
		--namespace $(HELM_NAMESPACE) --create-namespace \
		-f $(HELM_VALUES)

helm-upgrade:  ## Upgrade (or install if absent) the AudioMind Helm release
	@test -f $(HELM_CHART)/Chart.yaml || { echo "ERROR: Helm chart not found at $(HELM_CHART). Complete F2-2 before running this target."; exit 2; }
	@command -v helm >/dev/null 2>&1 || { echo "ERROR: helm is required. Install it from https://helm.sh/docs/intro/install/"; exit 127; }
	helm dependency build $(HELM_CHART)
	@cd $(HELM_CHART)/charts && for f in *.tgz; do tar xzf "$$f"; done
	helm upgrade --install $(HELM_RELEASE) $(HELM_CHART) \
		--namespace $(HELM_NAMESPACE) --create-namespace \
		-f $(HELM_VALUES)

# ---------------------------------------------------------------------------
# Monitoring stack (F2-7)
# ---------------------------------------------------------------------------
helm-monitoring-deps:  ## Download monitoring chart dependencies (kube-prometheus-stack, Loki, Jaeger)
	@command -v helm >/dev/null 2>&1 || { echo "ERROR: helm is required."; exit 127; }
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
	helm repo add grafana https://grafana.github.io/helm-charts 2>/dev/null || true
	helm repo add jaegertracing https://jaegertracing.github.io/helm-charts 2>/dev/null || true
	helm repo update
	helm dependency build $(HELM_MONITORING_CHART)

helm-monitoring-install:  ## Install the monitoring stack
	$(MAKE) helm-monitoring-deps
	helm upgrade --install audiomind-monitoring $(HELM_MONITORING_CHART) \
		--namespace $(HELM_MONITORING_NS) --create-namespace \
		-f $(HELM_MONITORING_VALUES)

helm-monitoring-upgrade:  ## Upgrade the monitoring stack
	$(MAKE) helm-monitoring-install

# ---------------------------------------------------------------------------
# GPU Operator (F2-3)
# ---------------------------------------------------------------------------
helm-gpu-deps:  ## Download GPU Operator chart dependency
	@command -v helm >/dev/null 2>&1 || { echo "ERROR: helm is required."; exit 127; }
	helm repo add nvidia https://helm.ngc.nvidia.com/nvidia 2>/dev/null || true
	helm repo update
	helm dependency build $(HELM_GPU_CHART)

helm-gpu-install:  ## Install NVIDIA GPU Operator (requires GPU node)
	$(MAKE) helm-gpu-deps
	kubectl apply -f infra/k8s/gpu/time-slicing-config.yaml 2>/dev/null || true
	helm upgrade --install gpu-operator $(HELM_GPU_CHART) \
		--namespace $(HELM_GPU_NS) --create-namespace \
		-f $(HELM_GPU_VALUES)

# ---------------------------------------------------------------------------
# KEDA (F2-5)
# ---------------------------------------------------------------------------
helm-keda-deps:  ## Download KEDA chart dependency
	@command -v helm >/dev/null 2>&1 || { echo "ERROR: helm is required."; exit 127; }
	helm repo add kedacore https://kedacore.github.io/charts 2>/dev/null || true
	helm repo update
	helm dependency build $(HELM_KEDA_CHART)

helm-keda-install:  ## Install KEDA and apply ScaledObjects
	$(MAKE) helm-keda-deps
	helm upgrade --install keda $(HELM_KEDA_CHART) \
		--namespace $(HELM_KEDA_NS) --create-namespace
	@echo "Waiting for KEDA CRDs..."
	kubectl wait --for condition=established crd/scaledobjects.keda.sh --timeout=60s
	kubectl apply -f infra/k8s/keda/ -n $(HELM_NAMESPACE)

# ---------------------------------------------------------------------------
# Ingress + cert-manager (F2-8)
# ---------------------------------------------------------------------------
helm-ingress-deps:  ## Download ingress-nginx + cert-manager chart dependencies
	@command -v helm >/dev/null 2>&1 || { echo "ERROR: helm is required."; exit 127; }
	helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx 2>/dev/null || true
	helm repo add jetstack https://charts.jetstack.io 2>/dev/null || true
	helm repo update
	helm dependency build $(HELM_INGRESS_CHART)

helm-ingress-install:  ## Install ingress-nginx and cert-manager
	$(MAKE) helm-ingress-deps
	helm upgrade --install audiomind-ingress $(HELM_INGRESS_CHART) \
		--namespace $(HELM_INGRESS_NS) --create-namespace \
		-f $(HELM_INGRESS_VALUES)
	@echo "Waiting for cert-manager webhook..."
	kubectl wait --for=condition=Available deployment/audiomind-ingress-cert-manager-webhook \
		-n $(HELM_INGRESS_NS) --timeout=120s 2>/dev/null || true
	kubectl apply -f infra/k8s/cert-manager/

# ---------------------------------------------------------------------------
# External Secrets Operator (F2-8)
# ---------------------------------------------------------------------------
helm-eso-deps:  ## Download External Secrets Operator chart dependency
	@command -v helm >/dev/null 2>&1 || { echo "ERROR: helm is required."; exit 127; }
	helm repo add external-secrets https://charts.external-secrets.io 2>/dev/null || true
	helm repo update
	helm dependency build $(HELM_ESO_CHART)

helm-eso-install:  ## Install External Secrets Operator
	$(MAKE) helm-eso-deps
	helm upgrade --install external-secrets $(HELM_ESO_CHART) \
		--namespace $(HELM_ESO_NS) --create-namespace

# ---------------------------------------------------------------------------
# Namespace setup (F2-6)
# ---------------------------------------------------------------------------
infra-namespaces:  ## Apply ResourceQuota and LimitRange to the audiomind namespace
	@command -v kubectl >/dev/null 2>&1 || { echo "ERROR: kubectl is required."; exit 127; }
	kubectl create namespace $(HELM_NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -f infra/k8s/namespaces/audiomind/

# ---------------------------------------------------------------------------
# Full local infra bootstrap (F2-3 through F2-8 in order)
# ---------------------------------------------------------------------------
infra-up:  ## Bootstrap the full local infra stack on a running kind cluster
	$(MAKE) infra-namespaces
	$(MAKE) helm-ingress-install
	$(MAKE) helm-monitoring-install
	$(MAKE) helm-keda-install
	$(MAKE) helm-eso-install
	$(MAKE) helm-install
	@echo ""
	@echo "✓ Full AudioMind infra deployed. Run 'make kind-status' to verify."

# ---------------------------------------------------------------------------
# CI gate (runs locally exactly what CI runs)
# ---------------------------------------------------------------------------
ci: lint typecheck test  ## Run full CI checks: lint + typecheck + test

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

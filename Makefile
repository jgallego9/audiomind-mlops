.DEFAULT_GOAL := help

KIND_CLUSTER_NAME ?= audiomind
KIND_CONFIG ?= infra/kind/cluster.yaml
HELM_RELEASE ?= audiomind
HELM_NAMESPACE ?= audiomind
HELM_CHART ?= infra/helm/audiomind

.PHONY: help install lock lint lint-fix format typecheck test test-fast ci \
        pre-commit-install pre-commit-run \
        up up-mlops up-all down logs ps build \
        kind-up kind-status kind-down helm-install helm-upgrade

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

helm-install:  ## Install the AudioMind Helm release (available after F2-2)
	@test -f $(HELM_CHART)/Chart.yaml || { echo "ERROR: Helm chart not found at $(HELM_CHART). Complete F2-2 before running this target."; exit 2; }
	@command -v helm >/dev/null 2>&1 || { echo "ERROR: helm is required. Install it from https://helm.sh/docs/intro/install/"; exit 127; }
	helm install $(HELM_RELEASE) $(HELM_CHART) --namespace $(HELM_NAMESPACE) --create-namespace

helm-upgrade:  ## Upgrade the AudioMind Helm release (available after F2-2)
	@test -f $(HELM_CHART)/Chart.yaml || { echo "ERROR: Helm chart not found at $(HELM_CHART). Complete F2-2 before running this target."; exit 2; }
	@command -v helm >/dev/null 2>&1 || { echo "ERROR: helm is required. Install it from https://helm.sh/docs/intro/install/"; exit 127; }
	helm upgrade $(HELM_RELEASE) $(HELM_CHART) --namespace $(HELM_NAMESPACE)

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

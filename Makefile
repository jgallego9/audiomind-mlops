.DEFAULT_GOAL := help

.PHONY: help install lock lint lint-fix format typecheck test test-fast ci \
        pre-commit-install pre-commit-run \
        up up-mlops up-all down logs ps build

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
# CI gate (runs locally exactly what CI runs)
# ---------------------------------------------------------------------------
ci: lint typecheck test  ## Run full CI checks: lint + typecheck + test

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

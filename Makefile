.DEFAULT_GOAL := help

.PHONY: help install lint lint-fix format typecheck test ci \
        pre-commit-install pre-commit-run

# ---------------------------------------------------------------------------
# Dev setup
# ---------------------------------------------------------------------------
install:  ## Install all dependencies (dev included)
	uv sync --dev

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

typecheck:  ## Run mypy type checker
	uv run mypy services/

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
# CI gate (runs locally exactly what CI runs)
# ---------------------------------------------------------------------------
ci: lint typecheck test  ## Run full CI checks: lint + typecheck + test

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Inferflow MLOps Platform — Backlog

> **Objetivo**: Portfolio project que posiciona como Senior MLOps Engineer.
> **Caso de uso**: Audio → Whisper (STT) → LLM analysis → Embeddings → RAG search
> **Estado actual**: F9 COMPLETE, F10 IN PLANNING
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

---

## Fases Completadas

### FASES 1-8: Plataforma Core Implementada ✅

| Fase | Objetivo | Status |
|---|---|---|
| **F1** | Core Services + API + Workers + Observability | ✅ DONE |
| **F2** | Kubernetes + Helm + GPU Operator | ✅ DONE |
| **F3** | GitOps + ArgoCD + CI/CD Automation | ✅ DONE |
| **F4** | Observability: Prometheus + Grafana + Jaeger | ✅ DONE |
| **F5** | MLOps: MLflow + Canary Deploys + Drift Detection | ✅ DONE |
| **F6** | Terraform IaC: multi-cloud (local/AWS/GCP) | ✅ DONE |
| **F7** | Generic Inference Platform: Step SDK + Pipeline-as-Code + CLI | ✅ DONE |
| **F8** | Branding + Community Setup + Release Automation | ✅ DONE |

**Evidencia**:
- All Phases committed to git with verified CI (120/120 tests, 92.47% coverage)
- Architectural decisions documented in `docs/architecture-benchmark.md`
- Tech stack: FastAPI + Redis Streams + Qdrant + Kubernetes + Helm + ArgoCD + Argo Rollouts + NVIDIA GPU Operator
- Rename to `inferflow-mlops` complete; GitHub community setup (labels, discussions, issue templates) done
- `inferflow` CLI production-ready (Typer + Rich); deployment automation codified

**Archivos clave F1-F8**:
- `services/api-gateway/`, `services/worker/`: Core runtime
- `services/step-sdk/`: BaseStep class + V2 Inference Protocol
- `steps/`, `pipelines/`, `tasks/`: Content / Pipeline-as-Code / Task contracts
- `infra/helm/`, `infra/terraform/`: Infrastructure-as-Code
- `.github/workflows/ci.yml`, `.github/workflows/release.yml`: Automation
- `tools/inferflow-cli/`: Developer experience CLI

---

### FASE 9 — Engineering Audit, IA-Quality Gate & Usability First ✅ (2026-05-15)

> **Objetivo**: cerrar el proyecto con una validación técnica seria, garantizar que la implementación está alineada con buenas prácticas reales del ecosistema y dejar un repositorio extremadamente fácil de usar para cualquier persona nueva.

- [x] **F9-1** Engineering Audit → `docs/engineering-audit.md` (5 hallazgos, 4 resueltos)
- [x] **F9-2** Architecture Benchmark → `docs/architecture-benchmark.md` (vs KServe, Seldon, Ray Serve, FastAPI, ArgoCD, Helm)
- [x] **F9-3** Code Cleanup → Legacy fallback removed, ruff TC003 fixed, 8/8 CLI smoke tests
- [x] **F9-4** Repository Structure → `docs/repo-structure.md` (taxonomy clara para contribuidores)
- [x] **F9-5** Quickstart → `docs/quickstart.md` (6 pasos validados en clean environment, <5 min)
- [x] **F9-6** CLI UX → 8/8 smoke tests passing (help, discovery, validation, errors)
- [x] **F9-7** Quality Gate → `docs/final-quality-gate.md` (CI verde, docs completas, hallazgos resueltos)
- [x] **F9-README** → README updated with CLI command groups + F9 doc links

**Metrics**: 120/120 tests, 92.47% coverage, 0 Trivy CRITICAL, all code changes verified.

---

## FASE 10 — Monorepo → Multi-Repo + Organization Launch 🚀

> **Objetivo**: convertir el monorepo `inferflow-mlops` en una organización GitHub `inferflow-labs` con tres repos enfocados y mantenibles de forma independiente. Cada repo tiene su propio ciclo de versioning, CI/CD y comunidad de contribuidores.

### Arquitectura target de F10

```
inferflow-labs/   ← GitHub organization
├── inferflow-core          # Runtime de la plataforma (API gateway + workers + shared libs)
├── inferflow-steps         # Catálogo de steps (todas las implementaciones de tareas)
├── inferflow-cli           # CLI tool para desarrolladores
└── inferflow-docs          # Documentación + sitio público (auto-deployed)
```

**Razones del split**:
| Repo | Antes (monorepo) | Ahora (multi) | Beneficio |
|---|---|---|---|
| **inferflow-core** | `services/`, `infra/` | Standalone | Runtime versionable independientemente; cambios en deploy no afectan CLI |
| **inferflow-steps** | `steps/`, `tasks/` | Standalone | Community puede contribuir steps sin tocar plataforma core; semantic versioning por step |
| **inferflow-cli** | `tools/inferflow-cli/` | Standalone | Instalable vía `uv tool install inferflow-cli`; releases independientes; UI desacoplada de runtime |
| **inferflow-docs** | `docs/`, `README.md` | Standalone + auto-deployed | Documentación pública; Netlify / Vercel auto-deploy en cada commit; versioning por release |

**Impacto en desarrollo**:
- New contributor → puede aportar un step en `inferflow-steps` sin clonar 20GB de infra
- Bug en runtime → merge rápido a `inferflow-core`, release v1.2.3, CLI automáticamente descubre versión nueva
- Nuevo paso AI (e.g. speech-emotion-recognition) → PR en `inferflow-steps`, sin bloqueos de cambios en Helm
- Documentación desactualizada → contribuidores pueden arreglarla sin hacer CI de servicios

### FASE 10 — Tareas

- [ ] **F10-1** Crear organización GitHub `inferflow-labs` y permisos base
  - Crear org en GitHub (Settings → New Organization → `inferflow-labs`)
  - Crear equipo `@inferflow-labs/maintainers` con permisos admin
  - Documentar seguridad: no secrets en env vars; usar OIDC para GHCR push

- [ ] **F10-2** Preparar `inferflow-core` repo (split de `services/` + `infra/`)
  - Crear nuevo repo: `inferflow-labs/inferflow-core`
  - Copiar: `services/`, `services/shared/`, `services/step-sdk/`, `infra/`
  - Copiar: `.github/workflows/` (sin CLI tests), `Makefile`, `pyproject.toml`, `README.md`
  - Crear: `version.txt` ("1.0.0"), `CHANGELOG.md`
  - Validar: `make ci` pasa en nuevo repo
  - Branch protection: `main` requiere PR review + CI green

- [ ] **F10-3** Preparar `inferflow-steps` repo (split de `steps/` + `tasks/`)
  - Crear nuevo repo: `inferflow-labs/inferflow-steps`
  - Copiar: `steps/`, `tasks/`, `Makefile`, `README.md`
  - Crear: `.github/workflows/step-ci.yml` con matrix dinámico por step changed
  - Crear: `pyproject.toml` con `inferflow-core` como git dep + CONTRIBUTING.md
  - Crear: `version.txt`, `CHANGELOG.md`
  - GitHub issue template: "Report a step"

- [ ] **F10-4** Preparar `inferflow-cli` repo (split de `tools/inferflow-cli/`)
  - Crear nuevo repo: `inferflow-labs/inferflow-cli`
  - Copiar: `inferflow_cli/`, `tests/`, `pyproject.toml`, `setup.py`
  - Crear: `.github/workflows/ci.yml` (lint, mypy, pytest, build dist)
  - Crear: `version.txt`, `CHANGELOG.md`, `README.md`
  - Config: `inferflow = "inferflow_cli.main:app"` como entry point
  - NO incluir `inferflow-core` en deps (CLI es stateless, habla HTTP)

- [ ] **F10-5** Preparar `inferflow-docs` repo (docs públicas con auto-deploy)
  - Crear nuevo repo: `inferflow-labs/inferflow-docs`
  - Copiar: `docs/` (architecture.md, quickstart.md, repo-structure.md, engineering-audit.md, etc)
  - Crear: `mkdocs.yml` (material theme, search, analytics)
  - Crear: `.github/workflows/deploy.yml` (build MkDocs → gh-pages)
  - Crear: `requirements.txt` (mkdocs, mkdocs-material, plugins)
  - Setup Pages: Settings → Pages → Deploy from GitHub Actions
  - URL pública: `https://inferflow-labs.github.io/`

- [ ] **F10-6** Migración de contenido: actualizar referencias cruzadas
  - `inferflow-core/pyproject.toml`: trae `inferflow-step-sdk` de local o git
  - `inferflow-steps/pyproject.toml`: trae `inferflow-step-sdk` desde `inferflow-core`
  - `inferflow-cli/pyproject.toml`: sin `inferflow-core` (comunicación HTTP)
  - README de cada repo apunta a los otros
  - `inferflow-docs/docs/index.md`: enlaza a los tres repos + badges CI
  - Mantener este BACKLOG en uno de los repos o en `/inferflow-labs/.github/`

- [ ] **F10-7** Configurar GitHub Actions compartidas (reutilizables)
  - Crear repo: `inferflow-labs/.github/` (privado)
  - Workflows reutilizables:
    - `.github/workflows/ci-python.yml`: lint + mypy + pytest (coverage > 80%)
    - `.github/workflows/docker-build.yml`: buildx + Trivy + push GHCR
  - Cada repo referencia: `uses: inferflow-labs/.github/workflows/ci-python.yml@main`

- [ ] **F10-8** Release workflow multi-repo
  - **inferflow-core**: `release-please` v1.0.0
    - GHCR: `ghcr.io/inferflow-labs/api-gateway:v1.0.0`
    - Helm chart: `inferflow:v1.0.0`
  - **inferflow-steps**: `release-please` per-step (v1.0.0, v2.1.0, etc.)
    - Config: `release-please-config.json` con `"components"`
    - GHCR: `ghcr.io/inferflow-labs/step-stt-whisper:v1.0.0`
  - **inferflow-cli**: `release-please` semver único
    - `uv tool install git+https://github.com/inferflow-labs/inferflow-cli@v1.0.0`

- [ ] **F10-9** Configurar security + compliance
  - **CODEOWNERS** en cada repo (API experts, ML engineers, UX/DevExp)
  - **Branch protection**: main requiere PR review + CI green
  - **Dependabot**: activo en todos con auto-merge de patch updates
  - **Secret scanning**: GitHub secret scanner activo
  - Documentar en `SECURITY.md` de cada repo

- [ ] **F10-10** Crear monorepo agregador (opcional)
  - Repo: `inferflow-labs/inferflow` con git submodules
  - Estructura: `.gitmodules`, `Makefile` (meta-targets), `README.md`
  - Permite: `git clone --recurse-submodules` para local dev convenience

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
| Documentación pública accesible | https://inferflow-labs.github.io/ |

---

## Decisiones técnicas registradas

Ver `docs/architecture-benchmark.md` para matriz completa de decisiones vs referentes públicos.

---

## Próximos pasos recomendados

**Inmediato** (post-F9):
1. Merge `develop` → `main` (confirmar todas las pruebas pasan)
2. Crear release v1.0.0 vía `release-please` (genera tag + GitHub Release)
3. Compartir el repositorio con portfolio/networking

**Después de F10** (multi-repo):
1. Crear organización `inferflow-labs` en GitHub
2. Split del monorepo en 4 repos según F10 tasks
3. Configurar Actions compartidas y releases automáticas
4. Publicar documentación en `https://inferflow-labs.github.io/`
5. Anunciar cambios a la comunidad early (si existe)

**Futuro** (más allá de F10):
- Phase 11: Community contributions framework (más steps, más pipelines)
- Phase 12: Performance benchmarking vs otros frameworks (KServe, Seldon, Ray Serve)
- Phase 13: Enterprise features (multi-tenancy, RBAC, audit logging)

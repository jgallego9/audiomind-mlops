# MoiraWeave MLOps Platform — Backlog

> **Objetivo**: Portfolio project que posiciona como Senior MLOps Engineer.
> **Caso de uso**: Audio → Whisper (STT) → LLM analysis → Embeddings → RAG search
> **Estado actual**: F9 COMPLETE, F0 IN PLANNING (BLOCKER), F10 IN PLANNING
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
- Rename to `moiraweave-mlops` complete; GitHub community setup (labels, discussions, issue templates) done
- `moiraweave` CLI production-ready (Typer + Rich); deployment automation codified

**Archivos clave F1-F8**:
- `services/api-gateway/`, `services/worker/`: Core runtime
- `services/step-sdk/`: BaseStep class + V2 Inference Protocol
- `steps/`, `pipelines/`, `tasks/`: Content / Pipeline-as-Code / Task contracts
- `infra/helm/`, `infra/terraform/`: Infrastructure-as-Code
- `.github/workflows/ci.yml`, `.github/workflows/release.yml`: Automation
- `tools/moiraweave-cli/`: Developer experience CLI

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

> **Objetivo**: convertir el monorepo `moiraweave-mlops` en una organización GitHub `moiraweave-labs` con repos enfocados y mantenibles de forma independiente. Cada repo tiene su propio ciclo de versioning, CI/CD y comunidad de contribuidores.

> **Prerequisito**: FASE 0 completada (rebrand base aplicado en naming, CLI, docs y artefactos).

**Etiquetas de ejecución**:
- `[MANUAL-GITHUB]`: requiere operación manual en GitHub (UI/org settings/branch protection/pages).
- `[REPO-LOCAL]`: se puede ejecutar desde este entorno editando código/config del repo.

### Arquitectura target de F10

```
moiraweave-labs/   ← GitHub organization
├── moiraweave-core          # Runtime de la plataforma (API gateway + workers + shared libs)
├── moiraweave-steps         # Catálogo de steps (todas las implementaciones de tareas)
├── moiraweave-cli           # CLI tool para desarrolladores
└── moiraweave-docs          # Documentación + sitio público (auto-deployed)
```

**Razones del split**:
| Repo | Antes (monorepo) | Ahora (multi) | Beneficio |
|---|---|---|---|
| **moiraweave-core** | `services/`, `infra/` | Standalone | Runtime versionable independientemente; cambios en deploy no afectan CLI |
| **moiraweave-steps** | `steps/`, `tasks/` | Standalone | Community puede contribuir steps sin tocar plataforma core; semantic versioning por step |
| **moiraweave-cli** | `tools/moira-cli/` | Standalone | Instalable vía `uv tool install moiraweave-cli`; releases independientes; UI desacoplada de runtime |
| **moiraweave-docs** | `docs/`, `README.md` | Standalone + auto-deployed | Documentación pública; Netlify / Vercel auto-deploy en cada commit; versioning por release |

**Impacto en desarrollo**:
- New contributor → puede aportar un step en `moiraweave-steps` sin clonar 20GB de infra
- Bug en runtime → merge rápido a `moiraweave-core`, release v1.2.3, CLI automáticamente descubre versión nueva
- Nuevo paso AI (e.g. speech-emotion-recognition) → PR en `moiraweave-steps`, sin bloqueos de cambios en Helm
- Documentación desactualizada → contribuidores pueden arreglarla sin hacer CI de servicios

### FASE 10 — Tareas

- [ ] **F10-1** `[MANUAL-GITHUB]` Crear organización GitHub `moiraweave-labs` y permisos base
  - Crear org en GitHub (Settings → New Organization → `moiraweave-labs`)
  - Crear equipo `@moiraweave-labs/maintainers` con permisos admin
  - Documentar seguridad: no secrets en env vars; usar OIDC para GHCR push

- [ ] **F10-2** `[MANUAL-GITHUB + REPO-LOCAL]` Preparar `moiraweave-core` repo (split de `services/` + `infra/`)
  - Crear nuevo repo: `moiraweave-labs/moiraweave-core` `[MANUAL-GITHUB]`
  - Copiar: `services/`, `services/shared/`, `services/step-sdk/`, `infra/`
  - Copiar: `.github/workflows/` (sin CLI tests), `Makefile`, `pyproject.toml`, `README.md`
  - Crear: `version.txt` ("1.0.0"), `CHANGELOG.md`
  - Validar: `make ci` pasa en nuevo repo
  - Branch protection: `main` requiere PR review + CI green `[MANUAL-GITHUB]`

- [ ] **F10-3** `[MANUAL-GITHUB + REPO-LOCAL]` Preparar `moiraweave-steps` repo (split de `steps/` + `tasks/`)
  - Crear nuevo repo: `moiraweave-labs/moiraweave-steps` `[MANUAL-GITHUB]`
  - Copiar: `steps/`, `tasks/`, `Makefile`, `README.md`
  - Crear: `.github/workflows/step-ci.yml` con matrix dinámico por step changed
  - Crear: `pyproject.toml` con `moiraweave-core` como git dep + CONTRIBUTING.md
  - Crear: `version.txt`, `CHANGELOG.md`
  - GitHub issue template: "Report a step" `[MANUAL-GITHUB]`

- [ ] **F10-4** `[MANUAL-GITHUB + REPO-LOCAL]` Preparar `moiraweave-cli` repo (split de `tools/moira-cli/`)
  - Crear nuevo repo: `moiraweave-labs/moiraweave-cli` `[MANUAL-GITHUB]`
  - Copiar: `moira_cli/`, `tests/`, `pyproject.toml`, `setup.py`
  - Crear: `.github/workflows/ci.yml` (lint, mypy, pytest, build dist)
  - Crear: `version.txt`, `CHANGELOG.md`, `README.md`
  - Config: `moira = "moira_cli.main:app"` como entry point principal
  - NO incluir `moiraweave-core` en deps (CLI es stateless, habla HTTP)

- [ ] **F10-5** `[MANUAL-GITHUB + REPO-LOCAL]` Preparar `moiraweave-docs` repo (docs públicas con auto-deploy)
  - Crear nuevo repo: `moiraweave-labs/moiraweave-docs` `[MANUAL-GITHUB]`
  - Copiar: `docs/` (architecture.md, quickstart.md, repo-structure.md, engineering-audit.md, etc)
  - Crear: `mkdocs.yml` (material theme, search, analytics)
  - Crear: `.github/workflows/deploy.yml` (build MkDocs → gh-pages)
  - Crear: `requirements.txt` (mkdocs, mkdocs-material, plugins)
  - Setup Pages: Settings → Pages → Deploy from GitHub Actions `[MANUAL-GITHUB]`
  - URL pública: `https://moiraweave-labs.github.io/`

- [ ] **F10-6** `[REPO-LOCAL]` Migración de contenido: actualizar referencias cruzadas
  - `moiraweave-core/pyproject.toml`: trae `moiraweave-step-sdk` de local o git
  - `moiraweave-steps/pyproject.toml`: trae `moiraweave-step-sdk` desde `moiraweave-core`
  - `moiraweave-cli/pyproject.toml`: sin `moiraweave-core` (comunicación HTTP)
  - README de cada repo apunta a los otros
  - `moiraweave-docs/docs/index.md`: enlaza a los tres repos + badges CI
  - Mantener este BACKLOG en uno de los repos o en `/moiraweave-labs/.github/`

- [ ] **F10-7** `[MANUAL-GITHUB + REPO-LOCAL]` Configurar GitHub Actions compartidas (reutilizables)
  - Crear repo: `moiraweave-labs/.github/` (privado) `[MANUAL-GITHUB]`
  - Workflows reutilizables:
    - `.github/workflows/ci-python.yml`: lint + mypy + pytest (coverage > 80%)
    - `.github/workflows/docker-build.yml`: buildx + Trivy + push GHCR
  - Cada repo referencia: `uses: moiraweave-labs/.github/workflows/ci-python.yml@main`

- [ ] **F10-8** `[REPO-LOCAL + MANUAL-GITHUB]` Release workflow multi-repo
  - **moiraweave-core**: `release-please` v1.0.0
    - GHCR: `ghcr.io/moiraweave-labs/api-gateway:v1.0.0`
    - Helm chart: `moiraweave:v1.0.0`
  - **moiraweave-steps**: `release-please` per-step (v1.0.0, v2.1.0, etc.)
    - Config: `release-please-config.json` con `"components"`
    - GHCR: `ghcr.io/moiraweave-labs/step-stt-whisper:v1.0.0`
  - **moiraweave-cli**: `release-please` semver único
    - `uv tool install git+https://github.com/moiraweave-labs/moiraweave-cli@v1.0.0`
  - Crear GitHub Environments y rulesets de release `[MANUAL-GITHUB]`

- [ ] **F10-9** `[MANUAL-GITHUB + REPO-LOCAL]` Configurar security + compliance
  - **CODEOWNERS** en cada repo (API experts, ML engineers, UX/DevExp)
  - **Branch protection**: main requiere PR review + CI green `[MANUAL-GITHUB]`
  - **Dependabot**: activo en todos con auto-merge de patch updates `[MANUAL-GITHUB]`
  - **Secret scanning**: GitHub secret scanner activo `[MANUAL-GITHUB]`
  - Documentar en `SECURITY.md` de cada repo

- [ ] **F10-10** `[MANUAL-GITHUB + REPO-LOCAL]` Crear monorepo agregador (opcional)
  - Repo: `moiraweave-labs/moiraweave` con git submodules `[MANUAL-GITHUB]`
  - Estructura: `.gitmodules`, `Makefile` (meta-targets), `README.md`
  - Permite: `git clone --recurse-submodules` para local dev convenience

---

## FASE 0 — Rebrand MoiraWeave + Refactor Inicial de Referencias 🎨

> **Objetivo**: sustituir completamente el naming `moiraweave` por `MoiraWeave` y `moira` en todo el proyecto.

> **Prioridad**: bloqueante y previa a cualquier split multi-repo (ejecutar antes de F10).
>
> **Decisión de DX**: el comando CLI oficial será `moira` (corto) y único.

- [x] **F0-1** `[REPO-LOCAL]` Definir policy de naming final
  - Canonical brand: `MoiraWeave`
  - Slug técnico: `moiraweave`
  - Reemplazo total: no mantener aliases legacy
  - Documento de migration final (`moiraweave` → `moiraweave` / `moira`) en README principal

- [x] **F0-2** `[REPO-LOCAL]` Refactor de CLI y packaging
  - Renombrar comando principal de `moiraweave` a `moira`
  - Eliminar aliases legacy (`moiraweave`, `moiraweave`) del entrypoint público (solo `moira`)
  - Actualizar `pyproject.toml`, entry points y smoke tests

- [x] **F0-3** `[REPO-LOCAL]` Refactor de documentación interna
  - Sustituir referencias de marca en README, docs y ejemplos de comandos
  - Actualizar nombres de repos target en diagramas y snippets
  - Verificar consistencia de badges, URLs y textos de onboarding

- [x] **F0-4** `[REPO-LOCAL]` Refactor de CI/CD e imágenes
  - Actualizar nombres de imagen GHCR (`ghcr.io/moiraweave-labs/*`)
  - Actualizar Helm chart name, release metadata y artefactos
  - Ajustar release-please para nuevos componentes

- [ ] **F0-5** `[MANUAL-GITHUB]` Operaciones de GitHub fuera del entorno
  - Crear/ajustar org y repos definitivos con naming MoiraWeave
  - Configurar redirects (si aplica) y actualizar descripción de repos
  - Revisar branch protections, rulesets, secrets, environments y Pages

- [ ] **F0-6** `[REPO-LOCAL + MANUAL-GITHUB]` Fase de transición y comunicación
  - Changelog: sección "Rebrand to MoiraWeave"
  - Nota de migración: reemplazo total de comandos (`moiraweave` -> `moira`)
  - Issue/Discussion pública con corte definitivo de naming legacy

- [ ] **F0-7** `[REPO-LOCAL]` Creación de identidad visual (logo + guidelines)
  - Diseñar logo v1 (símbolo + wordmark) alineado con metáfora "tejer el destino"
  - Definir paleta, tipografías y usos mínimos (README/docs/social)
  - Exportables: SVG oscuro/claro, favicon, avatar org

- [ ] **F0-8** `[MANUAL-GITHUB]` Aplicar branding en GitHub
  - Actualizar avatar y descripción de la organización
  - Actualizar social preview y README profile de la org
  - Revisar naming en topics, labels y plantillas de issue/PR

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
| Documentación pública accesible | https://moiraweave-labs.github.io/ |

---

## Decisiones técnicas registradas

Ver `docs/architecture-benchmark.md` para matriz completa de decisiones vs referentes públicos.

---

## Próximos pasos recomendados

**Inmediato** (post-F9):
1. Ejecutar FASE 0 completa (rebrand MoiraWeave + reemplazo total de naming)
2. Merge `develop` → `main` (confirmar todas las pruebas pasan)
3. Crear release v1.0.0 vía `release-please` (genera tag + GitHub Release)

**Después de F0 + F10** (multi-repo):
1. Crear organización `moiraweave-labs` en GitHub
2. Split del monorepo en 4 repos según F10 tasks
3. Configurar Actions compartidas y releases automáticas
4. Publicar documentación en `https://moiraweave-labs.github.io/`
5. Anunciar cambios a la comunidad early (si existe)

**Futuro** (más allá de F10):
- Phase 11: Community contributions framework (más steps, más pipelines)
- Phase 12: Performance benchmarking vs otros frameworks (KServe, Seldon, Ray Serve)
- Phase 13: Enterprise features (multi-tenancy, RBAC, audit logging)

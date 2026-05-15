# Architecture Benchmark (Phase 9)

Date: 2026-05-15

## Decision Matrix

| Area | Current Approach | Public Reference | Gap | Action |
| --- | --- | --- | --- | --- |
| Step contract | KServe-style tensor I/O and metadata endpoints in step services | KServe V2 Inference Protocol: https://kserve.github.io/website/modelserving/data_plane/v2_protocol/ | Naming and endpoint set mostly aligned; full conformance tests not explicit | Add protocol-level contract tests for request/response validation |
| Pipeline composition | YAML pipeline declarations plus runtime router | Seldon Core 2 inference graphs: https://docs.seldon.ai/seldon-core-2 | Graph semantics present; lifecycle constraints and retries less explicit | Document retry/backoff and failure semantics per step |
| Multi-model serving abstraction | Step-based modular runtime with per-step deployability | Ray Serve composition patterns: https://docs.ray.io/en/latest/serve/ | Equivalent modularity, but fewer production guidance docs in-repo | Add deployment guidance for scale and rollout scenarios |
| API runtime | FastAPI gateway with auth, readiness, job lifecycle | FastAPI deployment docs: https://fastapi.tiangolo.com/deployment/ | Operational baseline good; onboarding docs were fragmented | Centralize first-run path in quickstart |
| GitOps | ArgoCD + app-of-apps + environment sync modes | ArgoCD docs: https://argo-cd.readthedocs.io/ | Good pattern adoption; needs stricter runbook linking | Add troubleshooting runbook pointers in README/quickstart |
| Progressive delivery | Argo Rollouts canary analysis | Argo Rollouts docs: https://argo-rollouts.readthedocs.io/ | Strategy present; success criteria can be clearer per environment | Add explicit canary acceptance thresholds table |
| Packaging/deployment | Helm chart-driven deployment and env overlays | Helm chart best practices: https://helm.sh/docs/chart_best_practices/ | Structure mostly aligned; naming migration recently completed | Keep chart naming stable and remove legacy aliases |

## Adoption Verdict

- Adopted: KServe-style contracts, ArgoCD, Argo Rollouts, Helm packaging.
- Adapted: pipeline router and job model to fit async Redis-based runtime.
- Deferred: strict protocol conformance suite and explicit CLI compatibility mode switch.

## Priority Follow-ups

1. Add conformance tests for step I/O protocol.
2. Document retry/failure semantics in pipeline execution.
3. Add canary thresholds and rollback criteria in one operational table.

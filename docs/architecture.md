# Architecture

Inferflow MLOps is organized in three layers:

1. Step layer
- Reusable KServe V2 steps in `steps/<task>-<impl>/`.
- Each step declares task contract, version, and input/output tensors.

2. Pipeline layer
- Declarative definitions in `pipelines/<name>/pipeline.yaml`.
- Steps are composed by task compatibility.

3. Runtime layer
- API gateway and worker services.
- Redis streams for async orchestration.
- Qdrant for vector indexing/search.
- Helm chart for per-step scaling on Kubernetes.

See [architecture diagram](assets/architecture.svg).

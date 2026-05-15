# Adding a Pipeline

## 1. Create the pipeline file

Create `pipelines/<name>/pipeline.yaml` with step IDs, tasks, and URLs.

## 2. Validate contracts

Run:

```bash
inferflow pipeline validate <name>
```

This checks required input/output compatibility between adjacent steps.

## 3. Enable in Helm values

Add `.Values.pipelines.<name>` in `infra/helm/inferflow/values.yaml`.

No template changes are required in `infra/helm/inferflow/templates/steps/`.

# GitHub Manual Operations (F8)

This document centralizes all operations that must be executed manually in GitHub.
No local helper script is required.

## 1) Rename repository

1. Open repository settings for `jgallego9/inferflow-mlops`.
2. Rename to `inferflow-mlops`.
3. Keep default branch unchanged (`main`) unless intentionally changed.

## 2) Repository description and topics

Set description:

- `A production-ready, pipeline-as-code ML inference platform. Define your AI pipeline in YAML, deploy with one command, scale each step independently.`

Set topics:

- `mlops`
- `inference`
- `pipeline-as-code`
- `kubernetes`
- `helm`
- `argocd`
- `fastapi`
- `redis-streams`
- `vllm`
- `python`
- `docker`
- `gitops`
- `rag`
- `llm`

## 3) Labels

Create or update the following labels:

| Name | Color | Description |
| --- | --- | --- |
| bug | d73a4a | Something is broken |
| enhancement | a2eeef | New feature or request |
| new-step | 5319e7 | Proposal or work for a new step |
| new-pipeline | 0e8a16 | Proposal or work for a new pipeline |
| documentation | 0075ca | Documentation improvements |
| good first issue | 7057ff | Good for first-time contributors |
| help wanted | 008672 | Extra attention is needed |
| breaking-change | b60205 | Introduces backward-incompatible behavior |
| performance | fbca04 | Performance-related optimization or regression |

## 4) GitHub Discussions

1. Enable Discussions in repository settings.
2. Create categories:
   - Q&A
   - Ideas
   - Show and Tell

## 5) Project board (Kanban)

Create a project board linked to repository issues/PRs with columns:

- Backlog
- In Progress
- In Review
- Done

## 6) Verify workflows and permissions

Confirm that these workflows are enabled on default branch:

- `.github/workflows/ci.yml`
- `.github/workflows/step-ci.yml`
- `.github/workflows/release.yml`

Confirm `GITHUB_TOKEN` has permissions required by each workflow.

## 7) Release and package checks

1. Ensure tags of format `vX.Y.Z` trigger CI build/push path.
2. Ensure Release Please can open/update release PRs on `main`.
3. Ensure GHCR package namespace aligns with `ghcr.io/jgallego9/inferflow-*`.

## 8) Post-rename validation checklist

1. README badges resolve after rename.
2. Discussion and project links resolve.
3. Package links in GHCR are visible and write permissions are correct.
4. PR and issue templates render correctly in GitHub UI.
5. Security policy appears under Security tab.

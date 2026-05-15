#!/usr/bin/env bash
set -euo pipefail

# Repository hygiene bootstrap helper.
# Requires gh CLI auth with repo admin permissions.

REPO="${1:-jgallego9/audiomind-mlops}"

TOPICS=(
  mlops
  inference
  pipeline-as-code
  kubernetes
  helm
  argocd
  fastapi
  redis-streams
  vllm
  python
  docker
  gitops
  rag
  llm
)

echo "Setting repository description and homepage for $REPO"
gh repo edit "$REPO" \
  --description "A production-ready, pipeline-as-code ML inference platform. Define your AI pipeline in YAML, deploy with one command, scale each step independently." \
  --homepage "https://github.com/${REPO}"

echo "Syncing topics"
for topic in "${TOPICS[@]}"; do
  gh repo edit "$REPO" --add-topic "$topic"
done

echo "Enabling Discussions (requires admin permissions)"
gh api --method PATCH "repos/${REPO}" -f has_discussions=true >/dev/null

echo "Syncing labels"
"$(dirname "$0")/setup-labels.sh" "$REPO"

echo "Done."
echo "Next manual step: create or link a GitHub Project board (Backlog/In Progress/In Review/Done)."

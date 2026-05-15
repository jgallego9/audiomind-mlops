#!/usr/bin/env bash
set -euo pipefail

# Creates or updates repository labels used by the project workflow.
# Requires: gh CLI authenticated against the target repository.

REPO="${1:-jgallego9/audiomind-mlops}"

create_or_update_label() {
  local name="$1"
  local color="$2"
  local description="$3"

  if gh label list --repo "$REPO" --limit 200 | awk '{print $1}' | grep -Fxq "$name"; then
    gh label edit "$name" --repo "$REPO" --color "$color" --description "$description"
    echo "updated: $name"
  else
    gh label create "$name" --repo "$REPO" --color "$color" --description "$description"
    echo "created: $name"
  fi
}

create_or_update_label "bug" "d73a4a" "Something is broken"
create_or_update_label "enhancement" "a2eeef" "New feature or request"
create_or_update_label "new-step" "5319e7" "Proposal or work for a new step"
create_or_update_label "new-pipeline" "0e8a16" "Proposal or work for a new pipeline"
create_or_update_label "documentation" "0075ca" "Documentation improvements"
create_or_update_label "good first issue" "7057ff" "Good for first-time contributors"
create_or_update_label "help wanted" "008672" "Extra attention is needed"
create_or_update_label "breaking-change" "b60205" "Introduces backward-incompatible behavior"
create_or_update_label "performance" "fbca04" "Performance-related optimization or regression"

echo "Done. Labels synced for $REPO"

#!/bin/bash
# Create Booty labels for dogfooding. Run from repo root.
# Requires: gh (GitHub CLI) authenticated
set -e
cd "$(dirname "$0")/.."
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
create() {
  gh api "repos/${REPO}/labels" -X POST -f name="$1" -f description="$2" -f color="$3" >/dev/null 2>/dev/null || true
}
create "agent" "Triggers Booty Planner→Builder pipeline" "0366d6"
create "agent:architect-review" "Architect review required" "0366d6"
create "self-modification" "PR modifies Booty itself" "d93f0b"
echo "Labels created (or already exist)."

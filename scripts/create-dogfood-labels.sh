#!/bin/bash
# Create Booty labels for dogfooding. Run from repo root.
# Requires: gh (GitHub CLI) authenticated
set -e
cd "$(dirname "$0")/.."
gh label create "agent" --description "Triggers Booty Planner→Builder pipeline" --color "0366d6" 2>/dev/null || true
gh label create "agent:architect-review" --description "Architect review required" --color "0366d6" 2>/dev/null || true
gh label create "self-modification" --description "PR modifies Booty itself" --color "d93f0b" 2>/dev/null || true
echo "Labels created (or already exist)."

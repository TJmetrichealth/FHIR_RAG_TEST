#!/usr/bin/env bash
# Run this once from the repo root to commit the W1 post-fix artefacts and apply the week1-complete tag.
# Do NOT push (not authorised). The tag is local only.
set -euo pipefail

# Stage the four post-fix files that were either newly created or modified after the planner's
# provisional gate entry, plus the updated plan and decisions log.
git add Makefile
git add scripts/freeze_dataset.py
git add data/freeze.json
git add questions/questions.jsonl
git add docs/00_PROJECT_PLAN.md
git add docs/decisions.md

# Also stage any fidelity_reports_templated that exist (new untracked directory)
git add narratives/fidelity_reports_templated/ 2>/dev/null || true

# Commit using the project's short-phrase convention
git commit -m "week 1 post-fix: templated fidelity audit, questions.jsonl, freeze hardening, plan/decisions updated"

# Apply the annotated tag at the resulting HEAD
git tag -a week1-complete \
  -m "Week 1 complete; gate PASS per reviewer 2026-04-21; dataset-freeze-v1 intact; overall_sha256=0fb54a35ca5dcb2a"

echo "Done. Tag week1-complete applied at $(git rev-parse HEAD)."
echo "To verify: git show week1-complete --no-patch"

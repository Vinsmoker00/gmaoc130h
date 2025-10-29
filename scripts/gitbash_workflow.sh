#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -d .venv ]; then
  python -m venv .venv
fi

source .venv/bin/activate

if ! pip install -r requirements.txt; then
  echo "Warning: Failed to install dependencies (likely due to offline environment)." >&2
fi

git status

current_branch="$(git rev-parse --abbrev-ref HEAD)"
remotes="$(git remote)"
if [ -n "$remotes" ]; then
  if echo "$remotes" | grep -Fxq "origin"; then
    git pull --rebase origin "$current_branch"
  else
    first_remote="$(echo "$remotes" | head -n1)"
    git pull --rebase "$first_remote" "$current_branch"
  fi
else
  echo "No git remote configured; skipping pull." >&2
fi

if ! python -m flask --app gmao seed-demo; then
  echo "Warning: Flask command failed. Ensure dependencies are installed and environment variables are set." >&2
fi

echo "Repository update workflow finished."

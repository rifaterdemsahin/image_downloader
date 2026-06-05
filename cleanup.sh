#!/usr/bin/env bash
# Deletes all downloaded image folders. Safe to re-run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

folders=("downloads" "output" "outputs")

for folder in "${folders[@]}"; do
  path="$ROOT/$folder"
  if [[ -d "$path" ]]; then
    echo "Removing: $path"
    rm -rf "$path"
  fi
done

echo "Done."

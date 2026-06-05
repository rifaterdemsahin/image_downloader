#!/usr/bin/env bash
# Deletes all downloaded image folders and lists every file removed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

folders=("downloads" "output" "outputs")
total_files=0

for folder in "${folders[@]}"; do
  path="$ROOT/$folder"
  if [[ -d "$path" ]]; then
    echo "── $path"
    # list every file inside before deleting
    while IFS= read -r -d '' file; do
      echo "   deleted: $file"
      total_files=$((total_files + 1))
    done < <(find "$path" -type f -print0)
    rm -rf "$path"
  fi
done

if [[ $total_files -eq 0 ]]; then
  echo "Nothing to delete."
else
  echo ""
  echo "Done. $total_files file(s) deleted."
fi

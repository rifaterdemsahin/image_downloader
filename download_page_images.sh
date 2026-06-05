#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./download_page_images.sh <page_url> [output_directory]

Examples:
  ./download_page_images.sh "https://example.com"
  ./download_page_images.sh "https://example.com/gallery" "images"
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 1
fi

PAGE_URL="$1"
BASE_DIR="${2:-output}"

# Derive a safe folder name from the URL: strip scheme, replace non-alphanumeric with _
URL_FOLDER="$(python3 -c "
import sys, re
from urllib.parse import urlparse
p = urlparse(sys.argv[1])
raw = p.netloc + p.path
raw = raw.strip('/')
folder = re.sub(r'[^A-Za-z0-9._-]', '_', raw)
folder = re.sub(r'_+', '_', folder).strip('_')
print(folder or 'images')
" "$PAGE_URL")"

OUT_DIR="$BASE_DIR/$URL_FOLDER"

mkdir -p "$OUT_DIR"

TMP_HTML="$(mktemp)"
TMP_URLS="$(mktemp)"

cleanup() {
  rm -f "$TMP_HTML" "$TMP_URLS"
}
trap cleanup EXIT

echo "Fetching page: $PAGE_URL"
curl -fsSL "$PAGE_URL" -o "$TMP_HTML"

python3 - "$PAGE_URL" "$TMP_HTML" > "$TMP_URLS" <<'PY'
import sys
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

base_url = sys.argv[1]
html_path = sys.argv[2]

class ImgParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "img":
            return
        attrs = dict(attrs)

        candidates = []
        src = attrs.get("src")
        if src:
            candidates.append(src)

        srcset = attrs.get("srcset")
        if srcset:
            for item in srcset.split(","):
                first = item.strip().split()[0] if item.strip() else ""
                if first:
                    candidates.append(first)

        for raw in candidates:
            raw = raw.strip()
            if not raw or raw.startswith("data:"):
                continue
            absolute = urljoin(base_url, raw)
            parsed = urlparse(absolute)
            if parsed.scheme in ("http", "https"):
                self.urls.append(absolute)

with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
    html = f.read()

parser = ImgParser()
parser.feed(html)

seen = set()
for u in parser.urls:
    if u not in seen:
        seen.add(u)
        print(u)
PY

TOTAL="$(wc -l < "$TMP_URLS" | tr -d '[:space:]')"

if [[ "$TOTAL" == "0" ]]; then
  echo "No images found on page."
  exit 0
fi

echo "Found $TOTAL image URL(s). Downloading to: $OUT_DIR"

index=0
while IFS= read -r IMG_URL; do
  [[ -z "$IMG_URL" ]] && continue
  index=$((index + 1))

  FILE_NAME="$(python3 - "$IMG_URL" "$index" <<'PY'
import sys
from urllib.parse import urlparse, unquote
import os
import re

url = sys.argv[1]
index = int(sys.argv[2])

path = urlparse(url).path
name = os.path.basename(path)
name = unquote(name).strip()

if not name:
    name = f"image_{index}.jpg"

name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
if not name or name.startswith("."):
    name = f"image_{index}.jpg"

print(name)
PY
)"

  DEST="$OUT_DIR/$FILE_NAME"
  if [[ -e "$DEST" ]]; then
    base="${FILE_NAME%.*}"
    ext="${FILE_NAME##*.}"
    if [[ "$base" == "$ext" ]]; then
      ext=""
    else
      ext=".$ext"
    fi

    n=1
    while [[ -e "$OUT_DIR/${base}_$n$ext" ]]; do
      n=$((n + 1))
    done
    DEST="$OUT_DIR/${base}_$n$ext"
  fi

  if curl -fsSL "$IMG_URL" -o "$DEST"; then
    echo "[$index/$TOTAL] Downloaded: $DEST"
  else
    rm -f "$DEST"
    echo "[$index/$TOTAL] Failed: $IMG_URL" >&2
  fi
done < "$TMP_URLS"

echo "Done."

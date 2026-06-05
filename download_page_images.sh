#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./download_page_images.sh <page_url> [output_directory]

Examples:
  ./download_page_images.sh "https://example.com"
  ./download_page_images.sh "https://example.com/gallery" "images"

Crawls 2 levels deep (main page → linked pages → their linked pages).
Up to 5 internal links are followed per level.
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

TMP_URLS="$(mktemp)"

cleanup() {
  rm -f "$TMP_URLS"
}
trap cleanup EXIT

echo "Crawling 2 levels deep from: $PAGE_URL"

python3 - "$PAGE_URL" > "$TMP_URLS" <<'PY'
import sys
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen, Request
from urllib.error import URLError

MAX_LINKS_PER_LEVEL = 5
CRAWL_DEPTH = 2

def fetch(url):
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; image-downloader/1.0)"})
        with urlopen(req, timeout=10) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [skip] {url}: {e}", file=sys.stderr)
        return ""

class PageParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        self.images = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        tag = tag.lower()

        if tag == "img":
            for attr in ("src", "data-src", "data-lazy-src"):
                src = attrs.get(attr)
                if src:
                    self._add_image(src)
            srcset = attrs.get("srcset", "")
            if srcset:
                for item in srcset.split(","):
                    first = item.strip().split()[0] if item.strip() else ""
                    if first:
                        self._add_image(first)

        elif tag == "a":
            href = attrs.get("href", "")
            if href:
                absolute = urljoin(self.base_url, href)
                p = urlparse(absolute)
                if p.scheme in ("http", "https") and p.netloc == self.base_domain:
                    clean = p._replace(fragment="").geturl()
                    self.links.append(clean)

    def _add_image(self, raw):
        raw = raw.strip()
        if not raw or raw.startswith("data:"):
            return
        absolute = urljoin(self.base_url, raw)
        p = urlparse(absolute)
        if p.scheme in ("http", "https"):
            self.images.append(absolute)


base_url = sys.argv[1]
visited_pages = set()
image_seen = set()

def crawl(url, depth):
    if url in visited_pages:
        return []
    visited_pages.add(url)
    indent = "  " * (CRAWL_DEPTH - depth)
    print(f"{indent}[depth {CRAWL_DEPTH - depth}] Scanning: {url}", file=sys.stderr)

    html = fetch(url)
    if not html:
        return []

    parser = PageParser(url)
    parser.feed(html)

    images = parser.images
    if depth > 0:
        for link in parser.links[:MAX_LINKS_PER_LEVEL]:
            images += crawl(link, depth - 1)
    return images

for img in crawl(base_url, depth=CRAWL_DEPTH):
    if img not in image_seen:
        image_seen.add(img)
        print(img)
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

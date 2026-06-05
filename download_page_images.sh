#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./download_page_images.sh <page_url> [output_directory]

Examples:
  ./download_page_images.sh "https://www.bbc.com"
  ./download_page_images.sh "https://example.com/gallery" "images"

BFS-crawls pages (no fixed depth) until more than 10 images over 200 KB
have been downloaded. Stops at 100 pages as a safety cap.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage; exit 0
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage; exit 1
fi

PAGE_URL="$1"
BASE_DIR="${2:-output}"

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

python3 - "$PAGE_URL" "$OUT_DIR" <<'PY'
import sys, os, re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, unquote
from urllib.request import urlopen, Request
from collections import deque

TARGET    = 10          # stop once this many large images are found
THRESHOLD = 200 * 1024  # 200 KB
MAX_PAGES = 100         # safety cap

def fetch_html(url):
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [skip page] {e}", file=sys.stderr)
        return ""

def download_image(url, dest):
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=15) as r:
            data = r.read()
        with open(dest, "wb") as f:
            f.write(data)
        return len(data)
    except Exception as e:
        print(f"  [skip img] {e}", file=sys.stderr)
        if os.path.exists(dest):
            os.remove(dest)
        return -1

def safe_name(url, index):
    name = unquote(os.path.basename(urlparse(url).path)).strip()
    if not name:
        name = f"image_{index}.bin"
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name if name and not name.startswith(".") else f"image_{index}.bin"

def unique_dest(out_dir, name):
    dest = os.path.join(out_dir, name)
    if not os.path.exists(dest):
        return dest
    base, _, ext = name.rpartition(".")
    base, ext = (name, "") if not base else (base, "." + ext)
    n = 1
    while os.path.exists(os.path.join(out_dir, f"{base}_{n}{ext}")):
        n += 1
    return os.path.join(out_dir, f"{base}_{n}{ext}")

class PageParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.domain   = urlparse(base_url).netloc
        self.images   = []
        self.links    = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        tag   = tag.lower()
        if tag == "img":
            for attr in ("src", "data-src", "data-lazy-src"):
                if attrs.get(attr):
                    self._add_img(attrs[attr])
            for item in (attrs.get("srcset") or "").split(","):
                first = item.strip().split()[0] if item.strip() else ""
                if first:
                    self._add_img(first)
        elif tag == "a":
            href = attrs.get("href", "")
            if href:
                abs_url = urljoin(self.base_url, href)
                p = urlparse(abs_url)
                if p.scheme in ("http", "https") and p.netloc == self.domain:
                    self.links.append(p._replace(fragment="").geturl())

    def _add_img(self, raw):
        raw = raw.strip()
        if not raw or raw.startswith("data:"):
            return
        abs_url = urljoin(self.base_url, raw)
        if urlparse(abs_url).scheme in ("http", "https"):
            self.images.append(abs_url)

# ── main ──────────────────────────────────────────────────────────────────────
start_url, out_dir = sys.argv[1], sys.argv[2]

queue         = deque([start_url])
visited_pages = set()
seen_images   = set()
img_index     = 0
large_count   = 0
pages_scanned = 0

print(f"Crawling: {start_url}")
print(f"Goal: >{TARGET} images over {THRESHOLD//1024} KB  |  page cap: {MAX_PAGES}\n")

while queue and pages_scanned < MAX_PAGES:
    url = queue.popleft()
    if url in visited_pages:
        continue
    visited_pages.add(url)
    pages_scanned += 1
    print(f"[page {pages_scanned}/{MAX_PAGES}] {url}")

    html = fetch_html(url)
    if not html:
        continue

    parser = PageParser(url)
    parser.feed(html)

    for img_url in parser.images:
        if img_url in seen_images:
            continue
        seen_images.add(img_url)
        img_index += 1

        dest = unique_dest(out_dir, safe_name(img_url, img_index))
        size = download_image(img_url, dest)
        if size < 0:
            continue

        kb = size // 1024
        if size > THRESHOLD:
            large_count += 1
            print(f"  [{img_index}] {os.path.basename(dest)}  {kb} KB  *** large #{large_count}/{TARGET}")
            if large_count > TARGET:
                print(f"\nGoal reached: {large_count} images over {THRESHOLD//1024} KB. Done.")
                sys.exit(0)
        else:
            print(f"  [{img_index}] {os.path.basename(dest)}  {kb} KB")

    for link in parser.links:
        if link not in visited_pages:
            queue.append(link)

print(f"\nScanned {pages_scanned} pages. Found {large_count} large image(s) — goal not fully reached.")
PY

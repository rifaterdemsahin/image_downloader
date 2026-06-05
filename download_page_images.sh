#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./download_page_images.sh [--num N] <page_url> [output_directory]

Options:
  --num N   Stop after N large images (>200 KB) are downloaded (default: 10)

Examples:
  ./download_page_images.sh "https://www.bbc.com"
  ./download_page_images.sh --num 20 "https://www.bbc.com"
  ./download_page_images.sh "https://example.com/gallery" "images"

BFS-crawls pages (no fixed depth) until more than N images over 200 KB
have been downloaded. Stops at 100 pages as a safety cap.
Generates gallery.html in the output folder and opens it in the browser.
EOF
}

NUM_TARGET=10
PAGE_URL=""
BASE_DIR="downloads"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --num|-n)
      [[ $# -lt 2 ]] && { echo "Error: --num requires a value"; usage; exit 1; }
      NUM_TARGET="$2"; shift 2 ;;
    -*)
      echo "Unknown option: $1"; usage; exit 1 ;;
    *)
      if [[ -z "$PAGE_URL" ]]; then PAGE_URL="$1"
      elif [[ "$BASE_DIR" == "downloads" ]]; then BASE_DIR="$1"
      else echo "Too many arguments"; usage; exit 1
      fi
      shift ;;
  esac
done

if [[ -z "$PAGE_URL" ]]; then
  usage; exit 1
fi

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

python3 - "$PAGE_URL" "$OUT_DIR" "$NUM_TARGET" <<'PY'
import sys, os, re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, unquote
from urllib.request import urlopen, Request
from collections import deque
from datetime import datetime

TARGET    = int(sys.argv[3]) if len(sys.argv) > 3 else 10
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

def write_gallery(out_dir, source_url, entries):
    abs_path = os.path.abspath(out_dir)
    items_html = "\n".join(
        f'    <div class="item" data-kb="{kb}">\n'
        f'      <img src="{name}" alt="{name}" loading="lazy">\n'
        f'      <p>{name} &nbsp;·&nbsp; {kb} KB'
        + (' &nbsp;·&nbsp; <span class="large">★ large</span>' if large else '')
        + '</p>\n    </div>'
        for name, kb, large in entries
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gallery — {source_url}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ height: 100%; }}
    body {{
      background: #0d0d0d;
      color: #ccc;
      font-family: system-ui, sans-serif;
      font-size: 13px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    header {{
      flex-shrink: 0;
      background: #111;
      border-bottom: 1px solid #222;
      padding: 10px 16px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
    }}
    .header-url {{
      flex: 1;
      min-width: 0;
    }}
    .header-url a {{ color: #5af; text-decoration: none; word-break: break-all; }}
    .header-meta {{ color: #555; font-size: 11px; white-space: nowrap; }}
    .filters {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }}
    .filters button {{
      background: #1e1e1e;
      border: 1px solid #333;
      color: #aaa;
      padding: 4px 12px;
      border-radius: 20px;
      cursor: pointer;
      font-size: 12px;
      transition: background 0.15s, color 0.15s, border-color 0.15s;
    }}
    .filters button:hover {{
      background: #2a2a2a;
      color: #fff;
    }}
    .filters button.active {{
      background: #1a4a8a;
      border-color: #5af;
      color: #fff;
    }}
    #count {{
      color: #555;
      font-size: 11px;
      white-space: nowrap;
    }}
    .gallery {{
      flex: 1;
      min-height: 0;
      overflow-y: scroll;
      scroll-snap-type: y mandatory;
    }}
    .item {{
      height: 100%;
      flex-shrink: 0;
      scroll-snap-align: start;
      display: flex;
      flex-direction: column;
      border-bottom: 1px solid #1a1a1a;
    }}
    .item.hidden {{ display: none; }}
    :root {{ --zoom: 1; }}
    .item img {{
      flex: 1;
      min-height: 0;
      width: 100%;
      object-fit: contain;
      display: block;
      background: #0d0d0d;
      transform: scale(var(--zoom));
      transform-origin: center center;
      transition: transform .15s;
    }}
    .item p {{
      flex-shrink: 0;
      padding: 6px 10px;
      color: #666;
      font-size: 11px;
      background: #111;
    }}
    .large {{ color: #f90; font-weight: bold; }}
    .zoom-ctrl {{ display: flex; align-items: center; gap: 6px; }}
    .zoom-ctrl label {{ color: #999; font-size: 11px; }}
    .zoom-ctrl input[type=range] {{ width: 90px; cursor: pointer; accent-color: #5af; }}
    #zoom-val {{ color: #999; font-size: 11px; min-width: 34px; }}
    #del-btn {{ background: #1a0505; border: 1px solid #5a1a1a; color: #f66; padding: 4px 12px; border-radius: 20px; cursor: pointer; font-size: 12px; white-space: nowrap; }}
    #del-btn:hover {{ background: #5a1a1a; color: #fff; }}
  </style>
</head>
<body>
  <header>
    <div class="header-url">
      <a href="{source_url}" target="_blank">{source_url}</a>
      <span class="header-meta">&nbsp;·&nbsp; generated {datetime.now().strftime("%Y-%m-%d %H:%M")}</span>
    </div>
    <div class="filters">
      <button class="active" data-min="0">All</button>
      <button data-min="10">10 KB+</button>
      <button data-min="100">100 KB+</button>
      <button data-min="200">200 KB+</button>
      <button data-min="300">300 KB+</button>
      <button data-min="500">500 KB+</button>
    </div>
    <span id="count"></span>
    <div class="zoom-ctrl">
      <label for="zoom">Zoom</label>
      <input type="range" id="zoom" min="10" max="100" value="100">
      <span id="zoom-val">100%</span>
    </div>
    <button id="del-btn" onclick="deleteFolder()">Delete folder</button>
  </header>
  <div class="gallery">
{items_html}
  </div>
  <script>
    const items = Array.from(document.querySelectorAll('.item'));
    const countEl = document.getElementById('count');

    function applyFilter(minKb) {{
      let visible = 0;
      items.forEach(el => {{
        const kb = parseInt(el.dataset.kb, 10);
        const show = kb >= minKb;
        el.classList.toggle('hidden', !show);
        if (show) visible++;
      }});
      countEl.textContent = visible + ' / {len(entries)} images';
    }}

    document.querySelectorAll('.filters button').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        applyFilter(parseInt(btn.dataset.min, 10));
      }});
    }});

    applyFilter(0);

    document.getElementById('zoom').addEventListener('input', function() {{
      document.documentElement.style.setProperty('--zoom', this.value / 100);
      document.getElementById('zoom-val').textContent = this.value + '%';
    }});

    const folderPath = "{abs_path}";
    async function deleteFolder() {{
      if (!confirm('Permanently delete this folder?\\n\\n' + folderPath)) return;
      const btn = document.getElementById('del-btn');
      btn.textContent = 'Deleting...';
      btn.disabled = true;
      try {{
        await fetch('/delete');
        document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;background:#0d0d0d;color:#f66;font-family:system-ui;text-align:center"><div><p style="font-size:1.5rem;margin-bottom:.5rem">Folder deleted</p><p style="color:#555;font-size:.85rem">' + folderPath + '</p></div></div>';
      }} catch(e) {{
        btn.textContent = 'Delete folder';
        btn.disabled = false;
        alert('Delete failed. Is the server still running?');
      }}
    }}
  </script>
</body>
</html>"""
    path = os.path.join(out_dir, "gallery.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path

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
downloaded    = []   # (filename, kb, is_large)

print(f"Crawling: {start_url}", file=sys.stderr)
print(f"Goal: >{TARGET} images over {THRESHOLD//1024} KB  |  page cap: {MAX_PAGES}\n", file=sys.stderr)

while queue and pages_scanned < MAX_PAGES:
    url = queue.popleft()
    if url in visited_pages:
        continue
    visited_pages.add(url)
    pages_scanned += 1
    print(f"[page {pages_scanned}/{MAX_PAGES}] {url}", file=sys.stderr)

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

        kb    = size // 1024
        large = size > THRESHOLD
        downloaded.append((os.path.basename(dest), kb, large))

        if large:
            large_count += 1
            print(f"  [{img_index}] {os.path.basename(dest)}  {kb} KB  *** large #{large_count}/{TARGET}", file=sys.stderr)
            if large_count > TARGET:
                print(f"\nGoal reached: {large_count} images over {THRESHOLD//1024} KB.", file=sys.stderr)
                break
        else:
            print(f"  [{img_index}] {os.path.basename(dest)}  {kb} KB", file=sys.stderr)

    if large_count > TARGET:
        break

    for link in parser.links:
        if link not in visited_pages:
            queue.append(link)

write_gallery(out_dir, start_url, downloaded)
PY

python3 - "$OUT_DIR" <<'SERVE'
import sys, http.server, socketserver, threading, shutil, webbrowser

folder = sys.argv[1]

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=folder, **kwargs)
    def do_GET(self):
        if self.path == '/delete':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'deleted')
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            shutil.rmtree(folder, ignore_errors=True)
        else:
            super().do_GET()
    def log_message(self, *args): pass

with socketserver.TCPServer(('', 0), Handler) as httpd:
    port = httpd.server_address[1]
    url = f'http://localhost:{port}/gallery.html'
    webbrowser.open(url)
    print(f'Gallery: {url}  (Ctrl+C to exit)')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()
SERVE

read -rp $'\nRun cleanup.sh? [y/N] ' _ans
if [[ "${_ans,,}" == "y" ]]; then
  "$(dirname "$0")/cleanup.sh"
fi

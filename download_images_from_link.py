#!/usr/bin/env python3
import argparse
import os
import urllib.request
import urllib.parse
import webbrowser
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

class ImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image_urls = []

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            for name, value in attrs:
                if name == 'src' and value:
                    self.image_urls.append(value)
                # Some sites use data-src or data-original for lazy loading
                if name in ['data-src', 'data-original'] and value:
                    self.image_urls.append(value)

def download_image(url, output_dir):
    try:
        # Create a valid filename from the URL
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename:
            filename = 'image_' + str(abs(hash(url))) + '.jpg'
            
        filepath = os.path.join(output_dir, filename)
        
        # Add headers to avoid 403 Forbidden
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response, open(filepath, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
            
        return True, filename
    except Exception as e:
        return False, str(e)

def serve_gallery(output_dir: Path):
    import http.server, socketserver, threading, shutil

    folder = str(output_dir)

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


def write_gallery(output_dir: Path, title: str, entries: list) -> Path:
    total = len(entries)
    abs_path = str(output_dir.resolve())
    items_html = "\n".join(
        f'    <div class="item" data-kb="{kb}">\n'
        f'      <img src="{name}" alt="{name}" loading="lazy">\n'
        f'      <p>{name} &nbsp;·&nbsp; {kb} KB'
        + (' &nbsp;·&nbsp; <span class="large">★ large</span>' if kb >= 200 else '')
        + '</p>\n    </div>'
        for name, kb in entries
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Gallery — {title}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ height: 100%; }}
    body {{ background: #0d0d0d; color: #ccc; font-family: system-ui, sans-serif; font-size: 13px; display: flex; flex-direction: column; overflow: hidden; }}
    header {{
      flex-shrink: 0; background: #111; border-bottom: 1px solid #222;
      padding: 10px 16px;
      display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
    }}
    .header-title {{ flex: 1; min-width: 0; color: #5af; word-break: break-all; }}
    .header-meta {{ color: #555; font-size: 11px; white-space: nowrap; }}
    .filters {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    .filters button {{
      background: #1e1e1e; border: 1px solid #333; color: #aaa;
      padding: 4px 12px; border-radius: 20px; cursor: pointer; font-size: 12px;
      transition: background .15s, color .15s, border-color .15s;
    }}
    .filters button:hover {{ background: #2a2a2a; color: #fff; }}
    .filters button.active {{ background: #1a4a8a; border-color: #5af; color: #fff; }}
    #count {{ color: #555; font-size: 11px; white-space: nowrap; }}
    .gallery {{ flex: 1; min-height: 0; overflow-y: scroll; scroll-snap-type: y mandatory; }}
    .item {{ height: 100%; flex-shrink: 0; scroll-snap-align: start; display: flex; flex-direction: column; border-bottom: 1px solid #1a1a1a; }}
    .item.hidden {{ display: none; }}
    :root {{ --zoom: 1; }}
    .item img {{ flex: 1; min-height: 0; width: 100%; object-fit: contain; display: block; background: #0d0d0d; transform: scale(var(--zoom)); transform-origin: center center; transition: transform .15s; }}
    .item p {{ flex-shrink: 0; padding: 6px 10px; color: #666; font-size: 11px; background: #111; }}
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
    <div class="header-title">{title}</div>
    <span class="header-meta">generated {datetime.now().strftime("%Y-%m-%d %H:%M")}</span>
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
        const show = parseInt(el.dataset.kb, 10) >= minKb;
        el.classList.toggle('hidden', !show);
        if (show) visible++;
      }});
      countEl.textContent = visible + ' / {total} images';
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
    path = output_dir / "gallery.html"
    path.write_text(html, encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description="Download all images from a given URL.")
    parser.add_argument("url", help="The URL to scrape images from")
    parser.add_argument("--output", "-o", default="downloads", help="Base output directory (default: downloads)")
    args = parser.parse_args()

    from urllib.parse import urlparse as _urlparse
    _p = _urlparse(args.url)
    _folder = re.sub(r"[^A-Za-z0-9._-]", "_", (_p.netloc + _p.path).strip("/")) or "images"
    output_dir = Path(args.output) / _folder
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching link: {args.url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        req = urllib.request.Request(args.url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching URL: {e}")
        return

    parser_obj = ImageParser()
    parser_obj.feed(html)
    
    # Remove duplicates but preserve order
    seen = set()
    img_urls = []
    for url in parser_obj.image_urls:
        if url not in seen:
            seen.add(url)
            img_urls.append(url)
            
    if not img_urls:
        print("No images found on this page.")
        return
        
    print(f"Found {len(img_urls)} unique image tag(s). Resolving URLs and downloading...")
    
    downloaded = 0
    entries = []
    for i, img_src in enumerate(img_urls, 1):
        # Ignore data URIs
        if img_src.startswith('data:'):
            print(f"[{i}/{len(img_urls)}] Skipping data URI...")
            continue

        # Resolve relative URLs
        img_url = urllib.parse.urljoin(args.url, img_src)

        print(f"[{i}/{len(img_urls)}] Downloading {img_url} ...")
        success, result = download_image(img_url, str(output_dir))

        if success:
            size = (output_dir / result).stat().st_size
            print(f"  -> Saved as {result}  ({size:,} bytes)")
            entries.append((result, size // 1024))
            downloaded += 1
        else:
            print(f"  -> Failed: {result}")

    print(f"\nDone. Downloaded {downloaded} out of {len(img_urls)}. Images saved to '{output_dir}'.")
    if entries:
        write_gallery(output_dir, args.url, entries)
        serve_gallery(output_dir)

if __name__ == "__main__":
    main()

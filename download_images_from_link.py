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

def write_gallery(output_dir: Path, title: str, entries: list) -> Path:
    total = len(entries)
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
    body {{ background: #0d0d0d; color: #ccc; font-family: system-ui, sans-serif; font-size: 13px; }}
    header {{
      position: sticky; top: 0; background: #111; border-bottom: 1px solid #222;
      padding: 10px 16px; z-index: 10;
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
    .gallery {{ display: flex; flex-direction: column; gap: 6px; padding: 20px; }}
    .item {{ width: 100%; background: #161616; border: 1px solid #222; border-radius: 4px; overflow: hidden; }}
    .item.hidden {{ display: none; }}
    .item img {{ width: 100%; height: auto; display: block; }}
    .item p {{ padding: 6px 10px; color: #666; font-size: 11px; }}
    .large {{ color: #f90; font-weight: bold; }}
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
  </script>
</body>
</html>"""
    path = output_dir / "gallery.html"
    path.write_text(html, encoding="utf-8")
    webbrowser.open(path.resolve().as_uri())
    print(f"Gallery → {path}")
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

if __name__ == "__main__":
    main()

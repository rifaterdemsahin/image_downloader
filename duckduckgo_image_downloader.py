#!/usr/bin/env python3
"""
DuckDuckGo Image Downloader — no extra dependencies required.
Usage: python duckduckgo_image_downloader.py --query "car gif" --num 10 --output ./images
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path


def download_image(url: str, filepath: str) -> bool:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read()
        if len(data) < 500:
            return False
        with open(filepath, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"  [skip] {e}")
        return False


def get_vqd_token(query: str) -> str:
    """
    DuckDuckGo requires a vqd token from the main search page
    before allowing calls to the images API.
    """
    url = f"https://duckduckgo.com/?q={urllib.parse.quote(query)}&iax=images&ia=images"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        html = response.read().decode("utf-8", errors="ignore")

    # vqd token is embedded as: vqd="4-..."  or  vqd=4-...
    match = re.search(r'vqd=["\']([\d\-a-f]+)["\']', html)
    if not match:
        match = re.search(r'"vqd"\s*:\s*"([\d\-a-f]+)"', html)
    if not match:
        raise RuntimeError("Could not extract vqd token from DuckDuckGo page.")
    return match.group(1)


def fetch_image_urls(query: str, num_images: int, debug: bool = False) -> list[str]:
    vqd = get_vqd_token(query)
    if debug:
        print(f"[debug] vqd token: {vqd}")

    urls: list[str] = []
    params = {
        "l": "us-en",
        "o": "json",
        "q": query,
        "vqd": vqd,
        "f": ",,,,,",
        "p": "1",
    }

    # DuckDuckGo paginates via a 'next' cursor; fetch pages until we have enough
    api_base = "https://duckduckgo.com/i.js"
    next_url = api_base + "?" + urllib.parse.urlencode(params)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://duckduckgo.com/",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
    }

    while next_url and len(urls) < num_images:
        if debug:
            print(f"[debug] Fetching: {next_url[:120]}")

        req = urllib.request.Request(next_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8", errors="ignore"))

        for result in data.get("results", []):
            image_url = result.get("image")
            if image_url:
                urls.append(image_url)
            if len(urls) >= num_images:
                break

        # Follow pagination cursor
        next_cursor = data.get("next")
        if next_cursor:
            next_url = f"https://duckduckgo.com/{next_cursor}"
        else:
            break

    if debug:
        print(f"[debug] Total URLs collected: {len(urls)}")
        for u in urls[:10]:
            print(f"  {u[:100]}")
        print()

    return urls[:num_images]


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
    parser = argparse.ArgumentParser(description="Download images from DuckDuckGo Images")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--num", "-n", type=int, default=10, help="Number of images (default: 10)")
    parser.add_argument("--output", "-o", default="./images", help="Output directory (default: ./images)")
    parser.add_argument("--delay", "-d", type=float, default=0.5, help="Delay between downloads (default: 0.5s)")
    parser.add_argument("--debug", action="store_true", help="Print debug info")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Searching DuckDuckGo Images for: '{args.query}'")
    print(f"Target: {args.num} images → {output_dir}/\n")

    try:
        urls = fetch_image_urls(args.query, args.num, debug=args.debug)
    except Exception as e:
        print(f"Error fetching search results: {e}")
        sys.exit(1)

    if not urls:
        print("No image URLs found. Try --debug to inspect the response.")
        sys.exit(1)

    print(f"Found {len(urls)} image URL(s). Downloading...\n")

    downloaded = 0
    entries = []
    for i, url in enumerate(urls, start=1):
        path_part = url.split("?")[0].lower()
        ext = ".jpg"
        for candidate in [".gif", ".png", ".webp", ".jpeg", ".jpg"]:
            if path_part.endswith(candidate):
                ext = ".jpg" if candidate == ".jpeg" else candidate
                break

        safe_query = re.sub(r"[^\w]", "_", args.query)
        filename = output_dir / f"{safe_query}_{i:03d}{ext}"
        print(f"[{i}/{len(urls)}] {url[:90]}...")
        if download_image(url, str(filename)):
            size = filename.stat().st_size
            print(f"  Saved → {filename}  ({size:,} bytes)")
            entries.append((filename.name, size // 1024))
            downloaded += 1
        time.sleep(args.delay)

    print(f"\nDone. {downloaded}/{len(urls)} images saved to '{output_dir}/'")
    if entries:
        write_gallery(output_dir, f"DuckDuckGo Images: {args.query}", entries)


if __name__ == "__main__":
    main()

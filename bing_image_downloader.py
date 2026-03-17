#!/usr/bin/env python3
"""
Bing Image Downloader — no extra dependencies required.
Usage: python bing_image_downloader.py --query "car gif" --num 10 --output ./images
"""

import argparse
import html as html_module
import json
import time
import urllib.request
import urllib.parse
import re
import sys
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
            return False  # skip tiny/broken responses
        with open(filepath, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"  [skip] {e}")
        return False


def fetch_image_urls(query: str, num_images: int, debug: bool = False) -> list[str]:
    encoded_query = urllib.parse.quote(query)
    # Bing Images search — embeds image metadata as JSON in the page
    search_url = (
        f"https://www.bing.com/images/search"
        f"?q={encoded_query}&count={num_images * 3}&first=1&FORM=HDRSC2"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    req = urllib.request.Request(search_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response:
        raw = response.read().decode("utf-8", errors="ignore")

    # Bing HTML-entity-encodes embedded JSON — unescape it first
    html = html_module.unescape(raw)

    if debug:
        print(f"\n[debug] HTML length: {len(html)} chars")
        # find first murl occurrence
        idx = html.find("murl")
        if idx >= 0:
            print(f"[debug] Context around first 'murl':\n{html[max(0,idx-50):idx+200]}\n")
        else:
            print("[debug] 'murl' not found in page")
            print(f"[debug] First 1000 chars:\n{html[:1000]}\n")

    urls: list[str] = []

    # Strategy 1: "murl":"<url>" in unescaped HTML (Bing's main data format)
    for u in re.findall(r'"murl"\s*:\s*"(https?://[^"]+)"', html):
        # murl is often a Bing proxy; extract rurl= for the original
        if "rurl=" in u:
            rurl = re.search(r'rurl=(https?[^&"]+)', u)
            if rurl:
                urls.append(urllib.parse.unquote(rurl.group(1)))
            else:
                urls.append(u)
        else:
            urls.append(u)

    # Strategy 2: m={"murl":"..."} JSON attribute (unescaped)
    for m_json in re.findall(r'\bm=["\']\{([^"\']{20,})\}["\']', html):
        try:
            data = json.loads("{" + m_json + "}")
            if "murl" in data:
                mu = data["murl"]
                if "rurl=" in mu:
                    rurl = re.search(r'rurl=(https?[^&"]+)', mu)
                    urls.append(urllib.parse.unquote(rurl.group(1)) if rurl else mu)
                else:
                    urls.append(mu)
        except Exception:
            pass

    # Strategy 3: mediaurl= / imgurl= query params
    for raw in re.findall(r'(?:mediaurl|imgurl)=(https?://[^&"]+)', html):
        urls.append(urllib.parse.unquote(raw))

    # Deduplicate, skip Bing thumbnail CDN links
    seen: set[str] = set()
    unique: list[str] = []
    for u in urls:
        u = u.strip()
        if u in seen:
            continue
        if "tse1.mm.bing.net" in u or "th.bing.com" in u:
            continue
        seen.add(u)
        unique.append(u)

    if debug:
        print(f"[debug] Unique candidate URLs found: {len(unique)}")
        for u in unique[:10]:
            print(f"  {u[:100]}")
        print()

    return unique[:num_images]


def main():
    parser = argparse.ArgumentParser(description="Download images from Bing Images")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--num", "-n", type=int, default=10, help="Number of images (default: 10)")
    parser.add_argument("--output", "-o", default="./images", help="Output directory (default: ./images)")
    parser.add_argument("--delay", "-d", type=float, default=0.5, help="Delay between downloads (default: 0.5s)")
    parser.add_argument("--debug", action="store_true", help="Print debug info")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Searching Bing Images for: '{args.query}'")
    print(f"Target: {args.num} images → {output_dir}/\n")

    try:
        urls = fetch_image_urls(args.query, args.num, debug=args.debug)
    except Exception as e:
        print(f"Error fetching search results: {e}")
        sys.exit(1)

    if not urls:
        print("No image URLs found. Try --debug to inspect the page.")
        sys.exit(1)

    print(f"Found {len(urls)} candidate URL(s). Downloading...\n")

    downloaded = 0
    for i, url in enumerate(urls, start=1):
        # Detect extension from URL path (before query string)
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
            downloaded += 1
        time.sleep(args.delay)

    print(f"\nDone. {downloaded}/{len(urls)} images saved to '{output_dir}/'")


if __name__ == "__main__":
    main()

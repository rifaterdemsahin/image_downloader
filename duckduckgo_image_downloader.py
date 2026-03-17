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
            downloaded += 1
        time.sleep(args.delay)

    print(f"\nDone. {downloaded}/{len(urls)} images saved to '{output_dir}/'")


if __name__ == "__main__":
    main()

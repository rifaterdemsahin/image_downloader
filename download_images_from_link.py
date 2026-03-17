#!/usr/bin/env python3
import argparse
import os
import urllib.request
import urllib.parse
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

def main():
    parser = argparse.ArgumentParser(description="Download all images from a given URL.")
    parser.add_argument("url", help="The URL to scrape images from")
    parser.add_argument("--output", "-o", default="./downloaded_images", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
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
            print(f"  -> Saved as {result}")
            downloaded += 1
        else:
            print(f"  -> Failed: {result}")
            
    print(f"\nDone. Downloaded {downloaded} out of {len(img_urls)}. Images saved to '{output_dir}'.")

if __name__ == "__main__":
    main()

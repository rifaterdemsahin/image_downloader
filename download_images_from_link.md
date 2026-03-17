# How `download_images_from_link.py` Works

This script downloads all images from a given web page URL using only standard Python libraries (`urllib` and `html.parser`), eliminating the need to install third-party packages like `requests` or `BeautifulSoup`. 

Here is a step-by-step breakdown of how it works:

## 1. Fetching the Target Web Page
The script begins by making an HTTP Request to the URL you provide. To prevent the server from rejecting the request (a common cause for `403 Forbidden` errors), the script mimics a real web browser by sending a `User-Agent` string (e.g., claiming to be Google Chrome on Windows). 

```python
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
}
req = urllib.request.Request(args.url, headers=headers)
with urllib.request.urlopen(req, timeout=15) as response:
    html = response.read().decode('utf-8', errors='ignore')
```

## 2. Parsing HTML to Find Images
Once it retrieves the raw HTML text, the script feeds it into a custom `ImageParser` class. This class inherits from Python's built-in `HTMLParser`. As the parser reads the HTML piece-by-piece, it watches for the start of `<img>` tags.

When it spots an `<img>` tag, it inspects its attributes:
- `src`: The standard way images load on the web.
- `data-src` / `data-original`: Often used by modern websites to "lazy-load" images only when you scroll them into view.

```python
def handle_starttag(self, tag, attrs):
    if tag == 'img':
        for name, value in attrs:
            if name in ['src', 'data-src', 'data-original'] and value:
                self.image_urls.append(value)
```
Every discovered image link is added to a list.

## 3. Resolving Image URLs
HTML files frequently use relative URLs for images (e.g., `<img src="/images/logo.png">`). Before downloading, the script uses `urllib.parse.urljoin()` to resolve these relative paths against the main target URL, turning them into complete, valid URLs (e.g., `https://example.com/images/logo.png`). 

Data URIs (e.g., `data:image/png;base64,...`), which embed image source code directly into the HTML without an external link, are skipped.

## 4. Downloading and Saving the Images
Finally, the script iterates over the cleaned list of image links, once again providing the browser-like `User-Agent` header.

It extracts the file name from the URL path:
```python
parsed_url = urllib.parse.urlparse(url)
filename = os.path.basename(parsed_url.path)
```
If the URL doesn't have a recognizable file name in the path, the script creates a unique placeholder name using an absolute hash of the URL (`image_1234567.jpg`).

It initiates the connection, reads the binary data (`bytes`), and writes those bits directly into an output file within the specified target directory (`./downloaded_images` by default).

## Usage Overview
```bash
# Standard run
python download_images_from_link.py "https://example.com"

# Specifying a custom output folder
python download_images_from_link.py "https://example.com" -o "./my_website_backup"
```

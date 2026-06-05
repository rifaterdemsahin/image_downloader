# Image Downloader

Four scripts that download images from the web using only the Python / Bash standard library — no pip installs required. Every run produces a `gallery.html` that opens automatically in your browser.

---

## Scripts

| Script | Source | Language |
|---|---|---|
| `download_page_images.sh` | Any web page (BFS crawl) | Bash + Python inline |
| `bing_image_downloader.py` | Bing Images search | Python |
| `duckduckgo_image_downloader.py` | DuckDuckGo Images search | Python |
| `download_images_from_link.py` | Single page scrape | Python |

All scripts are `chmod +x` — run them directly (`./script`) or via their interpreter.

---

## Output layout

Every script writes into `downloads/<subfolder>/` by default:

```
downloads/
  www.bbc.com/          ← download_page_images.sh "https://www.bbc.com"
  bing_cats/            ← bing_image_downloader.py -q "cats"
  ddg_space_nebula/     ← duckduckgo_image_downloader.py -q "space nebula"
  www.example.com/      ← download_images_from_link.py https://www.example.com
```

Downloaded files and gallery HTML are git-ignored. Only `downloads/README.md` is tracked.

---

## Quick start

```bash
# Crawl a page (BFS, stops when >10 images over 200 KB are found)
./download_page_images.sh "https://www.bbc.com"

# Search Bing Images
./bing_image_downloader.py --query "mountain landscape" --num 20

# Search DuckDuckGo Images
./duckduckgo_image_downloader.py --query "space nebula" --num 15

# Scrape all images from a single URL
./download_images_from_link.py https://www.example.com
```

---

## Tactics

### 1. BFS crawling with adaptive depth (`download_page_images.sh`)

Rather than a fixed crawl depth, the script uses breadth-first search and **stops as soon as more than 10 images over 200 KB have been downloaded**. This finds high-resolution images on inner article pages without crawling the entire site.

- Starts at the seed URL and enqueues all internal links (same domain only)
- Processes pages one by one in BFS order
- Downloads each image immediately and checks its byte size
- Stops the crawl once the size threshold is met
- Hard cap of 100 pages to prevent runaway crawls

### 2. srcset full-resolution extraction

HTML `<img>` tags often contain a `srcset` attribute listing the same image at multiple resolutions. The parser reads every candidate URL from `srcset` and downloads them all, so the largest available variant is captured rather than just the low-res `src` thumbnail.

```html
<!-- srcset gives us the 800w and 1600w versions, not just the 320w src -->
<img src="thumb.jpg" srcset="med.jpg 800w, full.jpg 1600w">
```

### 3. Lazy-load attribute handling

Modern sites defer image loading using non-standard attributes. The parser checks `src`, `data-src`, and `data-lazy-src` on every `<img>` tag so images that haven't loaded yet in the browser are still captured.

### 4. URL-to-folder naming

Each run creates a deduplicated subfolder inside `downloads/` derived from the source:

- Pages / links → `netloc + path`, non-alphanumeric chars replaced with `_`
- Bing searches → `bing_<safe_query>`
- DuckDuckGo searches → `ddg_<safe_query>`

This means re-running the same query overwrites the previous results cleanly.

### 5. Bing HTML scraping (`bing_image_downloader.py`)

Bing embeds image metadata as HTML-entity-encoded JSON inside the search results page. The script:

1. Fetches `bing.com/images/search` with a browser User-Agent
2. HTML-unescapes the page to decode the entity encoding
3. Extracts `"murl":"..."` fields (the original image URL) via regex
4. Unwraps Bing proxy URLs by reading the `rurl=` query parameter to get the real source
5. Falls back to `mediaurl=` / `imgurl=` patterns as a secondary strategy

### 6. DuckDuckGo vqd token + JSON API (`duckduckgo_image_downloader.py`)

DuckDuckGo gates its image API behind a session token (`vqd`) that must be obtained first:

1. Fetches the DDG search page and extracts the `vqd` token via regex
2. Calls `duckduckgo.com/i.js` (JSON API) with the token
3. Paginates using the `next` cursor field until enough images are collected
4. Downloads from the original `image` URL in each result object

### 7. Gallery HTML with size filters

After every download run a `gallery.html` is written into the subfolder and opened automatically in the browser. Features:

- **Dark UI**, full-viewport-width images in a single vertical scroll
- **Sticky header** with source URL/query, image count, and timestamp
- **Filter buttons** — All / 10 KB+ / 100 KB+ / 200 KB+ / 300 KB+ / 500 KB+ — client-side JS, no reload
- **`★ large` badge** on images over 200 KB
- **Lazy loading** (`loading="lazy"`) so the page opens instantly even with hundreds of images

### 8. Collision-safe filenames

If two image URLs resolve to the same filename, successive files get a numeric suffix (`image_1.jpg`, `image_2.jpg`, …) so no download overwrites another.

### 9. Git hygiene

```
downloads/**          ← all downloaded content ignored
!downloads/README.md  ← only the README is tracked
*.html                ← generated galleries never committed
*.jpg / *.png / …     ← image formats blocked globally
```

---

## Requirements

- Python 3.10+
- `bash` + `curl` (for `download_page_images.sh`)
- No external dependencies

---

## Options reference

### `download_page_images.sh`

```
./download_page_images.sh <url> [base_dir]
```

### `bing_image_downloader.py` / `duckduckgo_image_downloader.py`

| Flag | Short | Default | Description |
|---|---|---|---|
| `--query` | `-q` | *(required)* | Search term |
| `--num` | `-n` | `10` | Number of images |
| `--output` | `-o` | `downloads` | Base output directory |
| `--delay` | `-d` | `0.5` | Seconds between downloads |
| `--debug` | | off | Print parsing / API debug info |

### `download_images_from_link.py`

| Flag | Short | Default | Description |
|---|---|---|---|
| `url` | | *(required)* | Page URL to scrape |
| `--output` | `-o` | `downloads` | Base output directory |

---

## Troubleshooting

**No image URLs found** — run with `--debug` to inspect what the page returned.

**vqd token error (DDG)** — DuckDuckGo changed its page structure; run `--debug` and check `get_vqd_token()`.

**Many skipped downloads** — increase the delay: `--delay 2.0`.

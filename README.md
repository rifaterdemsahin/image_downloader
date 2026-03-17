# Image Downloaders

Download images from Bing or DuckDuckGo using only Python standard library — no pip installs required.

---

## Files

| File | Source |
|------|--------|
| `bing_image_downloader.py` | Bing Images |
| `duckduckgo_image_downloader.py` | DuckDuckGo Images |

---

## Requirements

- Python 3.10+
- No external dependencies

---

## Bing Image Downloader

### Usage

```bash
python bing_image_downloader.py --query "car gif" --num 10 --output ./images
```

### How It Works

1. Sends a request to `bing.com/images/search` with a browser User-Agent
2. HTML-unescapes the page to decode Bing's entity-encoded JSON
3. Extracts image URLs from `"murl":"..."` fields in the embedded JSON
4. Strips Bing proxy wrappers by reading the `rurl=` parameter to get the original source URL
5. Downloads each image with a configurable delay

### Options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--query` | `-q` | *(required)* | Search term |
| `--num` | `-n` | `10` | Number of images |
| `--output` | `-o` | `./images` | Output folder |
| `--delay` | `-d` | `0.5` | Seconds between downloads |
| `--debug` | | off | Print page parsing info |

### Examples

```bash
# Download 10 car GIFs
python bing_image_downloader.py --query "car gif" --num 10 --output ./test_images

# Download 20 landscapes with a slower rate
python bing_image_downloader.py --query "mountain landscape" --num 20 --delay 1.5

# Debug mode — shows what URLs were found
python bing_image_downloader.py --query "cats" --num 5 --debug
```

---

## DuckDuckGo Image Downloader

### Usage

```bash
python duckduckgo_image_downloader.py --query "car gif" --num 10 --output ./images
```

### How It Works

1. Fetches the DuckDuckGo search page to extract a required `vqd` session token
2. Calls the DuckDuckGo images JSON API (`duckduckgo.com/i.js`) using that token
3. Paginates through results until the requested number of images is reached
4. Downloads each image directly from the original source URL

### Options

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--query` | `-q` | *(required)* | Search term |
| `--num` | `-n` | `10` | Number of images |
| `--output` | `-o` | `./images` | Output folder |
| `--delay` | `-d` | `0.5` | Seconds between downloads |
| `--debug` | | off | Print token and API responses |

### Examples

```bash
# Download 10 car GIFs
python duckduckgo_image_downloader.py --query "car gif" --num 10 --output ./test_images

# Download 30 images with pagination
python duckduckgo_image_downloader.py --query "space nebula" --num 30 --output ./space

# Debug mode — shows vqd token and API responses
python duckduckgo_image_downloader.py --query "cats" --num 5 --debug
```

---

## Output

Files are named:

```
<output_dir>/<query_with_underscores>_001.gif
<output_dir>/<query_with_underscores>_002.jpg
...
```

Extension is detected from the URL path (`.gif`, `.png`, `.webp`, `.jpg`).

---

## Comparison

| | Bing | DuckDuckGo |
|---|---|---|
| Approach | Scrapes HTML page | Calls JSON API |
| Token required | No | Yes (vqd, auto-fetched) |
| Pagination | Single page | Multi-page cursor |
| Result quality | Good | Good |
| Rate limiting | Moderate | Moderate |

---

## Troubleshooting

**No image URLs found**

Run with `--debug` to inspect what was returned:
```bash
python bing_image_downloader.py --query "cats" --num 5 --debug
python duckduckgo_image_downloader.py --query "cats" --num 5 --debug
```

**Could not extract vqd token** (DuckDuckGo only)

DuckDuckGo changed its page structure. Run with `--debug` and check the token extraction logic in `get_vqd_token()`.

**Many skipped downloads**

Increase the delay:
```bash
python bing_image_downloader.py --query "cats" --num 10 --delay 2.0
```

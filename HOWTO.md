# How to Run

## Setup (once)

```bash
git clone https://github.com/rifaterdemsahin/image_downloader.git
cd image_downloader
chmod +x *.sh *.py
```

---

## 1 — Download images from any web page (BFS crawler)

```bash
./download_page_images.sh "https://www.bbc.com"
```

Crawls the page and its internal links until it finds **>10 images over 200 KB**.  
Images → `downloads/www.bbc.com/`  
Gallery opens automatically in your browser at `http://localhost:<port>/gallery.html`

```bash
# Custom output folder
./download_page_images.sh "https://www.bbc.com" my_folder
```

---

## 2 — Download images from Bing search

```bash
./bing_image_downloader.py --query "mountain landscape" --num 20
```

Images → `downloads/bing_mountain_landscape/`

```bash
# More options
./bing_image_downloader.py -q "cats" -n 50 --delay 1.0 --debug
```

| Flag | Short | Default | Description |
|---|---|---|---|
| `--query` | `-q` | required | Search term |
| `--num` | `-n` | 10 | Number of images |
| `--output` | `-o` | `downloads` | Base output folder |
| `--delay` | `-d` | 0.5 s | Delay between downloads |
| `--debug` | | off | Show parsing details |

---

## 3 — Download images from DuckDuckGo search

```bash
./duckduckgo_image_downloader.py --query "space nebula" --num 15
```

Images → `downloads/ddg_space_nebula/`

```bash
# More options
./duckduckgo_image_downloader.py -q "cats" -n 30 --delay 1.0 --debug
```

Same flags as Bing above.

---

## 4 — Download all images from a single URL

```bash
./download_images_from_link.py https://www.example.com
```

Images → `downloads/www.example.com/`

```bash
# Custom output folder
./download_images_from_link.py https://www.example.com --output my_folder
```

---

## Gallery controls (in the browser)

| Control | What it does |
|---|---|
| **All / 10 KB+ / 100 KB+ …** | Filter images by file size |
| **Zoom slider** | Scale images smaller (10 – 100%) |
| **Scroll down** | Jump to the next image (snaps per screen) |
| **Delete folder** | Permanently deletes the folder — no undo |

---

## 5 — Clean up everything

```bash
./cleanup.sh
```

Deletes `downloads/`, `output/`, and `outputs/` folders.

---

## Requirements

- Python 3.10+
- `bash` + `curl` (for `download_page_images.sh`)
- No pip installs needed

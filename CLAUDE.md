# CLAUDE.md

## Project

Four image-downloader scripts (Bash + Python stdlib only). Each script downloads images and generates a `gallery.html` in the output subfolder, then opens it in the browser.

## Scripts

| File | What it does |
|---|---|
| `download_page_images.sh` | BFS-crawls a URL until >10 images over 200 KB are found |
| `bing_image_downloader.py` | Scrapes Bing Images search results |
| `duckduckgo_image_downloader.py` | Calls DuckDuckGo image JSON API |
| `download_images_from_link.py` | Scrapes all `<img>` tags from a single page |

## Output

All downloads go into `downloads/<subfolder>/`. The folder is git-ignored; only `downloads/README.md` is tracked. Generated `gallery.html` files are also git-ignored via `*.html`.

```
downloads/www.bbc.com/          ← download_page_images.sh
downloads/bing_<query>/         ← bing_image_downloader.py
downloads/ddg_<query>/          ← duckduckgo_image_downloader.py
downloads/<domain+path>/        ← download_images_from_link.py
```

## Key design decisions

- **No pip dependencies** — everything uses Python stdlib (`urllib`, `html.parser`, `json`, `re`, `pathlib`, `webbrowser`) and bash builtins + `curl`.
- **BFS + size threshold** — `download_page_images.sh` stops crawling once >10 images over 200 KB are downloaded rather than using a fixed depth. Safety cap: 100 pages.
- **srcset parsing** — extracts all candidates from `srcset` to get full-resolution variants, not just the `src` thumbnail.
- **Lazy-load attrs** — checks `data-src` and `data-lazy-src` in addition to `src`.
- **gallery.html** — written into every output subfolder after each run; same dark UI, sticky filter bar, full-width images. Auto-opens via `webbrowser.open()` / `open` (macOS).
- **Filter buttons** — All / 10 / 100 / 200 / 300 / 500 KB+ — client-side JS, no server needed.

## Testing

```bash
# BFS page crawler
./download_page_images.sh "https://www.bbc.com"

# Bing search
./bing_image_downloader.py --query "cats" --num 5 --debug

# DuckDuckGo search
./duckduckgo_image_downloader.py --query "cats" --num 5 --debug

# Single page
./download_images_from_link.py https://www.example.com
```

## Conventions

- All scripts are `chmod +x`
- Default base dir is `downloads/` for all scripts (pass `--output` to override)
- Filenames are collision-safe: duplicates get `_1`, `_2` suffixes
- Image formats (`*.jpg`, `*.png`, etc.) and `*.html` are globally git-ignored

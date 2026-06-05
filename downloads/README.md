# downloads

All downloaded images land here, organised into subfolders by source:

| Subfolder pattern | Script |
|---|---|
| `downloads/www.bbc.com/` | `download_page_images.sh` (URL-based) |
| `downloads/bing_<query>/` | `bing_image_downloader.py` |
| `downloads/ddg_<query>/` | `duckduckgo_image_downloader.py` |
| `downloads/<domain+path>/` | `download_images_from_link.py` |

This folder is git-ignored — downloaded files are never committed. Only this README is tracked.

Each subfolder also contains a `gallery.html` that opens automatically in your browser after a run.

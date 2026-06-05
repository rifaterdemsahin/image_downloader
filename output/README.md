# output

Downloaded images land here when you run `download_page_images.sh`.

This folder is git-ignored (see `.gitignore`) so downloaded files are never committed. Only this README is tracked.

## Usage

```bash
./download_page_images.sh <page_url> [output_directory]

# defaults to ./output/<url-derived-folder>/
./download_page_images.sh "https://www.bbc.com"
# saves to: output/www.bbc.com/
```

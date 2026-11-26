# Product Image-Link Scraper

Collects every product's **image links** from an online store into **one master CSV**,
with the product name, colour and sizes, and the **total product count** at the end.
No images are downloaded.

| S.No | Product Name | Color | Size | Image No | Image Link |
|---|---|---|---|---|---|
| 1 | Super Combed Cotton Solid Brief … - Assorted (Pack of 3) | Assorted | 3-4 Yrs, 5-6 Yrs, 7-8 Yrs, 9-10 Yrs, 11-12 Yrs | 1 | https://cdn.shopify.com/…_5.webp |
|   |   |   |   | 2 | https://cdn.shopify.com/…_1.webp |
|   |   |   |   | 3 | https://cdn.shopify.com/…_2.webp |
| 2 | Microfiber … Round Neck T-Shirt - Cosmic Sapphire | Cosmic Sapphire | S, M, L, XL, XXL | 1 | https://cdn.shopify.com/…_1.webp |
|   |   |   |   | 2 | https://cdn.shopify.com/…_2.webp |
|   |   |   |   |   |   |
| **Total Products** | **2** |   |   |   |   |

- One row per image link. S.No, name, colour and size appear **once**, on the product's first row.
- **Total Products** counts each product once, however many images it has.
- Saved as `<csv folder>\<site>_products.csv`, e.g. `csv\jockey.in_products.csv`.
  With `--collection men` it's `jockey.in_men_products.csv`.
- UTF-8 with BOM, so Excel opens it with ₹ and other special characters intact.

---

## Run it

### First time only (setup)
Requires **Python 3.10+** ([python.org](https://www.python.org/downloads/); tick *"Add Python to PATH"*).
```powershell
git clone <this repo's URL> scrapper
cd scrapper
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```
Or just double-click **`run.bat`** (Windows), which does the setup automatically.
On macOS/Linux use `python3 -m venv .venv` and `.venv/bin/python` instead of `.\.venv\Scripts\python`.

### Every time
```powershell
cd scrapper
```
Quick test (first 5 products):
```powershell
.\.venv\Scripts\python scraper.py --site jockey --max-products 5
```
**Entire site:**
```powershell
.\.venv\Scripts\python scraper.py --site jockey --no-prompt
```
Any other site by URL:
```powershell
.\.venv\Scripts\python scraper.py https://www.somestore.com
```
Or double-click `run.bat` (or run `.\.venv\Scripts\python scraper.py` with nothing after it). It asks:
1. **Site URL or saved site name**, e.g. `https://www.jockey.in` or `jockey`
2. **How many products?** Press Enter for all.
3. **Folder to save the CSV in**: first time only, and it's remembered.

When it finishes:
```
============================================================
  TOTAL PRODUCTS : 3
  Image links    : 45
  Master CSV     : C:\dev\scrapper\csv\jockey.in_products.csv
============================================================
```

---

## Where Color and Size come from

**Shopify stores** (Jockey and many brands):
- **Size** comes from the product's Size option: `S, M, L, XL, XXL`.
- **Color** comes from the product's Color option if it has one (`Red, Blue`). If not (Jockey sells each colour
  as its own product), it comes from a `color:` tag, or else from the end of the product name:
  `... T-Shirt - Cosmic Sapphire` gives `Cosmic Sapphire`.
  Pack sizes are dropped: `Chilli Pepper & Navy (Pack of 2)` gives `Chilli Pepper & Navy`.
- Any other options (e.g. Fit) are added to the Size column: `S, M | Fit: Slim`.

**Other sites:** colour and size come from the page's structured data when the site provides it, and are empty otherwise.

---

## Settings: `config.json`

Created automatically on the first run, next to `scraper.py` (it's personal, so it isn't in git):
```json
{
  "csv_dir": "",
  "ask_path_every_run": false,
  "delay": 2.0,
  "cooldown": 60,
  "max_cooldown": 900,
  "max_blocks": 6
}
```
| Key | Meaning |
|---|---|
| `csv_dir` | Folder for the CSV. Empty `""` means ask on the next run |
| `ask_path_every_run` | `true` asks for the folder every time |
| `delay` | Seconds between requests to the website (plus 0–50% random jitter) |
| `cooldown` | First pause, in seconds, when the site blocks us. It doubles on each block in a row (60 → 120 → 240 …) |
| `max_cooldown` | Longest single pause (900 s = 15 min) |
| `max_blocks` | Pauses in a row before the run stops (re-run later to resume) |

---

## Speed and rate limits

### How fast is it?
On Shopify stores it uses two public sources, fastest first:

1. **Storefront API** (`/api/<version>/graphql.json`, no key needed). This is the API Shopify provides
   for storefronts and apps. It returns 250 products with all their images, colours and sizes per request,
   and it has its own, much more generous limits.
   **Jockey test: all 3,724 products and 29,006 image links in 37 seconds, with no rate limiting.**
2. **`/products.json`**: the classic feed. It has the same data, but stores often rate-limit it hard,
   sometimes right after the first 250 products. It's used only if a store turns the Storefront API off.

The log tells you which one is used:
`Storefront API not available here (HTTP 401); using /products.json instead.`

| Store size | Requests | Time at the default `delay: 2` |
|---|---|---|
| 1,000 products | 4 | ~10 s |
| 5,000 products | 20 | ~50 s |
| 20,000 products | 80 | ~4 min |

### Pick a pace
| Situation | `delay` |
|---|---|
| Normal first run on a store | `2` (default) |
| The store blocked you recently (lots of `HTTP 429`) | `20`–`60`, or wait a few hours / until the next day |
| Your own site, or one that never blocks | `0.5`–`1` |

Set it in `config.json`, or for one run: `--delay 30`.

### What happens when a site blocks
If the site answers HTTP 403/429/503 or a "Verifying your connection" page, the scraper
**pauses** (1 min, 2 min, 4 min … up to 15 min), **slows down** (the delay doubles, then speeds back up
after 100 good requests), and **retries the same request**, so nothing is skipped. You'll see:
```
WARNING www.jockey.in is rate-limiting us (HTTP 429). Pausing 60s, then retrying (1/6). New delay: 4.0s
```
That's normal. Leave it running.

- A request the site holds open without answering is treated the same way. There are **no hidden retries**:
  every request the site receives is one you see in the log.
- If blocks continue after `max_blocks` pauses, it **stops cleanly**. Everything collected so far is in the CSV
  (with the total), and the page where it stopped is remembered (see Resume).
- Rate limits are per network/IP and remember recent traffic. Many test runs in one day make the site stricter
  for hours; a single normal run usually goes straight through.

### Not included on purpose: proxies, IP rotation, browser cookies
They're deliberately left out. Rotating IPs or reusing a browser's
bot-check cookies is a way around the site's own limits, which breaks most stores' terms of use and gets
public scraper repos reported. They also aren't needed, because the Storefront API above already gets a whole
store in under a minute.

### Resume: continue where it stopped

The CSV is saved after **every page** (250 products), and the next page to fetch is stored in
`csv\<site>_products.progress.json`, including which source was used, so a resumed run continues on the same one. So if a run stops (site blocking, `Ctrl+C`, internet drop, PC restart):

1. Wait a while (30–60 min, or until the next day if the site blocked you a lot).
2. Run the **same command** again:
   ```powershell
   .\.venv\Scripts\python scraper.py --site jockey --no-prompt
   ```
   It says `Resuming from page 3: 490 products already in the CSV` and fetches only the remaining pages.
   Numbering and the total continue correctly, and nothing is duplicated.
3. When the whole list is done it prints `Complete: the whole product list was collected.` and deletes the progress file.

| Want to… | Command |
|---|---|
| Continue an unfinished run | the same command as before |
| Start over from page 1 | add `--fresh` |
| Continue from a specific `/products.json` page, adding to the existing CSV | add `--start-page 3` |

Test runs with `--max-products` never save or use a resume point.

---

## Adding a site

Save it in **`sites.json`** and run it by name with `--site <name>`:
```json
{
  "jockey":  { "url": "https://www.jockey.in", "mode": "shopify" },
  "mystore": { "url": "https://www.mystore.com" }
}
```
Any command-line option can go in an entry (write `-` as `_`). Options typed on the command line win.

### Non-Shopify sites
Most need two hints:
1. **`product_pattern`**: the part of the URL that marks product pages. If a product page is
   `https://shop.com/p/blue-shirt-123`, it's `/p/`.
2. **`image_selector`**: right-click a product photo, choose **Inspect**, and find the gallery's class, e.g.
   `.product-gallery img`. Optional, because the page's structured data and `og:image` are always read.
3. If the site's `sitemap.xml` is blocked, give a category page as `start_url`.
```json
"mystore": {
  "url": "https://shop.com",
  "mode": "generic",
  "product_pattern": "/p/",
  "image_selector": ".product-gallery img",
  "start_url": ["https://shop.com/category/shirts"]
}
```
Working example: `--site books-demo` (books.toscrape.com, a practice site).

---

## All options

| Option | Meaning |
|---|---|
| `url` | Site address (asked if omitted) |
| `--site` | A saved site from `sites.json` |
| `--max-products N` | Stop after N products (for testing) |
| `--collection` | Shopify: one category only, e.g. `men` |
| `--csv-out` | CSV folder for this run |
| `--delay` | Seconds between requests for this run |
| `--fresh` | Ignore an unfinished earlier run and start from page 1 |
| `--start-page N` | Shopify: continue from list page N, adding to the existing CSV |
| `--no-prompt` | Never ask questions |
| `--mode` | `auto` (default), `shopify`, `generic` |
| `--product-pattern` / `--image-selector` / `--start-url` | Non-Shopify hints (see above) |
| `-v` | Detailed log for troubleshooting |

## Troubleshooting
- **`Total Products, 0` on a non-Shopify site**: `product_pattern` doesn't match its product URLs. Run with `-v`.
- **`no images: <product>`**: that product has no photos on the site, so it isn't counted.
- Only scrape sites you are allowed to, and respect their terms of use.

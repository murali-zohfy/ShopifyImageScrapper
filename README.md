<div align="center">

# 🛍️ Shopify Image Scraper

**Every product. Every image link. One clean CSV.**

Point it at any Shopify store and get a single master CSV with each product's
name, colour, sizes and *all* of its image links, plus the total product count.

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![Shopify](https://img.shields.io/badge/works%20with-Shopify-95BF47?logo=shopify&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-1%20(requests)-informational)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

</div>

---

## ✨ Highlights

| | |
|---|---|
| ⚡ **Fast** | Uses Shopify's public **Storefront API**: 250 products per request. A real 3,700-product store took **37 seconds**. |
| 🧾 **One master CSV** | Product name, colour and size appear once per product, with one row per image link and the total at the end. |
| 🎨 **Colour & size aware** | Reads the store's Color/Size options. Stores that sell each colour as its own product get the colour from the title. |
| 🛡️ **Polite by design** | Paced requests with random jitter. It pauses and retries automatically on `429`, so nothing is skipped. |
| ⏯️ **Resumable** | Saves after every page. If a run stops, run the same command again and it continues where it left off. |
| 🧩 **No setup headaches** | One dependency. It asks for the store and folder in the terminal, or reads them from `config.json`. |

---

## 📄 What you get

`csv/jockey.in_products.csv`

| S.No | Product Name | Color | Size | Image No | Image Link |
|---|---|---|---|---|---|
| 1 | Round Neck Half Sleeve T-Shirt - Cosmic Sapphire | Cosmic Sapphire | S, M, L, XL, XXL | 1 | https://cdn.shopify.com/…_1.webp |
|   |   |   |   | 2 | https://cdn.shopify.com/…_2.webp |
|   |   |   |   | 3 | https://cdn.shopify.com/…_3.webp |
| 2 | Trino® Tubers - Onyx | Onyx | S (W5-7), M (W8-10 / M8), L … | 1 | https://cdn.shopify.com/…_FRONT.png |
|   |   |   |   | 2 | https://cdn.shopify.com/…_BACK.png |
|   |   |   |   |   |   |
| **Total Products** | **2** |   |   |   |   |

- **Total Products** counts each product **once**, however many images it has.
- Products with no photos are skipped and not counted.
- It's saved as UTF-8 with BOM, so Excel shows ₹, ®, accents and so on correctly.
- No images are downloaded, only their links.

---

## 🚀 Quick start

### 1. Install (once)

Requires **Python 3.10+** ([download](https://www.python.org/downloads/); on Windows tick *"Add Python to PATH"*).

```powershell
git clone <this-repo-url> ShopifyImageScrapper
cd ShopifyImageScrapper
```

| Windows | macOS / Linux |
|---|---|
| Double-click **`run.bat`** | `./run.sh` |

The first launch creates a private Python environment (`.venv`) and installs everything.

<details>
<summary>Manual setup instead</summary>

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt     # Windows
# .venv/bin/python -m pip install -r requirements.txt         # macOS / Linux
```
</details>

### 2. Run

```powershell
.\.venv\Scripts\python shopify_scraper.py
```

It asks in the terminal:

```text
Store URL or saved store name (e.g. https://www.jockey.in): https://www.allbirds.com
Save this store in config.json for next time? (y/n) [y]:
How many products? (Enter = all):
Folder to save the CSV in (Enter = default) [...\ShopifyImageScrapper\csv]: D:\exports
Save this folder in config.json for next time? (y/n) [y]:
```

### 3. Done

```text
10:02:50 INFO    Page 1: 250 products (250 fetched this run)
10:02:52 INFO    Page 2: 250 products (500 fetched this run)
   ...
10:03:26 INFO    Reached the end of the product list.

============================================================
  TOTAL PRODUCTS : 3723
  Image links    : 28999
  Source         : Storefront API
  Time           : 37s
  Master CSV     : D:\exports\jockey.in_products.csv
============================================================

  Complete: the whole product list was collected.
```

> On macOS / Linux, use `.venv/bin/python` wherever this README says `.\.venv\Scripts\python`.

---

## 🧭 Common commands

| I want to… | Command |
|---|---|
| Scrape a store | `.\.venv\Scripts\python shopify_scraper.py https://www.store.com` |
| Try it on 5 products first | `... shopify_scraper.py https://www.store.com --max-products 5` |
| Scrape one collection only | `... shopify_scraper.py https://www.store.com --collection men` |
| Use a saved store | `... shopify_scraper.py --site jockey` |
| Save the CSV somewhere else | `... shopify_scraper.py https://www.store.com --csv-out D:\exports` |
| Run unattended (no questions) | add `--no-prompt` |
| Start over, ignoring a stopped run | add `--fresh` |

The collection name is the last part of a collection page's URL:
`https://www.jockey.in/collections/men` → `--collection men`.

---

## ⚙️ Configuration

### `config.json`: your personal settings

It's created automatically from **`config.example.json`** on the first run, and it's **not tracked by git**,
so your paths stay on your machine.

```json
{
  "store_url": "https://your-store.com",
  "collection": "",
  "csv_dir": "C:/path/to/your/csv-folder",
  "delay": 2.0,
  "cooldown": 60,
  "max_cooldown": 900,
  "max_blocks": 6
}
```

| Key | What it does |
|---|---|
| `store_url` | The store to scrape when no URL is given on the command line |
| `collection` | `""` for the whole store, or a collection handle like `"men"` |
| `csv_dir` | Folder for the CSV (absolute, or relative to where you run it) |
| `delay` | Seconds between requests (+0–50 % random jitter) |
| `cooldown` | First pause when the store says "slow down"; it doubles each time (60 → 120 → 240 s …) |
| `max_cooldown` | Longest single pause (900 s = 15 min) |
| `max_blocks` | Pauses in a row before the run stops cleanly (resume later) |

**Where each setting comes from, first match wins:**

```text
store:   command line  →  --site (sites.json)  →  config.json  →  asked in the terminal
folder:  --csv-out     →  config.json          →  asked in the terminal  →  ./csv (with --no-prompt)
```

A placeholder value (`your-store.com`, `path/to/…`), an empty value, or a folder that can't be created
(e.g. a missing drive) is skipped, and you're asked instead.

### `sites.json`: saved stores

```json
{
  "jockey":     { "url": "https://www.jockey.in" },
  "jockey-men": { "url": "https://www.jockey.in", "collection": "men" },
  "allbirds":   { "url": "https://www.allbirds.com" }
}
```

Then run `--site jockey-men`. Any command-line option can go in an entry (write `-` as `_`), and options typed on the
command line still win.

---

## 🎨 How Color & Size are filled

| Column | Taken from |
|---|---|
| **Size** | The product's *Size* option, e.g. `S, M, L, XL` |
| **Color** | The product's *Color / Colour* option, e.g. `Red, Blue`. If there isn't one (many stores sell each colour as its own product), a `color:` tag, or the end of the title: `T-Shirt - Cosmic Sapphire` → `Cosmic Sapphire`. Pack sizes are dropped: `Navy (Pack of 2)` → `Navy` |
| *other options* | Added to Size, e.g. `S, M \| Fit: Slim` |

---

## ⚡ How it's fast *and* safe

```text
           ┌─────────────────────────────────────┐
 store ──► │ 1. Storefront API (GraphQL)          │ ──► 250 products / request
           │    /api/<version>/graphql.json       │     generous limits
           └──────────────┬──────────────────────┘
                          │ store turned it off?
                          ▼
           ┌─────────────────────────────────────┐
           │ 2. /products.json?limit=250&page=N   │ ──► same data, but often
           └─────────────────────────────────────┘     rate-limited after page 1
```

| Store size | Requests | Time at `delay: 2` |
|---|---|---|
| 1,000 products | 4 | ~10 s |
| 5,000 products | 20 | ~50 s |
| 20,000 products | 80 | ~4 min |

**When a store pushes back** (HTTP 403 / 429 / 503, a "verifying your connection" page, or no answer at all):

1. It **pauses**: 1 min, then 2, 4 … up to 15 min, or longer if the store asks via `Retry-After`.
2. It **slows down**: the delay doubles, then eases back after 100 good requests.
3. It **retries the same request**, so nothing is skipped.
4. After `max_blocks` pauses in a row, it **stops cleanly**, with everything so far saved.

```text
WARNING www.store.com is rate-limiting us (HTTP 429). Pausing 60s, then retrying (1/6). New delay: 4.0s
```

There are no hidden retries: every request the store receives appears in the log.

**Pick a pace:**

| Situation | `delay` |
|---|---|
| Normal run | `2` (default) |
| The store blocked you recently | `20`–`60`, or wait a few hours |
| Your own store | `0.5`–`1` |

> 🚫 **No proxies, IP rotation or cookie tricks.** They work around a store's own limits and break most stores'
> terms of use. They also aren't needed, because the Storefront API already gets a whole store in under a minute.

---

## ⏯️ Resume a stopped run

The CSV is saved after **every page** of 250 products, and the resume point is kept in `<csv>.progress.json`.
If a run stops (rate limit, `Ctrl+C`, Wi-Fi drop, reboot), run the **same command** again:

```text
INFO    Resuming from page 6: 1250 products already in the CSV. (Use --fresh to start over.)
```

Numbering and the total carry on correctly, and nothing is duplicated. When it finishes, the progress file is removed.

| Want to… | Add |
|---|---|
| Continue an unfinished run | nothing, just run the same command |
| Start over from scratch | `--fresh` |
| Continue from a specific `/products.json` page | `--start-page 6` |

Test runs with `--max-products` never save or use a resume point.

---

## 🧰 All options

| Option | Meaning |
|---|---|
| `url` | Store address, e.g. `https://www.jockey.in` |
| `--site NAME` | A saved store from `sites.json` |
| `--collection HANDLE` | One collection only, e.g. `men` |
| `--csv-out FOLDER` | CSV folder for this run |
| `--max-products N` | Stop after N products (testing) |
| `--delay SECONDS` | Seconds between requests for this run |
| `--fresh` | Ignore an unfinished run and start over |
| `--start-page N` | Continue from `/products.json` page N, adding to the existing CSV |
| `--no-prompt` | Never ask questions (scripts, Task Scheduler, cron) |
| `-v` | Detailed log |

---

## 🩺 Troubleshooting

| You see | What to do |
|---|---|
| `doesn't look like a Shopify store` | The site isn't Shopify, or it uses a custom front-end (e.g. headless). Try the store's `xxx.myshopify.com` address. |
| `Storefront API not available here … using /products.json` | Normal for a few stores. It still works, just with more rate limiting. |
| Lots of `HTTP 429` pauses | You've sent a lot of traffic recently. Leave it running, or stop with `Ctrl+C`, wait a few hours and resume. |
| `no images: <product>` | That product has no photos on the store, so it isn't counted. |
| Password-protected store | Not supported: the store isn't public. |

**Tested on:** jockey.in, allbirds.com, colourpop.com, fashionnova.com, kyliecosmetics.com, snitch.co.in, boat-lifestyle.com.

---

## 📁 Project layout

```text
ShopifyImageScrapper/
├── shopify_scraper.py     # the scraper (single file)
├── config.example.json    # template → copied to config.json on first run
├── sites.json             # saved stores
├── requirements.txt       # requests
├── run.bat / run.sh       # one-click start (sets up .venv on first run)
└── csv/                   # output (not in git)
```

---

## ⚖️ Responsible use

This tool reads **public** product data that every Shopify storefront exposes to browsers and apps.
Only scrape stores you're allowed to, respect their terms of use, and keep the default polite pace.

<div align="center">

# 🛍️ Shopify Image Scraper

**Every product. Every image link. One clean CSV.**

Give it any Shopify store and a folder, and you get one master CSV with each product's
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
| 🧩 **Two questions, that's it** | Store URL and folder. Everything else is an optional flag. |

---

## 🖥️ What it looks like

```text
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    🛍️  Shopify Image Scraper   ·   every product, every image link
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ➜  Store URL (e.g. https://your-store.com): https://www.jockey.in
  ➜  Folder to save the CSV (e.g. D:\exports): D:\exports

  10:02:49  ✔  Shopify store found: https://www.jockey.in
  10:02:50  ▸  Page 1    250 products   250 so far
  10:02:52  ▸  Page 2    250 products   500 so far
  10:02:54  ▸  Page 3    250 products   750 so far
            ⋮
  10:03:25  ▸  Page 15   233 products   3,733 so far
  10:03:25  ✔  Reached the end of the product list

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ✔  Done   ·   37s
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   📦  Products      3,723
   🖼️  Image links   28,999
   ⏭️  Skipped       10 without images
   ⚡  Source        Storefront API
   📄  CSV           D:\exports\jockey_products.csv
```

> In a modern terminal (Windows Terminal, macOS Terminal, VS Code) it's in colour too.

---

## 📄 What you get

**`jockey_products.csv`**: the file is named after the store, e.g. `allbirds_products.csv`, or
`jockey_men_products.csv` for one collection.

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

### 1️⃣ Install (once)

Requires **Python 3.10+** ([download](https://www.python.org/downloads/); on Windows tick *"Add Python to PATH"*).

```powershell
git clone <this-repo-url> ShopifyImageScrapper
cd ShopifyImageScrapper
```

| 🪟 Windows | 🍎 macOS / 🐧 Linux |
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

### 2️⃣ Run

```powershell
.\.venv\Scripts\python shopify_scraper.py
```

It asks two things:

| Question | Example answer |
|---|---|
| ➜ **Store URL** | `https://www.allbirds.com` |
| ➜ **Folder to save the CSV** | `D:\exports` (it's created if it doesn't exist) |

### 3️⃣ Open the CSV ✔

When it says **Done**, the path to your CSV is on the last line.

> 💡 On macOS / Linux, use `.venv/bin/python` wherever this README says `.\.venv\Scripts\python`.

---

## 🧭 Recipes

Answers can be given up front, so nothing is asked:

| I want to… | Command |
|---|---|
| 🏬 Scrape a whole store | `.\.venv\Scripts\python shopify_scraper.py https://www.store.com -o D:\exports` |
| 🧪 Try only the first 150 products | `... shopify_scraper.py https://www.store.com -o D:\exports -n 150` |
| 👕 Scrape one collection | `... shopify_scraper.py https://www.store.com -o D:\exports -c men` |
| 🐢 Go slower (store blocked you before) | `... shopify_scraper.py https://www.store.com -o D:\exports --delay 30` |
| 🔁 Start over, ignoring a stopped run | add `--fresh` |
| 🤖 Run unattended (Task Scheduler / cron) | add `--no-prompt` |

The collection name is the last part of a collection page's URL:
`https://www.jockey.in/collections/men` → `-c men`.

---

## 🧰 All options

| Option | Meaning |
|---|---|
| `url` | Store address, e.g. `https://www.jockey.in` *(asked if omitted)* |
| `-o`, `--csv-out FOLDER` | Folder for the CSV *(asked if omitted)* |
| `-n`, `--max-products N` | Stop after N products, e.g. `-n 150` |
| `-c`, `--collection HANDLE` | One collection only, e.g. `-c men` |
| `--delay SECONDS` | Seconds between requests (default `2`) |
| `--fresh` | Ignore an unfinished run and start over |
| `--start-page N` | Continue from `/products.json` page N, adding to the existing CSV |
| `--no-prompt` | Never ask questions; fail with a clear message if something is missing |
| `-v`, `--verbose` | Detailed log, including each product skipped for having no images |

---

## ⚙️ Optional: `config.json`

You don't need to touch it. It's created from **`config.example.json`** on the first run and
**isn't tracked by git**, so whatever you put there stays on your machine.

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
| `store_url` | Replace the placeholder to skip the *Store URL* question |
| `collection` | `""` for the whole store, or a collection handle like `"men"` |
| `csv_dir` | Replace the placeholder to skip the *Folder* question |
| `delay` | Seconds between requests (+0–50 % random jitter) |
| `cooldown` | First pause when the store says "slow down"; it doubles each time (60 → 120 → 240 s …) |
| `max_cooldown` | Longest single pause (900 s = 15 min) |
| `max_blocks` | Pauses in a row before the run stops cleanly (resume later) |

**Where each answer comes from, first match wins:**

```text
🏬 store   command line   →  config.json  →  asked in the terminal
📁 folder  -o / --csv-out  →  config.json  →  asked in the terminal
```

A placeholder, an empty value, or a folder that can't be created (e.g. a missing drive) is skipped,
and you're asked instead.

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
           ┌──────────────────────────────────────┐
 store ──► │ 1. Storefront API (GraphQL)           │ ──► 250 products / request
           │    /api/<version>/graphql.json        │     generous limits
           └──────────────┬───────────────────────┘
                          │ store turned it off?
                          ▼
           ┌──────────────────────────────────────┐
           │ 2. /products.json?limit=250&page=N    │ ──► same data, but often
           └──────────────────────────────────────┘     rate-limited after page 1
```

| Store size | Requests | Time at `--delay 2` |
|---|---|---|
| 1,000 products | 4 | ~10 s |
| 5,000 products | 20 | ~50 s |
| 20,000 products | 80 | ~4 min |

**When a store pushes back** (HTTP 403 / 429 / 503, a "verifying your connection" page, or no answer at all):

1. ⏸️ It **pauses**: 1 min, then 2, 4 … up to 15 min, or longer if the store asks via `Retry-After`.
2. 🐢 It **slows down**: the delay doubles, then eases back after 100 good requests.
3. 🔁 It **retries the same request**, so nothing is skipped.
4. 🛑 After `max_blocks` pauses in a row, it **stops cleanly**, with everything so far saved.

```text
  10:14:36  ⚠  Store is rate-limiting (HTTP 429) · pausing 60s · retry 1/6 · delay now 4.0s
```

There are no hidden retries: every request the store receives appears in the log.

> 🚫 **No proxies, IP rotation or cookie tricks.** They work around a store's own limits and break most stores'
> terms of use. They also aren't needed, because the Storefront API already gets a whole store in under a minute.

---

## ⏯️ Resume a stopped run

The CSV is saved after **every page** of 250 products, and the resume point is kept next to it in
`<store>_products.progress.json`. If a run stops (rate limit, `Ctrl+C`, Wi-Fi drop, reboot), run the
**same command** again:

```text
  10:20:11  ▸  Resuming from page 6 · 1,250 products already in the CSV (--fresh to start over)
```

Numbering and the total carry on correctly, and nothing is duplicated. When it finishes, the progress file is removed.
Test runs with `-n` never save or use a resume point.

---

## 🩺 Troubleshooting

| You see | What to do |
|---|---|
| `✖ … doesn't look like a Shopify store` | The site isn't Shopify, or it uses a custom front-end (e.g. headless). Try the store's `xxx.myshopify.com` address. |
| `▸ Storefront API is off on this store … switching to /products.json` | Normal for a few stores. It still works, just with more rate limiting. |
| Lots of `⚠ Store is rate-limiting` | You've sent a lot of traffic recently. Leave it running, or press `Ctrl+C`, wait a few hours and resume. |
| Odd symbols instead of ✔ ➜ 📦 | You're in an old console. Use **Windows Terminal**, or set `NO_COLOR=1` to turn colours off. |
| Password-protected store | Not supported: the store isn't public. |

**Tested on:** jockey.in, allbirds.com, colourpop.com, fashionnova.com, kyliecosmetics.com, snitch.co.in, boat-lifestyle.com.

---

## 📁 Project layout

```text
ShopifyImageScrapper/
├── shopify_scraper.py     # the scraper (single file)
├── config.example.json    # template → copied to config.json on first run
├── requirements.txt       # requests
├── run.bat / run.sh       # one-click start (sets up .venv on first run)
└── <your folder>/         # the CSVs (wherever you choose)
```

---

## ⚖️ Responsible use

This tool reads **public** product data that every Shopify storefront exposes to browsers and apps.
Only scrape stores you're allowed to, respect their terms of use, and keep the default polite pace.

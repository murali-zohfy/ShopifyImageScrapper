"""
Shopify Image Scraper -> one master CSV per store.

Collects every product's image links from any Shopify store, with the product
name, colour and sizes, and ends with the total number of (unique) products.
No images are downloaded.

    S.No, Product Name, Color, Size, Image No, Image Link
    1,    Round Neck T-Shirt - Cosmic Sapphire, Cosmic Sapphire, "S, M, L", 1, https://...
     ,    ,                                     ,               ,          2, https://...
    ...
    Total Products, 1234

Sources (both public, fastest first):
  1. Storefront API  /api/<version>/graphql.json  (no key needed, 250 products per request)
  2. /products.json  (classic feed, used if a store turns the Storefront API off)

See README.md for how to run it.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import random
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter

log = logging.getLogger("scraper")

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
CSV_COLUMNS = ["S.No", "Product Name", "Color", "Size", "Image No", "Image Link"]


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class Product:
    title: str
    url: str
    images: list[str] = field(default_factory=list)
    id: str = ""
    color: str = ""   # "Cosmic Sapphire"  or  "Red, Blue"
    size: str = ""    # "S, M, L, XL"      (+ any other options, e.g. "S, M | Fit: Slim")
    page: int = 0     # Shopify list page it came from (0 = not paged)


# --------------------------------------------------------------------------- #
# Polite HTTP session (rate-limit control)
# --------------------------------------------------------------------------- #
class BlockedError(Exception):
    """The site kept blocking us even after all cool-down pauses."""


BLOCK_STATUSES = {403, 429, 503}
CHALLENGE_MARKERS = (b"Verifying your connection", b"cf-challenge", b"captcha", b"Access Denied")


class PoliteSession(requests.Session):
    """A requests.Session that behaves like a patient visitor:

    * Throttle: at least `delay` seconds between two requests to the same host.
    * Jitter:   +0-50% random on each wait, so requests don't arrive like a metronome.
    * Cool-down: on 403/429/503 or a "verifying your connection" page, pause
      (cooldown, 2x, 4x ... up to max_cooldown) and retry the same request.
      After `max_blocks` pauses in a row -> BlockedError (stop cleanly, resume later).
    * Slow-down: each block doubles the delay (max 10s); after 100 good requests in a
      row it speeds back up step by step, never below the configured delay.
    """

    SLOWEST = 10.0
    RECOVER_AFTER = 100

    def __init__(self, delay: float = 1.0, cooldown: float = 60, max_cooldown: float = 900,
                 max_blocks: int = 6):
        super().__init__()
        self.delay = delay
        self.cooldown, self.max_cooldown, self.max_blocks = cooldown, max_cooldown, max_blocks
        self._lock = threading.Lock()
        self._next_ok: dict[str, float] = {}
        self._host_delay: dict[str, float] = {}
        self._ok_streak: dict[str, int] = {}
        self.blocks = 0

    def _cur_delay(self, host: str) -> float:
        return self._host_delay.setdefault(host, self.delay)

    def _wait_turn(self, host: str) -> None:
        with self._lock:
            now = time.monotonic()
            start = max(now, self._next_ok.get(host, 0))
            self._next_ok[host] = start + self._cur_delay(host) * (1 + random.random() * 0.5)
        if start > now:
            if start - now >= 5:
                log.info("Waiting %ds before the next request (safe pace) ...", start - now)
            time.sleep(start - now)

    def _on_success(self, host: str) -> None:
        with self._lock:
            self._ok_streak[host] = self._ok_streak.get(host, 0) + 1
            cur = self._cur_delay(host)
            if cur > self.delay and self._ok_streak[host] >= self.RECOVER_AFTER:
                self._host_delay[host] = max(self.delay, cur * 0.75)
                self._ok_streak[host] = 0
                log.info("%s: no blocks for a while, delay lowered to %.1fs", host, self._host_delay[host])

    @staticmethod
    def _looks_blocked(r: requests.Response) -> bool:
        if r.status_code in BLOCK_STATUSES:
            return True
        if r.status_code == 200 and "text/html" in r.headers.get("Content-Type", ""):
            # bot-check pages are small; real pages are bigger (avoids false alarms)
            body = r.content
            return len(body) < 30_000 and any(m.lower() in body.lower() for m in CHALLENGE_MARKERS)
        return False

    def request(self, method, url, *args, probe: bool = False, **kwargs):
        """probe=True: one paced request, answer returned as-is (no pause/retry).
        Used to ask "does this site support X?" without waiting minutes on a 429."""
        host = urlparse(url).netloc.lower()
        strikes = 0
        while True:
            self._wait_turn(host)
            log.debug("%s %s", method, url)
            if probe:
                return super().request(method, url, *args, **kwargs)
            try:
                r = super().request(method, url, *args, **kwargs)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                # a site that holds the connection open without answering is also
                # telling us to back off -> same pause/retry as a 429
                r, why = None, f"no answer: {type(e).__name__}"
            else:
                if not self._looks_blocked(r):
                    self._on_success(host)
                    return r
                why = f"HTTP {r.status_code}" if r.status_code != 200 else "bot-check page"
            strikes += 1
            self.blocks += 1
            if strikes > self.max_blocks:
                raise BlockedError(f"{host} is still blocking after {self.max_blocks} pauses ({why})")
            pause = min(self.cooldown * 2 ** (strikes - 1), self.max_cooldown)
            retry_after = r.headers.get("Retry-After", "") if r is not None else ""
            if retry_after.isdigit():
                pause = min(max(pause, int(retry_after)), self.max_cooldown)
            with self._lock:
                self._next_ok[host] = max(self._next_ok.get(host, 0), time.monotonic() + pause)
                ceiling = max(self.SLOWEST, self.delay * 2)
                self._host_delay[host] = min(max(self._cur_delay(host) * 2, 0.5), ceiling)
                self._ok_streak[host] = 0
            log.warning("%s is rate-limiting us (%s). Pausing %ds, then retrying (%d/%d). "
                        "New delay: %.1fs", host, why, pause, strikes, self.max_blocks,
                        self._host_delay[host])
            if r is not None:
                r.close()


def make_session(**polite) -> PoliteSession:
    s = PoliteSession(**polite)
    s.headers.update({"User-Agent": DEFAULT_UA, "Accept-Language": "en-US,en;q=0.9"})
    # No silent retries: every request the site sees is one we logged and paced.
    # (Timeouts, connection drops and 429/403/503 are handled in PoliteSession.)
    adapter = HTTPAdapter(max_retries=0)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def normalize_base(url: str) -> str:
    if not re.match(r"^https?://", url):
        url = "https://" + url
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def site_name(base: str) -> str:
    return re.sub(r"^www\.", "", urlparse(base).netloc.lower()).split(":")[0]


def safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .") or "site"


def abs_url(url: str, base: str) -> str:
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    return urljoin(base + "/", url)


def dedupe(seq) -> list:
    seen, out = set(), []
    for x in seq:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def color_from_title(title: str) -> str:
    """'Round Neck T-Shirt - Cosmic Sapphire' -> 'Cosmic Sapphire'
    'Trunk - Chilli Pepper & Navy (Pack of 2)' -> 'Chilli Pepper & Navy'"""
    head, sep, tail = title.rpartition(" - ")
    if sep and head and 0 < len(tail) <= 60:
        return re.sub(r"\s*\(pack of \d+\)\s*$", "", tail, flags=re.I).strip()
    return ""


# --------------------------------------------------------------------------- #
# Shopify
# --------------------------------------------------------------------------- #
COLOR_NAMES = {"color", "colour", "colors", "colours", "shade"}
SIZE_NAMES = {"size", "sizes"}


STOREFRONT_VERSION = "2025-10"  # Shopify serves the oldest supported version if this one retires
PRODUCT_FIELDS = """pageInfo { hasNextPage endCursor }
  nodes { id title handle tags options { name optionValues { name } } images(first: 250) { nodes { url } } }"""
STOREFRONT_QUERY = "query($after: String) { products(first: 250, after: $after) { %s } }" % PRODUCT_FIELDS
STOREFRONT_COLLECTION_QUERY = ("query($after: String, $handle: String!) { collection(handle: $handle) "
                               "{ products(first: 250, after: $after) { %s } } }" % PRODUCT_FIELDS)


class StorefrontUnavailable(Exception):
    """The store doesn't allow tokenless Storefront API access (use /products.json)."""


def is_shopify_response(r: requests.Response) -> bool:
    h = {k.lower(): v for k, v in r.headers.items()}
    return h.get("powered-by", "").lower() == "shopify" or "x-shopid" in h or "x-shopify-stage" in h


class ShopifyScraper:
    """Two public Shopify sources, fastest first:

    1. Storefront API (POST /api/<version>/graphql.json, no token needed): the API
       Shopify provides for storefronts and apps. 250 products with all images and
       options per request, with its own, much more generous limits.
    2. /products.json?limit=250&page=N: the classic feed. Same data, but stores
       often rate-limit it hard (e.g. right after the first page).
    """

    def __init__(self, session: requests.Session, base: str, collection: str | None = None,
                 start_page: int = 1, cursor: str | None = None, api: str = "auto"):
        self.s, self.base, self.collection = session, base, collection
        self.page = start_page  # the list page being fetched/processed right now
        self.cursor = cursor    # Storefront API: where page `start_page` begins
        self.api = api          # "auto" | "storefront" | "json"
        self.used = ""          # the source actually used
        self.page_cursor: dict[int, str | None] = {}

    @property
    def graphql_url(self) -> str:
        return f"{self.base}/api/{STOREFRONT_VERSION}/graphql.json"

    @staticmethod
    def detect(session: PoliteSession, base: str) -> bool:
        try:
            r = session.post(f"{base}/api/{STOREFRONT_VERSION}/graphql.json", probe=True, timeout=20,
                             json={"query": "{ shop { name } }"})
            if r.ok and "shop" in ((r.json() or {}).get("data") or {}):
                return True
        except Exception:
            pass
        try:
            r = session.get(f"{base}/products.json", params={"limit": 1}, probe=True, timeout=20)
            if r.ok:
                return "products" in r.json()
            return is_shopify_response(r)  # e.g. a 429 that clearly comes from Shopify
        except Exception:
            return False

    def resume_point(self, page: int) -> dict:
        """What to store so a later run can continue at `page`."""
        return {"api": self.used, "next_page": page, "cursor": self.page_cursor.get(page)}

    @staticmethod
    def color_and_size(p: dict) -> tuple[str, str]:
        color, size, other = "", "", []
        for o in p.get("options") or []:
            name = (o.get("name") or "Option").strip()
            values = [str(v) for v in o.get("values", []) if v != "Default Title"]
            if not values:
                continue
            if name.lower() in COLOR_NAMES:
                color = ", ".join(values)
            elif name.lower() in SIZE_NAMES:
                size = ", ".join(values)
            else:
                other.append(f"{name}: {', '.join(values)}")
        if not color:
            # no Color option (e.g. Jockey sells each colour as its own product):
            # try a 'color:Red' tag, then the end of the title
            tags = p.get("tags") or []
            tags = tags.split(",") if isinstance(tags, str) else tags
            for t in tags:
                if m := re.match(r"^\s*colou?r\s*[:_=-]\s*(.+)$", str(t), re.I):
                    color = m.group(1).strip()
                    break
            color = color or color_from_title(p.get("title") or "")
        if other:
            size = " | ".join(([size] if size else []) + other)
        return color, size

    def _product(self, p: dict, images: list, page: int) -> Product:
        color, size = self.color_and_size(p)
        return Product(
            title=p.get("title") or p.get("handle", ""),
            url=f"{self.base}/products/{p.get('handle')}",
            images=dedupe(abs_url(u, self.base) for u in images if u),
            id=str(p.get("id", "")).rsplit("/", 1)[-1],  # gid://shopify/Product/123 -> 123
            color=color,
            size=size,
            page=page,
        )

    def products(self) -> Iterator[Product]:
        if self.api in ("auto", "storefront"):
            try:
                yield from self._storefront()
                return
            except StorefrontUnavailable as e:
                log.info("Storefront API not available here (%s); using /products.json instead.", e)
                # different ordering -> restart the list; products already in the CSV are skipped
                self.page, self.cursor = 1, None
        yield from self._products_json()

    def _storefront(self) -> Iterator[Product]:
        self.used = "storefront"
        after, total, first = self.cursor, 0, True
        query = STOREFRONT_COLLECTION_QUERY if self.collection else STOREFRONT_QUERY
        while True:
            page = self.page
            self.page_cursor[page] = after
            variables = {"after": after, **({"handle": self.collection} if self.collection else {})}
            # the very first request is a probe: if the store refuses, fall back at once
            r = self.s.post(self.graphql_url, json={"query": query, "variables": variables},
                            timeout=60, probe=first)
            try:
                data = r.json() or {}
            except ValueError:
                data = {}
            if first and (not r.ok or "data" not in data):
                raise StorefrontUnavailable(f"HTTP {r.status_code}")
            if data.get("errors") or not data.get("data"):
                msg = "; ".join(str(e.get("message")) for e in data.get("errors") or [])[:200]
                raise StorefrontUnavailable(msg or f"HTTP {r.status_code}")
            first = False
            root = data["data"]
            if self.collection:
                if not root.get("collection"):
                    raise StorefrontUnavailable(f"no collection '{self.collection}'")
                root = root["collection"]
            conn = root["products"]
            items = conn["nodes"]
            total += len(items)
            log.info("Page %d: %d products (%d fetched this run)", page, len(items), total)
            for p in items:
                p["options"] = [{"name": o.get("name"),
                                 "values": [v.get("name") for v in o.get("optionValues") or []]}
                                for o in p.get("options") or []]
                yield self._product(p, [i.get("url") for i in p["images"]["nodes"]], page)
            if not conn["pageInfo"]["hasNextPage"] or not items:
                log.info("Reached the end of the product list.")
                return
            after = conn["pageInfo"]["endCursor"]
            self.page = page + 1
            self.page_cursor[self.page] = after

    def _products_json(self) -> Iterator[Product]:
        self.used = "json"
        path = f"/collections/{self.collection}/products.json" if self.collection else "/products.json"
        total = 0
        while True:
            page = self.page
            r = self.s.get(f"{self.base}{path}", params={"limit": 250, "page": page}, timeout=60)
            r.raise_for_status()
            items = r.json().get("products", [])
            if not items:
                log.info("Reached the end of the product list.")
                return
            total += len(items)
            log.info("Page %d: %d products (%d fetched this run)", page, len(items), total)
            for p in items:
                yield self._product(p, [i.get("src") for i in p.get("images", [])], page)
            self.page = page + 1


# --------------------------------------------------------------------------- #
# Master CSV
# --------------------------------------------------------------------------- #
class MasterCsv:
    """The master CSV: one row per image link. S.No / Product Name / Color / Size only on
    each product's first row; the last line is the total number of unique products.

    Next to it lives '<name>.progress.json' while a run is unfinished, so the next run
    can continue from the page where it stopped instead of starting over."""

    def __init__(self, path: Path):
        self.path = path
        self.progress_path = path.with_name(path.stem + ".progress.json")
        self.rows: list[list] = []
        self.products = 0
        self.seen: set[str] = set()

    # ---- existing data (resume) ----
    def load_existing(self) -> None:
        if not self.path.exists():
            return
        with open(self.path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)  # header
            for row in reader:
                if not row or not any(row) or row[0] == "Total Products":
                    break
                self.rows.append(row)
                if row[0]:
                    self.products += 1

    def load_progress(self) -> dict | None:
        try:
            return json.loads(self.progress_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    # ---- add + save ----
    def add(self, p: Product) -> bool:
        """Add a product's rows; False if it was a duplicate or had no images."""
        key = p.id or p.url
        if key in self.seen:     # same product listed twice -> count once
            return False
        self.seen.add(key)
        if not p.images:
            log.info("no images: %s", p.title)
            return False
        self.products += 1
        n = self.products
        for i, link in enumerate(p.images, 1):
            first = i == 1
            self.rows.append([n if first else "", p.title if first else "", p.color if first else "",
                              p.size if first else "", i, link])
        return True

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.stem + ".saving.tmp")
        # utf-8-sig so Excel shows special characters correctly
        with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(CSV_COLUMNS)
            w.writerows(self.rows)
            w.writerow([])
            w.writerow(["Total Products", self.products])
        tmp.replace(self.path)  # the CSV on disk is always complete and valid

    def save_progress(self, info: dict) -> None:
        info = {**info, "products_in_csv": self.products, "seen": sorted(self.seen)}
        self.progress_path.write_text(json.dumps(info), encoding="utf-8")

    def clear_progress(self) -> None:
        self.progress_path.unlink(missing_ok=True)


def collect(products: Iterator[Product], master: MasterCsv, scraper, resume_info: dict | None,
            max_products: int | None = None) -> dict:
    """Pull products into the master CSV. The CSV (and, for Shopify, the resume point)
    is saved after every list page, so an interruption never loses finished pages."""
    stats = {"added": 0, "no_images": 0, "error": None, "finished": False}
    paged = resume_info is not None
    current_page = None
    try:
        for p in products:
            if max_products and stats["added"] >= max_products:
                break
            if paged and p.page != current_page:
                if current_page is not None:  # previous page fully done -> checkpoint
                    master.save()
                    master.save_progress({**resume_info, **scraper.resume_point(p.page)})
                current_page = p.page
            if master.add(p):
                stats["added"] += 1
            elif not p.images:
                stats["no_images"] += 1
        else:
            stats["finished"] = True
    except KeyboardInterrupt:
        stats["error"] = "Interrupted (Ctrl+C)."
    except BlockedError as e:
        stats["error"] = f"Stopped: {e}"
    finally:
        master.save()
        if paged:
            if stats["finished"]:
                master.clear_progress()
            else:
                master.save_progress({**resume_info, **scraper.resume_point(scraper.page)})
    return stats


# --------------------------------------------------------------------------- #
# Settings (config.json, kept outside the code) + prompts
# --------------------------------------------------------------------------- #
HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "config.json"
EXAMPLE_CONFIG_PATH = HERE / "config.example.json"
DEFAULT_CSV_DIR = HERE / "csv"
DEFAULT_CONFIG = {
    "store_url": "https://your-store.com",       # placeholder -> asked in the terminal
    "collection": "",                           # "" = whole store, or a collection handle e.g. "men"
    "csv_dir": "C:/path/to/your/csv-folder",    # placeholder -> asked in the terminal
    # ---- rate-limit control ----
    "delay": 2.0,           # seconds between requests to the store
    "cooldown": 60,         # first pause (seconds) when blocked; doubles each time
    "max_cooldown": 900,    # longest single pause (15 min)
    "max_blocks": 6,        # pauses in a row before stopping (re-run later to resume)
}


def is_placeholder(value) -> bool:
    """True for empty values and the example values shipped in config.example.json."""
    v = str(value or "").strip().replace("\\", "/").lower()
    return not v or "your-store" in v or "path/to/" in v or v.startswith("<")


def load_config() -> dict:
    """config.json is personal (not in git). On the first run it's created from
    config.example.json, so it starts with placeholders that get asked for."""
    if not CONFIG_PATH.exists():
        src = EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8") if EXAMPLE_CONFIG_PATH.exists() \
            else json.dumps(DEFAULT_CONFIG, indent=2)
        CONFIG_PATH.write_text(src, encoding="utf-8")
    cfg = dict(DEFAULT_CONFIG)
    try:
        saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"config.json is not valid JSON ({e}). Fix it, or delete it to start from the example.")
    cfg.update({k: v for k, v in saved.items() if k in DEFAULT_CONFIG})
    if set(saved) != set(DEFAULT_CONFIG):  # old/extra/missing keys -> tidy it up
        save_config(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def ask(question: str, default: str = "") -> str:
    try:
        ans = input(f"{question}{f' [{default}]' if default else ''}: ").strip().strip('"')
    except EOFError:
        ans = ""
    return ans or default


def remember(cfg: dict, key: str, value: str, what: str, no_prompt: bool) -> None:
    if no_prompt or cfg.get(key) == value:
        return
    if ask(f"Save this {what} in config.json for next time? (y/n)", "y").lower().startswith("y"):
        cfg[key] = value
        save_config(cfg)


def usable_folder(folder: str) -> Path | None:
    """The folder as a Path if it exists or can be created, else None."""
    try:
        path = Path(os.path.expandvars(os.path.expanduser(folder)))
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError as e:
        log.warning("Can't use the folder %r (%s).", folder, e)
        return None


def resolve_csv_dir(args: argparse.Namespace, cfg: dict) -> Path:
    """CSV folder: --csv-out, then config.json, then a question in the terminal.
    A placeholder, empty or unusable path falls through to the next option."""
    for folder in (args.csv_out, cfg.get("csv_dir")):
        if folder and not is_placeholder(folder) and (path := usable_folder(folder)):
            return path
    if args.no_prompt:
        log.info("No usable CSV folder in config.json; using %s", DEFAULT_CSV_DIR)
        return usable_folder(str(DEFAULT_CSV_DIR)) or DEFAULT_CSV_DIR
    while True:
        folder = ask("Folder to save the CSV in (Enter = default)", str(DEFAULT_CSV_DIR))
        if path := usable_folder(folder):
            remember(cfg, "csv_dir", folder, "folder", args.no_prompt)
            return path
        print("  That folder can't be used. Try another one.")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Collect every product's image links from a Shopify store into one master CSV.")
    ap.add_argument("url", nargs="?", help="Store URL, e.g. https://www.jockey.in (else config.json, else asked)")
    ap.add_argument("--site", help="Use a saved store from sites.json")
    ap.add_argument("--sites-file", default=str(HERE / "sites.json"))
    ap.add_argument("--collection", help="Only one collection, e.g. 'men' (from /collections/men)")
    ap.add_argument("--csv-out", help="CSV folder for this run (overrides config.json)")
    ap.add_argument("--max-products", type=int, help="Stop after N products (for testing)")
    ap.add_argument("--delay", type=float, help="Seconds between requests (overrides config.json)")
    ap.add_argument("--fresh", action="store_true",
                    help="Ignore an unfinished earlier run and start again from the beginning")
    ap.add_argument("--start-page", type=int,
                    help="Continue from /products.json page N, adding to the existing CSV")
    ap.add_argument("--no-prompt", action="store_true", help="Never ask questions (for scripts/schedulers)")
    ap.add_argument("-v", "--verbose", action="store_true", help="Detailed log")
    args = ap.parse_args(argv)

    profiles = {}
    if Path(args.sites_file).exists():
        profiles = json.loads(Path(args.sites_file).read_text(encoding="utf-8"))
    if args.site:
        if args.site not in profiles:
            sys.exit(f"'{args.site}' is not in {args.sites_file}. Saved stores: {', '.join(profiles)}")
        for k, v in profiles[args.site].items():
            k = k.replace("-", "_")
            if getattr(args, k, None) in (None, False):  # command-line flags win
                setattr(args, k, v)
    args.profiles = profiles
    return args


def resolve_store(args: argparse.Namespace, cfg: dict) -> None:
    """Store URL: command line / --site, then config.json, then a question in the terminal."""
    if not args.url and not is_placeholder(cfg.get("store_url")):
        args.url = cfg["store_url"]
        if args.collection is None and cfg.get("collection"):
            args.collection = cfg["collection"]
    if args.url:
        return
    if args.no_prompt:
        sys.exit("No store URL. Give one (shopify_scraper.py https://store.com), use --site, "
                 "or set \"store_url\" in config.json.")
    if args.profiles:
        print("Saved stores (sites.json):", ", ".join(args.profiles))
    while not args.url:
        answer = ask("Store URL or saved store name (e.g. https://www.jockey.in)")
        if answer in args.profiles:
            args.site = answer
            for k, v in args.profiles[answer].items():
                if getattr(args, k.replace("-", "_"), None) in (None, False):
                    setattr(args, k.replace("-", "_"), v)
        elif answer:
            args.url = answer
            remember(cfg, "store_url", normalize_base(answer), "store", args.no_prompt)
    if args.max_products is None:
        n = ask("How many products? (Enter = all)")
        args.max_products = int(n) if n.isdigit() else None


def main(argv=None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    cfg = load_config()
    resolve_store(args, cfg)
    csv_dir = resolve_csv_dir(args, cfg)
    delay = cfg["delay"] if args.delay is None else args.delay

    base = normalize_base(args.url)
    session = make_session(delay=delay, cooldown=cfg["cooldown"],
                           max_cooldown=cfg["max_cooldown"], max_blocks=cfg["max_blocks"])
    log.info("Store: %s%s  |  %.1fs between requests", base,
             f"  |  collection: {args.collection}" if args.collection else "", delay)
    if not ShopifyScraper.detect(session, base):
        sys.exit(f"\n{base} doesn't look like a Shopify store (or it's blocking us right now).\n"
                 "Tip: some stores use a custom front-end; try the store's xxx.myshopify.com address.")

    site = site_name(base)
    suffix = f"_{safe_filename(args.collection)}" if args.collection else ""
    master = MasterCsv(csv_dir / f"{site}{suffix}_products.csv")

    # ---- resume an unfinished run? (test runs with --max-products never resume)
    resume_info = None
    start_page, cursor, api = 1, None, "auto"
    if not args.max_products:
        resume_info = {"site": base, "collection": args.collection or ""}
        progress = master.load_progress()
        same_run = progress and {k: progress.get(k) for k in resume_info} == resume_info
        if args.start_page:
            start_page, api = args.start_page, "json"  # page numbers belong to /products.json
        elif same_run and not args.fresh:
            start_page = int(progress.get("next_page", 1))
            if progress.get("api") == "storefront" and progress.get("cursor"):
                cursor, api = progress["cursor"], "storefront"
            elif start_page > 1:
                api = "json"
        if start_page > 1:
            master.load_existing()
            if same_run:
                master.seen = set(progress.get("seen", []))
            log.info("Resuming from page %d: %d products already in the CSV. "
                     "(Use --fresh to start over.)", start_page, master.products)
        else:
            master.clear_progress()

    scraper = ShopifyScraper(session, base, collection=args.collection, start_page=start_page,
                             cursor=cursor, api=api)
    started = time.monotonic()
    stats = collect(scraper.products(), master, scraper, resume_info, max_products=args.max_products)
    took = time.monotonic() - started

    print()
    print("=" * 60)
    print(f"  TOTAL PRODUCTS : {master.products}" + (f"   ({stats['added']} added this run)"
                                                     if start_page > 1 else ""))
    print(f"  Image links    : {len(master.rows)}")
    if stats["no_images"]:
        print(f"  Skipped        : {stats['no_images']} product(s) with no images")
    if session.blocks:
        print(f"  Rate limits    : store slowed us down {session.blocks} time(s); handled automatically")
    print(f"  Source         : {'Storefront API' if scraper.used == 'storefront' else '/products.json'}")
    print(f"  Time           : {took:.0f}s")
    print(f"  Master CSV     : {master.path.resolve()}")
    print("=" * 60)
    if stats["error"]:
        print(f"\n  {stats['error']}")
        print("  The CSV has everything collected so far.")
        if resume_info is not None:
            print(f"  Run the SAME command again later and it continues from page {scraper.page}.")
        else:
            print("  Run the same command again later for the complete list.")
        sys.exit(1)
    if resume_info is not None and stats["finished"]:
        print("\n  Complete: the whole product list was collected.")


if __name__ == "__main__":
    main()

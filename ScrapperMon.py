"""
Fetch Nifty/Sensex prices and upcoming stock events via Google Finance.

Usage:
    python ScrapperMon.py
    python ScrapperMon.py INFY TCS
    python ScrapperMon.py INFY --headless

Events require: pip install playwright && python -m playwright install chromium
"""

import argparse
import http.client as http_client
import logging
import re
import sys
import threading
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

ENABLE_HTTP_DEBUG = False

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30

GOOGLE_SEARCH_URL = (
    "https://www.google.com/search"
    "?q=nifty+50+and+sensex+index+price+today&gbv=1&hl=en"
)
GOOGLE_FINANCE_TICKERS = {
    "Nifty 50": "NIFTY_50:INDEXNSE",
    "Sensex": "SENSEX:INDEXBOM",
}
FINANCE_RESEARCH_URL = "https://www.google.com/finance/beta/#research"
EVENTS_QUERY_TEMPLATE = (
    "upcoming events on {symbol}. "
    "Reply with only a bullet list of events and dates, no intro text."
)

INDICES_CSV = "financial_data.csv"
EVENTS_CSV = "stock_events.csv"

if ENABLE_HTTP_DEBUG:
    http_client.HTTPConnection.debuglevel = 1
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.DEBUG)


def fetch_page(url, label):
    """Fetch a URL with progress logging, heartbeat, and timeouts."""
    print(f"   Fetching {label}...", flush=True)
    t0 = time.perf_counter()
    done = False

    def heartbeat():
        elapsed = 0
        while not done:
            time.sleep(5)
            elapsed += 5
            if not done:
                print(f"      ... still waiting on {label} ({elapsed}s)", flush=True)

    threading.Thread(target=heartbeat, daemon=True).start()

    try:
        response = requests.get(
            url,
            stream=True,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            headers=HEADERS,
        )
        print(
            f"   {label}: connected in {time.perf_counter() - t0:.1f}s "
            f"— status {response.status_code}",
            flush=True,
        )
        content = response.content
        print(
            f"   {label}: downloaded {len(content)} bytes "
            f"in {time.perf_counter() - t0:.1f}s",
            flush=True,
        )
        return content
    finally:
        done = True


def parse_google_search_prices(html):
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    if "Please click here if you are not redirected" in text:
        print("   Google Search returned a bot-check page (no usable results).", flush=True)
        return {}

    patterns = {
        "Nifty 50": r"Nifty\s*50[^0-9]{0,40}([0-9,]+\.?[0-9]*)",
        "Sensex": r"(?:BSE\s*)?S(?:ensex|ENSEX)[^0-9]{0,40}([0-9,]+\.?[0-9]*)",
    }
    prices = {}
    for name, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            prices[name] = match.group(1)
    return prices


def scrape_google_finance(ticker):
    url = f"https://www.google.com/finance/quote/{ticker}"
    html = fetch_page(url, ticker)
    soup = BeautifulSoup(html, "html.parser")
    price_el = soup.select_one("div.N6SYTe")
    return price_el.get_text(strip=True) if price_el else None


def fetch_index_prices():
    print("A. Fetching index prices...", flush=True)

    print("   Trying Google Search first...", flush=True)
    search_html = fetch_page(GOOGLE_SEARCH_URL, "Google Search")
    search_prices = parse_google_search_prices(search_html)
    if search_prices:
        print(f"   Parsed from search: {search_prices}", flush=True)
    else:
        print("   Search scrape found nothing — falling back to Google Finance.", flush=True)

    print("   Fetching quotes from Google Finance...", flush=True)
    finance_prices = {}
    for name, ticker in GOOGLE_FINANCE_TICKERS.items():
        value = scrape_google_finance(ticker)
        finance_prices[name] = value or "Not found"
        print(f"   {name}: {finance_prices[name]}", flush=True)

    final_prices = {
        name: search_prices.get(name) or finance_prices.get(name, "Not found")
        for name in GOOGLE_FINANCE_TICKERS
    }

    df = pd.DataFrame(
        {
            "Index": list(final_prices.keys()),
            "Value": list(final_prices.values()),
            "Source": [
                "Google Search" if name in search_prices else "Google Finance"
                for name in final_prices
            ],
        }
    )
    df.to_csv(INDICES_CSV, index=False)
    print(f"   Saved index data to {INDICES_CSV}", flush=True)
    return df


def clean_event_line(text):
    line = text.strip()
    line = re.sub(r"\s*link\s*$", "", line, flags=re.IGNORECASE)
    return line.strip()


def fetch_stock_events(symbol, headless=False, timeout_ms=120_000):
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright

    query = EVENTS_QUERY_TEMPLATE.format(symbol=symbol.upper())
    print(f"   Research query for {symbol.upper()}...", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(
            viewport={"width": 1400, "height": 900},
            user_agent=HEADERS["User-Agent"],
        )

        page.goto(FINANCE_RESEARCH_URL, wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(1500)

        ask_box = page.get_by_placeholder(re.compile(r"Ask", re.I))
        ask_box.click()
        page.keyboard.type(query, delay=10)
        page.keyboard.press("Enter")

        page.wait_for_selector("role=listitem", timeout=timeout_ms)

        prev_count = 0
        stable_rounds = 0
        deadline = time.time() + 30
        while time.time() < deadline:
            count = page.get_by_role("listitem").count()
            if count and count == prev_count:
                stable_rounds += 1
                if stable_rounds >= 3:
                    break
            else:
                stable_rounds = 0
                prev_count = count
            time.sleep(1)

        raw_items = page.get_by_role("listitem").all_inner_texts()
        events = [clean_event_line(item) for item in raw_items if clean_event_line(item)]
        browser.close()

        if not events:
            raise PlaywrightTimeout(f"No events returned for {symbol.upper()}")

        return events


def fetch_all_stock_events(symbols, headless=False):
    print("B. Fetching stock events via Google Finance Research...", flush=True)

    rows = []
    for symbol in symbols:
        try:
            events = fetch_stock_events(symbol, headless=headless)
            for event in events:
                rows.append({"Symbol": symbol.upper(), "Event": event})
            print(f"   {symbol.upper()}: {len(events)} event(s)", flush=True)
        except Exception as exc:
            print(f"   {symbol.upper()}: failed — {exc}", flush=True)
            rows.append({"Symbol": symbol.upper(), "Event": f"Error: {exc}"})

    df = pd.DataFrame(rows)
    df.to_csv(EVENTS_CSV, index=False)
    print(f"   Saved events to {EVENTS_CSV}", flush=True)
    return df


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Fetch Nifty/Sensex prices and upcoming stock events."
    )
    parser.add_argument(
        "symbols",
        nargs="*",
        default=["INFY"],
        help="Stock symbol(s) for events, e.g. INFY TCS (default: INFY)",
    )
    parser.add_argument("--headless", action="store_true", help="Run browser without UI")
    args = parser.parse_args()

    print("1. Starting ScrapperMon...", flush=True)

    indices_df = fetch_index_prices()
    events_df = fetch_all_stock_events(args.symbols, headless=args.headless)

    print("\n2. Index prices:", flush=True)
    print(indices_df.to_string(index=False), flush=True)

    print("\n3. Stock events:", flush=True)
    for symbol in args.symbols:
        symbol_events = events_df[events_df["Symbol"] == symbol.upper()]["Event"].tolist()
        print(f"\n{symbol.upper()}:", flush=True)
        for event in symbol_events:
            print(f"  - {event}", flush=True)

    print(f"\n4. Done — saved {INDICES_CSV} and {EVENTS_CSV}", flush=True)


if __name__ == "__main__":
    main()

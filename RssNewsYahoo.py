"""
Fetch Indian market news from Yahoo Finance RSS feeds (local script only).

Uses HTTP + RSS parsing — no browser / Playwright.

Usage:
    python RssNewsYahoo.py "Nifty 50"
    python RssNewsYahoo.py india
    python RssNewsYahoo.py Sensex --limit 5 --json

Requires:
    pip install requests
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}
YAHOO_RSS_URL = (
    "https://feeds.finance.yahoo.com/rss/2.0/headline"
    "?s={symbol}&region=US&lang=en-US"
)
CONNECT_TIMEOUT = 15
DEFAULT_LIMIT = 10

# Display name -> Yahoo Finance symbol for RSS
INDEX_SYMBOLS: dict[str, str] = {
    "nifty": "^NSEI",
    "nifty50": "^NSEI",
    "nifty 50": "^NSEI",
    "nifty_50": "^NSEI",
    "sensex": "^BSESN",
    "bse sensex": "^BSESN",
    "banknifty": "^NSEBANK",
    "nifty bank": "^NSEBANK",
    "niftybank": "^NSEBANK",
    "nifty it": "^CNXIT",
    "niftyit": "^CNXIT",
    "nifty metal": "^CNXMETAL",
    "nifty auto": "^CNXAUTO",
    "nifty pharma": "^CNXPHARMA",
    "nifty energy": "^CNXENERGY",
    "infy": "INFY.NS",
    "infosys": "INFY.NS",
    "tcs": "TCS.NS",
    "reliance": "RELIANCE.NS",
    "hdfcbank": "HDFCBANK.NS",
    "hdfc bank": "HDFCBANK.NS",
}

# Symbols merged when user asks for broad Indian market news
INDIA_MARKET_SYMBOLS = (
    "^NSEI",
    "^BSESN",
    "^NSEBANK",
    "INFY.NS",
    "TCS.NS",
    "RELIANCE.NS",
    "HDFCBANK.NS",
)


def normalize_topic(topic: str) -> str:
    return topic.strip().lower()


def resolve_symbols(topic: str) -> tuple[str, list[str]]:
    """Return label + Yahoo symbols to fetch for a topic."""
    key = normalize_topic(topic)
    if key in {"india", "indian market", "market", "all"}:
        return "Indian market", list(INDIA_MARKET_SYMBOLS)
    if key in INDEX_SYMBOLS:
        symbol = INDEX_SYMBOLS[key]
        label = topic.strip()
        for name, sym in INDEX_SYMBOLS.items():
            if sym == symbol and " " in name:
                label = name.title() if name != "nifty 50" else "Nifty 50"
        return label, [symbol]
    # Allow raw Yahoo symbol e.g. ^NSEI or INFY.NS
    if topic.strip().startswith("^") or topic.strip().endswith(".NS"):
        return topic.strip(), [topic.strip()]
    return topic.strip(), [topic.strip()]


def _parse_pub_date(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError, OverflowError):
        return raw.strip()


def fetch_yahoo_rss(symbol: str) -> list[dict[str, str | None]]:
    """Download and parse one Yahoo Finance headline RSS feed."""
    url = YAHOO_RSS_URL.format(symbol=quote(symbol, safe=""))
    response = requests.get(url, headers=HEADERS, timeout=CONNECT_TIMEOUT)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    items: list[dict[str, str | None]] = []
    for node in root.findall(".//item"):
        title = (node.findtext("title") or "").strip()
        if not title:
            continue
        items.append(
            {
                "title": title,
                "link": (node.findtext("link") or "").strip() or None,
                "published": _parse_pub_date(node.findtext("pubDate")),
                "summary": (node.findtext("description") or "").strip() or None,
                "source_symbol": symbol,
            }
        )
    return items


def fetch_market_news(
    topic: str,
    *,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, Any]:
    """Fetch news for an index/topic; merge and dedupe across RSS feeds."""
    label, symbols = resolve_symbols(topic)
    merged: list[dict[str, str | None]] = []
    seen: set[str] = set()
    feeds_ok = 0

    for symbol in symbols:
        try:
            items = fetch_yahoo_rss(symbol)
            feeds_ok += 1
            for item in items:
                key = (item.get("title") or "").lower()
                if key and key not in seen:
                    seen.add(key)
                    merged.append(item)
        except requests.RequestException as exc:
            print(f"   Skipped {symbol}: {exc}", flush=True)

    if feeds_ok == 0:
        raise RuntimeError(f"No RSS feeds could be fetched for {label}")

    merged.sort(key=lambda x: x.get("published") or "", reverse=True)
    headlines = merged[:limit]

    return {
        "topic": label,
        "symbols": symbols,
        "feeds_fetched": feeds_ok,
        "count": len(headlines),
        "news": headlines,
    }


def format_bullet(item: dict[str, str | None]) -> str:
    title = item.get("title") or ""
    published = item.get("published")
    if published:
        return f"{title} ({published})"
    return title


def print_news(result: dict[str, Any]) -> None:
    print(f"\nNews for {result['topic']}:\n", flush=True)
    for item in result["news"]:
        print(f"- {format_bullet(item)}", flush=True)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Fetch Indian market news from Yahoo Finance RSS."
    )
    parser.add_argument(
        "topic",
        nargs="?",
        default="india",
        help='Topic: india, "Nifty 50", Sensex, INFY, ^NSEI, etc. (default: india)',
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Max headlines to return (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    parser.add_argument("--out", metavar="FILE", help="Save JSON to file")
    args = parser.parse_args(argv)

    print(f"1. Fetching Yahoo RSS for {args.topic!r}...", flush=True)
    try:
        result = fetch_market_news(args.topic, limit=max(1, args.limit))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_news(result)

    step = 2
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)
        print(f"\n{step}. Saved to {args.out}", flush=True)
        step += 1

    print(
        f"\n{step}. Done — {result['count']} headline(s) "
        f"from {result['feeds_fetched']} feed(s)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

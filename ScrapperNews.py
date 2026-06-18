"""
Fetch latest index news via Google Finance Research (AI).

Headless browser only — suitable for CLI, Azure Functions, and AWS Lambda.

Usage:
    python ScrapperNews.py "Nifty 50"
    python ScrapperNews.py Sensex --json

Requires:
    pip install playwright
    python -m playwright install chromium
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from typing import Any

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
FINANCE_RESEARCH_URL = "https://www.google.com/finance/beta/#research"
DEFAULT_TIMEOUT_MS = 120_000
CHROMIUM_ARGS = ["--no-sandbox", "--disable-setuid-sandbox"]
# If Google starts blocking headless sessions, also try adding:
# "--disable-blink-features=AutomationControlled"

# Friendly names -> canonical label used in the Research prompt
INDEX_ALIASES: dict[str, str] = {
    "nifty": "Nifty 50",
    "nifty50": "Nifty 50",
    "nifty 50": "Nifty 50",
    "nifty_50": "Nifty 50",
    "sensex": "Sensex",
    "bse sensex": "Sensex",
    "banknifty": "Nifty Bank",
    "nifty bank": "Nifty Bank",
    "niftybank": "Nifty Bank",
    "nifty it": "Nifty IT",
    "niftyit": "Nifty IT",
    "nifty metal": "Nifty Metal",
    "nifty auto": "Nifty Auto",
    "nifty energy": "Nifty Energy",
    "nifty pharma": "Nifty Pharma",
    "nifty midcap": "Nifty Midcap 150",
    "midcap": "Nifty Midcap 150",
}

NEWS_QUERY_TEMPLATE = (
    "Latest market news for the {index} index (India). "
    "Return ONLY a bullet list (maximum 8 bullets). "
    "Each bullet must be one concrete headline; include the date when known. "
    "Cover only: index price moves, RBI/policy, earnings, sector drivers, and macro events. "
    "Do not add an introduction, conclusion, analysis paragraph, sources list, "
    "or follow-up questions."
)

SKIP_LINE_PATTERNS = (
    r"^link$",
    r"^sources?$",
    r"^show all$",
    r"^learn more$",
    r"^ask a follow-up",
    r"^thumb (up|down)$",
    r"^deep search$",
)


def normalize_index(index: str) -> str:
    key = index.strip().lower()
    if key in INDEX_ALIASES:
        return INDEX_ALIASES[key]
    return index.strip()


def build_news_query(index: str) -> str:
    return NEWS_QUERY_TEMPLATE.format(index=normalize_index(index))


def clean_bullet(text: str) -> str:
    line = text.strip()
    line = re.sub(r"\s*link\s*$", "", line, flags=re.IGNORECASE)
    line = re.sub(r"^[\-\*\u2022\d\.\)]+\s*", "", line)
    return line.strip()


def is_valid_bullet(text: str) -> bool:
    if not text or len(text) < 12:
        return False
    lowered = text.lower()
    return not any(re.match(pat, lowered) for pat in SKIP_LINE_PATTERNS)


def parse_bullets_from_text(text: str) -> list[str]:
    bullets: list[str] = []
    for raw_line in text.splitlines():
        cleaned = clean_bullet(raw_line)
        if is_valid_bullet(cleaned):
            bullets.append(cleaned)
    return bullets


def dedupe_bullets(bullets: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in bullets:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def wait_for_stable_listitems(page, timeout_ms: int) -> None:
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


def extract_listitem_bullets(page) -> list[str]:
    raw_items = page.get_by_role("listitem").all_inner_texts()
    bullets = [clean_bullet(item) for item in raw_items]
    return [b for b in bullets if is_valid_bullet(b)]


def extract_fallback_bullets(page, query: str) -> list[str]:
    """Fallback when Research returns paragraphs instead of HTML list items."""
    headings = page.locator("h3").all_inner_texts()
    if not headings:
        return []
    panel_text = page.locator("h3").last.locator("xpath=..").inner_text(timeout=5000)
    panel_text = panel_text.replace(query, "")
    return parse_bullets_from_text(panel_text)


def fetch_index_news(
    index: str,
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> dict[str, Any]:
    """
    Query Google Finance Research for index news (headless Chromium).

    Returns:
        {"index": str, "query": str, "news": list[str]}
    """
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright

    canonical_index = normalize_index(index)
    query = build_news_query(index)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=CHROMIUM_ARGS)
        page = browser.new_page(
            viewport={"width": 1400, "height": 900},
            user_agent=USER_AGENT,
        )

        page.goto(FINANCE_RESEARCH_URL, wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(1500)

        ask_box = page.get_by_placeholder(re.compile(r"Ask", re.I))
        ask_box.click()
        page.keyboard.type(query, delay=10)
        page.keyboard.press("Enter")

        bullets: list[str] = []
        try:
            wait_for_stable_listitems(page, timeout_ms)
            bullets = extract_listitem_bullets(page)
        except PlaywrightTimeout:
            bullets = []

        if not bullets:
            bullets = extract_fallback_bullets(page, query)

        browser.close()

    bullets = dedupe_bullets(bullets)
    if not bullets:
        raise PlaywrightTimeout(f"No news bullets returned for {canonical_index}")

    return {
        "index": canonical_index,
        "query": query,
        "news": bullets,
    }


def print_news(result: dict[str, Any]) -> None:
    print(f"\nNews for {result['index']}:\n", flush=True)
    for item in result["news"]:
        print(f"- {item}", flush=True)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Fetch latest index news from Google Finance Research."
    )
    parser.add_argument(
        "index",
        help='Index name, e.g. "Nifty 50", Sensex, "Nifty Bank"',
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON instead of bullet list",
    )
    parser.add_argument(
        "--out",
        metavar="FILE",
        help="Optional path to save JSON output",
    )
    args = parser.parse_args(argv)

    print(f"1. Fetching news for {normalize_index(args.index)}...", flush=True)
    try:
        result = fetch_index_news(args.index)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        payload = json.dumps(result, indent=2, ensure_ascii=False)
        print(payload)
    else:
        print_news(result)

    step = 2
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, ensure_ascii=False)
        print(f"\n{step}. Saved to {args.out}", flush=True)
        step += 1

    print(f"\n{step}. Done — {len(result['news'])} headline(s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

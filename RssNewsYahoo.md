# RssNewsYahoo

Fetch **Indian market news** from **Yahoo Finance RSS** feeds. Local script only — no Playwright, no browser, no cloud deployment.

Designed as a fast, lightweight alternative to `ScrapperNews.py` (Google Finance AI).

---

## Overview

| Item | Detail |
|------|--------|
| **Script** | `RssNewsYahoo.py` |
| **Data source** | [Yahoo Finance RSS headlines](https://feeds.finance.yahoo.com/rss/2.0/headline) |
| **Method** | `requests` + Python `xml.etree` (stdlib) |
| **Input** | Topic: `india`, `Nifty 50`, `Sensex`, stock symbol, etc. |
| **Output** | Bullet headlines (title + date), optional JSON |
| **Runtime** | ~5–15 seconds (HTTP only) |
| **Dependencies** | `requests` only |

---

## How it works

```
You pass topic (e.g. india, Nifty 50)
        │
        ▼
Resolve topic → Yahoo symbol(s)  (^NSEI, INFY.NS, …)
        │
        ▼
GET Yahoo RSS URL for each symbol
        │
        ▼
Parse XML <item> entries (title, link, pubDate, description)
        │
        ▼
Merge feeds → dedupe by title → sort by date → apply --limit
        │
        ▼
Print bullets or JSON
```

---

## Installation

```powershell
cd "C:\WORK\TEST WEB LOADER\WebScrapper"
pip install -r requirements-rss.txt
```

### requirements-rss.txt

```
requests>=2.28.0
```

No Playwright. No Chromium.

---

## CLI usage

```powershell
python RssNewsYahoo.py india
python RssNewsYahoo.py "Nifty 50"
python RssNewsYahoo.py Sensex --limit 5
python RssNewsYahoo.py TCS --json
python RssNewsYahoo.py india --limit 25 --out india_news.json
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `topic` | `india` | Index, stock, or market preset |
| `--limit` | `10` | Max headlines to return (no hard cap in code) |
| `--json` | off | Print JSON instead of bullets |
| `--out FILE` | — | Save JSON to file |

### How many bullet points?

| Setting | Result |
|---------|--------|
| Default | Up to **10** headlines |
| `--limit N` | Up to **N** headlines (any integer ≥ 1) |
| Actual count | May be **less** — Yahoo decides how many `<item>` entries each feed returns (often 0–20 per symbol) |

**Examples from local tests:**

| Command | Result |
|---------|--------|
| `Nifty 50` | 4 headlines (feed had only 4 items) |
| `india --limit 8` | 8 headlines from 7 feeds |

---

## Supported topics

| You pass | Yahoo symbol(s) | Label |
|----------|-----------------|-------|
| `india`, `market`, `all` | 7 symbols (see below) | Indian market |
| `nifty`, `nifty 50` | `^NSEI` | Nifty 50 |
| `sensex` | `^BSESN` | Sensex |
| `banknifty`, `nifty bank` | `^NSEBANK` | Nifty Bank |
| `nifty it`, `nifty metal`, etc. | `^CNXIT`, `^CNXMETAL`, … | Sector indices |
| `infy`, `tcs`, `reliance`, `hdfcbank` | `INFY.NS`, `TCS.NS`, … | NSE stocks |
| `^NSEI`, `INFY.NS` | As given | Raw Yahoo symbol |

### `india` preset merges these 7 feeds

```
^NSEI        Nifty 50
^BSESN       Sensex
^NSEBANK     Nifty Bank
INFY.NS      Infosys
TCS.NS       TCS
RELIANCE.NS  Reliance
HDFCBANK.NS  HDFC Bank
```

---

## Output format

### Console (default)

```
1. Fetching Yahoo RSS for 'Nifty 50'...

News for Nifty 50:

- India might be the 'perfect' emerging market, strategist says (2025-10-01 18:30 UTC)
- Analysts' top emerging market fund and trust picks (2025-08-15 05:00 UTC)
...

2. Done — 4 headline(s) from 1 feed(s)
```

### JSON

```json
{
  "topic": "Nifty 50",
  "symbols": ["^NSEI"],
  "feeds_fetched": 1,
  "count": 4,
  "news": [
    {
      "title": "India might be the 'perfect' emerging market, strategist says",
      "link": "https://finance.yahoo.com/video/india-might-perfect-emerging-market-183000557.html?.tsrc=rss",
      "published": "2025-10-01 18:30 UTC",
      "summary": "EMQQ Global founder ...",
      "source_symbol": "^NSEI"
    }
  ]
}
```

---

## Python API

```python
from RssNewsYahoo import fetch_market_news, fetch_yahoo_rss

# Full topic fetch (merge + dedupe)
result = fetch_market_news("india", limit=10)
for item in result["news"]:
    print(item["title"], item["published"])

# Single symbol RSS feed
items = fetch_yahoo_rss("^NSEI")
```

### `fetch_market_news()` return value

```python
{
    "topic": str,
    "symbols": list[str],
    "feeds_fetched": int,
    "count": int,
    "news": [
        {
            "title": str,
            "link": str | None,
            "published": str | None,
            "summary": str | None,
            "source_symbol": str,
        }
    ],
}
```

---

## HTTP: what we send to Yahoo

Example for **Nifty 50** (`^NSEI`):

### Request

**Method:** `GET`

**URL:**
```
https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5ENSEI&region=US&lang=en-US
```

| Query param | Value | Meaning |
|-------------|-------|---------|
| `s` | `%5ENSEI` | URL-encoded `^NSEI` (Yahoo symbol) |
| `region` | `US` | Region (works better for index feeds than `IN`) |
| `lang` | `en-US` | Language |

**Headers sent:**

```http
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
Accept: application/rss+xml, application/xml, text/xml, */*
```

- No request body (GET only)
- No cookies
- **User-Agent** avoids the default `python-requests/x.x` string that some servers block

---

## HTTP: what Yahoo returns

### Response status

```
200 OK
```

### Key response headers

```http
content-type: application/xml
cache-control: public, max-age=300, stale-while-revalidate=75
content-encoding: gzip
server: ATS
```

Real **RSS XML** — not HTML, not a bot-check page.

### Response body (RSS 2.0 structure)

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<rss version="2.0">
    <channel>
        <title>Yahoo! Finance: ^NSEI News</title>
        <description>Latest Financial News for ^NSEI</description>
        <link>http://finance.yahoo.com/q/h?s=^NSEI</link>
        <lastBuildDate>Fri, 19 Jun 2026 12:10:42 +0000</lastBuildDate>

        <item>
            <title>Trending tickers: Datavault, Novo Nordisk, FedEx, SBI and NatWest</title>
            <link>https://uk.finance.yahoo.com/news/...html?.tsrc=rss</link>
            <pubDate>Mon, 09 Feb 2026 09:20:18 +0000</pubDate>
            <description>The latest investor updates on stocks that are trending on Monday</description>
            <guid isPermaLink="false">6825959b-a086-4ff8-b165-2d54ec82bba8</guid>
        </item>

        <item>
            <title>India might be the 'perfect' emerging market, strategist says</title>
            <link>https://finance.yahoo.com/video/...html?.tsrc=rss</link>
            <pubDate>Wed, 01 Oct 2025 18:30:00 +0000</pubDate>
            <description>EMQQ Global founder ... India (^NSEI)...</description>
        </item>

        <!-- more <item> elements ... -->
    </channel>
</rss>
```

### How each `<item>` becomes a bullet

| XML field | Parsed to | Printed as |
|-----------|-----------|------------|
| `<title>` | `title` | Headline text |
| `<pubDate>` | `published` | `YYYY-MM-DD HH:MM UTC` |
| `<link>` | `link` | In JSON only |
| `<description>` | `summary` | In JSON only |

**Bullet example:**
```
- India might be the 'perfect' emerging market, strategist says (2025-10-01 18:30 UTC)
```

---

## Yahoo RSS vs Google Finance (ScrapperNews)

| | RssNewsYahoo | ScrapperNews |
|--|--------------|--------------|
| **Source** | Yahoo RSS XML | Google Finance Research AI |
| **Tool** | `requests` | Playwright (headless Chromium) |
| **Speed** | ~5–15 s | ~25–40 s |
| **Cloud** | Not needed | Container + Chromium for Azure/Lambda |
| **Headlines** | Raw Yahoo articles | AI-curated summaries |
| **Blocking risk** | Low (RSS is public) | Low–medium |
| **Items per run** | 0–20 per feed (Yahoo decides) | Up to 8 (prompt limit) |

Use **RssNewsYahoo** for fast free headlines. Use **ScrapperNews** when you want AI-written market summaries.

---

## Project files

```
WebScrapper/
├── RssNewsYahoo.py       # Main script
├── RssNewsYahoo.md       # This file
├── requirements-rss.txt  # requests only
├── ScrapperNews.py       # Google Finance AI (separate)
└── ScrapperNews.md
```

---

## Limitations

| Topic | Notes |
|-------|-------|
| **Feed freshness** | Yahoo may return older headlines; not always “today only” |
| **Empty feeds** | Some symbols return 0 items (e.g. `^NSEI` with `region=IN`) — script uses `region=US` |
| **Not official API** | Public RSS; format/availability can change |
| **Rate limits** | Heavy polling may get throttled — cache results if calling often |
| **India-only filter** | `india` preset uses Indian symbols but headlines can mention global names |
| **No cloud middleware** | Local CLI only (by design) |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `No module named requests` | `pip install -r requirements-rss.txt` |
| `No RSS feeds could be fetched` | Check internet; retry; verify symbol |
| Fewer bullets than `--limit` | Normal — Yahoo returned fewer `<item>` entries |
| `Skipped ^SYMBOL: ...` | That feed failed; others still merge if any succeed |
| 403 / 429 errors | Add delay between feeds; avoid rapid repeated calls |

### If Yahoo starts blocking

Headers already include User-Agent. If blocked later, try adding:

```python
"Accept-Language": "en-US,en;q=0.9",
```

and a short `time.sleep(0.5)` between feeds in the `india` preset loop.

---

## Example session

```powershell
python RssNewsYahoo.py india --limit 8
```

```
1. Fetching Yahoo RSS for 'india'...

News for Indian market:

- Infosys (NSEI:INFY) Stock Sees Split Analyst Revisions... (2026-06-19 10:10 UTC)
- India's Nifty IT index at three-year low... (2026-06-19 03:57 UTC)
- Accenture Shares Sink 20% After Revenue Outlook Misses... (2026-06-18 18:00 UTC)
...

2. Done — 8 headline(s) from 7 feed(s)
```

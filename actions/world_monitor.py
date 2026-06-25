"""
world_monitor — Real-time global intelligence for J.A.R.V.I.S.

Integrates the curated RSS sources from the worldmonitor project
(https://github.com/koala73/worldmonitor) into Jarvis: pulls live headlines
across geopolitical / regional / finance / defense categories, optionally
AI-synthesizes a spoken brief, and feeds the HUD "WORLD MONITOR" tab.

Usable two ways:
  - get_headlines(category, limit)      -> list[dict] (for the HUD, no AI)
  - world_monitor(parameters, ...)      -> str brief (for the voice tool)
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import feedparser

try:
    import requests
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


# --- Curated feed set, mirroring worldmonitor's FULL_FEEDS / INTEL_SOURCES ---
# Direct RSS URLs (no proxy). Kept to reliable, mostly-English high-tier sources.
WORLD_FEEDS = {
    "world": [
        ("BBC World",     "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("Guardian World","https://www.theguardian.com/world/rss"),
        ("Al Jazeera",    "https://www.aljazeera.com/xml/rss/all.xml"),
        ("Reuters World", "https://news.google.com/rss/search?q=site:reuters.com+world&hl=en-US&gl=US&ceid=US:en"),
        ("AP News",       "https://news.google.com/rss/search?q=site:apnews.com&hl=en-US&gl=US&ceid=US:en"),
        ("UN News",       "https://news.un.org/feed/subscribe/en/news/all/rss.xml"),
    ],
    "us": [
        ("NPR News",   "https://feeds.npr.org/1001/rss.xml"),
        ("PBS NewsHour","https://www.pbs.org/newshour/feeds/rss/headlines"),
        ("NBC News",   "https://feeds.nbcnews.com/nbcnews/public/news"),
        ("Politico",   "https://rss.politico.com/politics-news.xml"),
        ("The Hill",   "https://thehill.com/news/feed"),
    ],
    "europe": [
        ("Euronews",  "https://www.euronews.com/rss?format=xml"),
        ("DW News",   "https://rss.dw.com/xml/rss-en-all"),
        ("France 24", "https://www.france24.com/en/rss"),
        ("BBC Europe","https://feeds.bbci.co.uk/news/world/europe/rss.xml"),
    ],
    "middleeast": [
        ("BBC Middle East","https://feeds.bbci.co.uk/news/world/middle_east/rss.xml"),
        ("Al Jazeera ME",  "https://www.aljazeera.com/xml/rss/all.xml"),
        ("Times of Israel","https://www.timesofisrael.com/feed/"),
    ],
    "asia": [
        ("NHK World",   "https://www3.nhk.or.jp/nhkworld/en/news/rss/c_all.xml"),
        ("BBC Asia",    "https://feeds.bbci.co.uk/news/world/asia/rss.xml"),
        ("Nikkei Asia", "https://news.google.com/rss/search?q=site:asia.nikkei.com+when:1d&hl=en-US&gl=US&ceid=US:en"),
        ("South China Morning Post","https://www.scmp.com/rss/91/feed"),
    ],
    "africa": [
        ("BBC Africa",  "https://feeds.bbci.co.uk/news/world/africa/rss.xml"),
        ("AllAfrica",   "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf"),
    ],
    "latam": [
        ("BBC Latin America","https://feeds.bbci.co.uk/news/world/latin_america/rss.xml"),
        ("MercoPress",       "https://en.mercopress.com/rss/"),
    ],
    "tech": [
        ("The Verge",   "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica","https://feeds.arstechnica.com/arstechnica/index"),
        ("TechCrunch",  "https://techcrunch.com/feed/"),
        ("Hacker News", "https://hnrss.org/frontpage"),
    ],
    "ai": [
        ("Google News AI","https://news.google.com/rss/search?q=artificial+intelligence+when:1d&hl=en-US&gl=US&ceid=US:en"),
        ("VentureBeat AI","https://venturebeat.com/category/ai/feed/"),
        ("MIT Tech Review","https://www.technologyreview.com/feed/"),
    ],
    "finance": [
        ("CNBC",        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
        ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/"),
        ("FT",          "https://news.google.com/rss/search?q=site:ft.com+when:1d&hl=en-US&gl=US&ceid=US:en"),
        ("Yahoo Finance","https://finance.yahoo.com/news/rssindex"),
    ],
    "energy": [
        ("OilPrice",    "https://oilprice.com/rss/main"),
        ("Reuters Energy","https://news.google.com/rss/search?q=energy+oil+gas+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ],
    "defense": [
        ("Defense One",   "https://www.defenseone.com/rss/all/"),
        ("The War Zone",  "https://www.twz.com/feed"),
        ("Defense News",  "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml"),
        ("Task & Purpose","https://taskandpurpose.com/feed/"),
        ("UK MOD",        "https://www.gov.uk/government/organisations/ministry-of-defence.atom"),
    ],
    "crisis": [
        ("ReliefWeb",   "https://reliefweb.int/updates/rss.xml"),
        ("CrisisWatch", "https://news.google.com/rss/search?q=site:crisisgroup.org+when:3d&hl=en-US&gl=US&ceid=US:en"),
    ],
}

# Friendly aliases so voice commands map to a category.
CATEGORY_ALIASES = {
    "global": "world", "news": "world", "headlines": "world", "geopolitics": "world",
    "america": "us", "usa": "us", "united states": "us",
    "mideast": "middleeast", "middle east": "middleeast", "gulf": "middleeast",
    "technology": "tech",
    "artificial intelligence": "ai",
    "markets": "finance", "stocks": "finance", "economy": "finance",
    "military": "defense", "war": "defense", "intel": "defense", "intelligence": "defense",
    "disaster": "crisis", "humanitarian": "crisis",
}

CATEGORIES = list(WORLD_FEEDS.keys())
_UA = {"User-Agent": "Mozilla/5.0 (JARVIS WorldMonitor)"}


def _resolve_category(cat: str) -> str:
    if not cat:
        return "world"
    c = cat.strip().lower()
    if c in WORLD_FEEDS:
        return c
    return CATEGORY_ALIASES.get(c, "world")


def _fetch_feed(name: str, url: str, per_feed: int = 5):
    items = []
    try:
        if _HAS_REQUESTS:
            resp = requests.get(url, headers=_UA, timeout=8)
            parsed = feedparser.parse(resp.content)
        else:
            parsed = feedparser.parse(url)
        for e in parsed.entries[:per_feed]:
            title = (getattr(e, "title", "") or "").strip()
            if not title:
                continue
            ts = 0
            for attr in ("published_parsed", "updated_parsed"):
                tp = getattr(e, attr, None)
                if tp:
                    ts = time.mktime(tp)
                    break
            items.append({
                "source": name,
                "title": title,
                "link": getattr(e, "link", ""),
                "ts": ts,
            })
    except Exception:
        pass
    return items


def get_headlines(category: str = "world", limit: int = 10) -> list:
    """Fetch + merge headlines for a category. No AI. Used by HUD and the tool."""
    cat = _resolve_category(category)
    feeds = WORLD_FEEDS.get(cat, WORLD_FEEDS["world"])
    all_items = []
    with ThreadPoolExecutor(max_workers=min(8, len(feeds))) as ex:
        futs = {ex.submit(_fetch_feed, n, u): n for n, u in feeds}
        for f in as_completed(futs):
            all_items.extend(f.result())

    # Dedupe by lowercased title, newest first.
    seen, deduped = set(), []
    for it in sorted(all_items, key=lambda x: x["ts"], reverse=True):
        k = it["title"].lower()[:80]
        if k in seen:
            continue
        seen.add(k)
        deduped.append(it)
    return deduped[:limit]


def _synthesize_brief(category: str, items: list) -> str:
    """AI-synthesize a short spoken brief. Falls back to a plain list."""
    headlines = "\n".join(f"- [{it['source']}] {it['title']}" for it in items)
    if not headlines:
        return f"Sir, I couldn't pull any fresh {category} headlines right now."
    try:
        cfg = _base_dir() / "config" / "api_keys.json"
        key = json.loads(cfg.read_text(encoding="utf-8")).get("gemini_api_key")
        if not key:
            raise RuntimeError("no key")
        from google import genai
        client = genai.Client(api_key=key)
        prompt = (
            f"You are JARVIS giving Sir a concise spoken {category} intelligence brief. "
            f"From these live headlines, synthesize the 4-6 most important developments into a "
            f"natural, spoken-style brief (no markdown, no bullet symbols, no links). "
            f"Keep it crisp and under 130 words. Start with 'Here is your {category} brief, Sir.'\n\n"
            f"Headlines:\n{headlines}"
        )
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return (r.text or "").strip() or headlines
    except Exception:
        # No AI available — return a plain readable list.
        lines = [f"Here are the latest {category} headlines, Sir:"]
        lines += [f"{i+1}. {it['title']} ({it['source']})" for i, it in enumerate(items[:6])]
        return "\n".join(lines)


def get_weather(city: str = "Islamabad") -> dict:
    """Quick weather via wttr.in (no API key). Returns {} on failure."""
    if not _HAS_REQUESTS:
        return {}
    try:
        r = requests.get(
            f"https://wttr.in/{city}?format=j1", headers=_UA, timeout=14
        )
        data = r.json()
        cur = data["current_condition"][0]
        return {
            "city": city,
            "temp_c": cur.get("temp_C"),
            "feels_c": cur.get("FeelsLikeC"),
            "desc": (cur.get("weatherDesc", [{}])[0].get("value", "")).strip(),
            "humidity": cur.get("humidity"),
            "wind_kph": cur.get("windspeedKmph"),
        }
    except Exception:
        return {}


def get_situation_brief() -> str:
    """Forward-looking world situation + 'what happens next' outlook (AI)."""
    items = get_headlines("world", 16)
    if not items:
        return "Global situation feed unavailable right now, Sir."
    headlines = "\n".join(f"- {it['title']}" for it in items)
    try:
        cfg = _base_dir() / "config" / "api_keys.json"
        key = json.loads(cfg.read_text(encoding="utf-8")).get("gemini_api_key")
        from google import genai
        client = genai.Client(api_key=key)
        prompt = (
            "You are JARVIS giving Sir a situational-awareness read of the world. "
            "From these live headlines, write a tight 3-sentence assessment of the current "
            "global situation, then 2 sentences on what is likely to develop next (the outlook). "
            "Plain spoken text, no markdown, under 110 words.\n\n" + headlines
        )
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return (r.text or "").strip() or headlines
    except Exception:
        return "Top developments: " + "; ".join(it["title"] for it in items[:4])


def world_monitor(parameters: dict = None, player=None, speak=None, **kwargs) -> str:
    """Voice tool entrypoint. parameters: {category, limit, brief}."""
    parameters = parameters or {}
    category = _resolve_category(parameters.get("category", "world"))
    limit = int(parameters.get("limit", 10) or 10)
    want_brief = parameters.get("brief", True)

    if player is not None:
        try:
            player.write_log(f"WORLD MONITOR: Pulling live {category} intelligence...")
        except Exception:
            pass

    items = get_headlines(category, limit)

    # Push to the HUD tab if the UI exposes the hook.
    if player is not None:
        for hook in ("update_world_monitor", "set_world_headlines"):
            fn = getattr(player, hook, None)
            if callable(fn):
                try:
                    fn(category, items)
                except Exception:
                    pass
                break

    if want_brief:
        return _synthesize_brief(category, items)
    if not items:
        return f"Sir, no fresh {category} headlines available right now."
    return "\n".join(f"{i+1}. {it['title']} ({it['source']})" for i, it in enumerate(items))


if __name__ == "__main__":
    cat = sys.argv[1] if len(sys.argv) > 1 else "world"
    print(world_monitor({"category": cat, "brief": False}))

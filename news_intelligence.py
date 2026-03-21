"""
News Intelligence — fetches top market news and uses Claude AI
to identify which stocks to watch or avoid based on current events.
"""

import yfinance as yf
import requests
import json
from datetime import datetime, timedelta


# ── Sector/theme → ticker mapping ─────────────────────────────────────────
THEME_TICKERS = {
    "oil": ["XOM", "CVX", "COP", "SLB", "HAL", "PSX", "VLO", "MPC", "OVV", "DVN"],
    "gas": ["LNG", "AR", "EQT", "COP", "OKE", "WMB", "KMI"],
    "solar": ["ENPH", "SEDG", "FSLR", "RUN", "SPWR"],
    "crypto": ["COIN", "MSTR", "HOOD", "MARA", "RIOT", "HUT", "WULF"],
    "bitcoin": ["COIN", "MSTR", "HOOD", "MARA", "RIOT", "HUT"],
    "defense": ["RTX", "LMT", "NOC", "GD", "ESLT", "AXON", "HEI"],
    "ai": ["NVDA", "AMD", "GOOGL", "PLTR", "NET", "DDOG", "MRVL"],
    "semiconductor": ["AMAT", "LRCX", "KLAC", "MU", "MRVL", "MCHP", "ON"],
    "banking": ["JPM", "BAC", "GS", "MS", "WFC", "C", "BX"],
    "shipping": ["ZIM", "FRO", "SDRL", "NE"],
    "electric_vehicle": ["RIVN", "NIO", "GM", "F"],
    "rates_up": ["BX", "KKR", "GS", "MS", "BFH"],
    "rates_down": ["RIVN", "NIO", "COIN", "MSTR", "HOOD"],
    "geopolitical": ["RTX", "LMT", "NOC", "GD", "ESLT", "XOM", "CVX"],
    "healthcare": ["JNJ", "UNH", "ABBV", "BMY", "MRK"],
    "inflation": ["XOM", "CVX", "NEM", "GOLD", "AA", "CF"],
    "china_tension": ["AMAT", "LRCX", "KLAC", "MRVL", "ASX"],
    "israel_conflict": ["ESLT", "RTX", "LMT", "NOC"],
}


def _get_market_news() -> list[dict]:
    """
    Fetch recent market headlines using yfinance on major tickers.
    Returns list of {title, publisher, published} dicts.
    """
    headlines = []
    seen = set()

    # Pull news from high-profile tickers + market ETFs
    sources = ["SPY", "QQQ", "GLD", "USO", "BTC-USD", "^VIX"]
    for sym in sources:
        try:
            t    = yf.Ticker(sym)
            news = t.news or []
            for item in news[:8]:
                title = (item.get('title') or
                         item.get('content', {}).get('title') or '')
                if not title or title in seen:
                    continue
                seen.add(title)
                pub_time = item.get('providerPublishTime') or 0
                try:
                    pub_str = datetime.fromtimestamp(pub_time).strftime('%b %d %H:%M')
                except Exception:
                    pub_str = ''
                url = (item.get('link') or item.get('url') or
                       item.get('content', {}).get('url') or '')
                headlines.append({
                    'title':     title,
                    'publisher': item.get('publisher', ''),
                    'published': pub_str,
                    'url':       url,
                })
        except Exception:
            pass

    return headlines[:40]


def _call_claude(headlines: list[dict]) -> dict:
    """
    Send headlines to Claude API and get structured analysis.
    Returns {watch: [...], avoid: [...], summary: str}
    """
    headlines_text = "\n".join(
        f"- {h['published']} | {h['title']}" for h in headlines
    )

    prompt = f"""You are a professional stock market analyst. 
Analyze these recent market headlines and identify:
1. Stocks/sectors to WATCH (likely to go up based on news)
2. Stocks/sectors to AVOID (likely to go down or risky)

Headlines:
{headlines_text}

Respond ONLY with valid JSON in this exact format (no markdown, no explanation outside JSON):
{{
  "watch": [
    {{"ticker": "COIN", "reason": "Bitcoin ETF approval drives crypto demand", "confidence": "HIGH", "theme": "crypto"}},
    {{"ticker": "XOM", "reason": "Oil supply cuts expected", "confidence": "MEDIUM", "theme": "oil"}}
  ],
  "avoid": [
    {{"ticker": "RIVN", "reason": "EV demand weakening, rate concerns", "confidence": "HIGH", "theme": "EV"}}
  ],
  "summary": "2-3 sentence market overview based on today's news.",
  "key_themes": ["crypto rally", "oil supply concerns", "rate uncertainty"]
}}

Rules:
- Use real ticker symbols only
- confidence: HIGH / MEDIUM / LOW
- Include 3-8 watch stocks and 2-5 avoid stocks
- Focus on clear cause-and-effect from the news
- If news mentions a sector, include relevant tickers from that sector"""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        if resp.status_code != 200:
            return {}

        data    = resp.json()
        content = data.get('content', [{}])[0].get('text', '')
        # Strip markdown fences if present
        content = content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1].rsplit('```', 1)[0]
        return json.loads(content)

    except Exception:
        return {}


def run_news_intelligence() -> dict:
    """
    Main entry point: fetch news → analyze with Claude → return results.
    Returns {watch, avoid, summary, key_themes, headlines, timestamp}
    """
    headlines = _get_market_news()
    if not headlines:
        return {"error": "Could not fetch market news."}

    analysis = _call_claude(headlines)
    if not analysis:
        return {
            "error": "AI analysis unavailable.",
            "headlines": headlines,
            "timestamp": datetime.now().strftime('%H:%M:%S')
        }

    return {
        "watch":      analysis.get("watch", []),
        "avoid":      analysis.get("avoid", []),
        "summary":    analysis.get("summary", ""),
        "key_themes": analysis.get("key_themes", []),
        "headlines":  headlines,
        "timestamp":  datetime.now().strftime('%H:%M:%S'),
    }

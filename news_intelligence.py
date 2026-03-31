"""
News Intelligence v2:
1. Multi-source news fetching (Yahoo Finance, Google News RSS, Seeking Alpha RSS)
2. VIX spike history analysis — what happened to stocks when VIX > threshold
3. Claude AI analysis of headlines → watch/avoid recommendations
"""

import yfinance as yf
import requests
import json
import re
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


# ── Sector/theme → ticker mapping ────────────────────────────
THEME_TICKERS = {
    "oil":           ["XOM","CVX","COP","SLB","HAL","PSX","VLO","MPC","OVV","DVN"],
    "gas":           ["LNG","AR","EQT","OKE","WMB","KMI"],
    "solar":         ["ENPH","SEDG","FSLR","RUN"],
    "crypto":        ["COIN","MSTR","HOOD","WULF","HUT"],
    "defense":       ["RTX","LMT","NOC","GD","ESLT","AXON","HEI"],
    "ai":            ["NVDA","AMD","GOOGL","PLTR","NET","DDOG","MRVL"],
    "semiconductor": ["AMAT","LRCX","KLAC","MU","MRVL","MCHP"],
    "banking":       ["JPM","BAC","GS","MS","WFC","BX"],
    "shipping":      ["ZIM","FRO","SDRL","NE"],
    "ev":            ["RIVN","NIO","GM"],
    "geopolitical":  ["RTX","LMT","NOC","GD","ESLT","XOM","CVX"],
    "healthcare":    ["UNH","ABBV","BMY","MRK","JNJ"],
    "inflation":     ["XOM","CVX","NEM","GOLD","AA","CF"],
    "rates_up":      ["BX","KKR","GS","MS"],
    "rates_down":    ["RIVN","NIO","COIN","MSTR"],
    "safe_haven":    ["GLD","TLT","VZ","JNJ","PG","KO","WMT"],
}

# Stocks known to be "defensive" (tend to hold up when VIX spikes)
DEFENSIVE_STOCKS = [
    "JNJ","PG","KO","WMT","MCD","VZ","T","SO","DUK","NEE",
    "GLD","SHW","CL","MO","PM","ABBV","BMY","MRK","UNH","CVS",
]

# Stocks that tend to benefit from high VIX (volatility plays)
VIX_BENEFICIARIES = [
    "GLD","TLT","VZ","JNJ","PG","WMT","KO",   # safe havens go UP
]

# Stocks that tend to get crushed when VIX spikes
VIX_LOSERS = [
    "COIN","MSTR","RIVN","NIO","HOOD","WULF","AFRM","UPST","SOFI",  # high-beta risk assets
    "TSLA","NVDA","META","AMZN",
]


# ══════════════════════════════════════════════════════════════
#  1. MULTI-SOURCE NEWS FETCHER
# ══════════════════════════════════════════════════════════════

def _fetch_yahoo_news() -> list:
    """Fetch from Yahoo Finance via yfinance."""
    headlines = []
    seen = set()
    sources = ["SPY","QQQ","GLD","USO","BTC-USD","^VIX","^GSPC","AAPL","NVDA","META"]
    for sym in sources:
        try:
            news = yf.Ticker(sym).news or []
            for item in news[:6]:
                title = (item.get('title') or
                         item.get('content', {}).get('title') or '')
                if not title or title in seen:
                    continue
                seen.add(title)
                pub = item.get('providerPublishTime', 0)
                try:
                    pub_str = datetime.fromtimestamp(pub).strftime('%b %d %H:%M')
                except Exception:
                    pub_str = ''
                url = (item.get('link') or item.get('url') or
                       item.get('content', {}).get('url') or '')
                headlines.append({
                    'title':     title,
                    'publisher': item.get('publisher', 'Yahoo Finance'),
                    'published': pub_str,
                    'url':       url,
                    'source':    'Yahoo Finance',
                })
        except Exception:
            pass
    return headlines


def _fetch_google_news_rss(query: str = "stock market today") -> list:
    """Fetch from Google News RSS feed."""
    headlines = []
    try:
        url = f"https://news.google.com/rss/search?q={query.replace(' ','+')}&hl=en-US&gl=US&ceid=US:en"
        resp = requests.get(url, timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code != 200:
            return []
        # Parse RSS items
        items = re.findall(r'<item>(.*?)</item>', resp.text, re.DOTALL)
        for item in items[:15]:
            title = re.search(r'<title>(.*?)</title>', item)
            link  = re.search(r'<link>(.*?)</link>', item)
            pub   = re.search(r'<pubDate>(.*?)</pubDate>', item)
            if title:
                t = re.sub(r'<[^>]+>', '', title.group(1)).strip()
                if t:
                    headlines.append({
                        'title':     t,
                        'publisher': 'Google News',
                        'published': pub.group(1)[:16] if pub else '',
                        'url':       link.group(1).strip() if link else '',
                        'source':    'Google News',
                    })
    except Exception:
        pass
    return headlines


def _fetch_seeking_alpha_rss() -> list:
    """Fetch from Seeking Alpha market news RSS."""
    headlines = []
    try:
        url = "https://seekingalpha.com/market_currents.xml"
        resp = requests.get(url, timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code != 200:
            return []
        items = re.findall(r'<item>(.*?)</item>', resp.text, re.DOTALL)
        for item in items[:10]:
            title = re.search(r'<title>(.*?)</title>', item)
            link  = re.search(r'<link>(.*?)</link>', item)
            pub   = re.search(r'<pubDate>(.*?)</pubDate>', item)
            if title:
                t = re.sub(r'<[^>]+>|<!\[CDATA\[|\]\]>', '', title.group(1)).strip()
                if t:
                    headlines.append({
                        'title':     t,
                        'publisher': 'Seeking Alpha',
                        'published': pub.group(1)[:16] if pub else '',
                        'url':       link.group(1).strip() if link else '',
                        'source':    'Seeking Alpha',
                    })
    except Exception:
        pass
    return headlines


def _fetch_bizportal_rss() -> list:
    """Fetch from Bizportal (Israeli financial news) RSS."""
    headlines = []
    try:
        url = "https://www.bizportal.co.il/rss/wallstreet"
        resp = requests.get(url, timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code != 200:
            return []
        items = re.findall(r'<item>(.*?)</item>', resp.text, re.DOTALL)
        for item in items[:8]:
            title = re.search(r'<title>(.*?)</title>', item)
            link  = re.search(r'<link>(.*?)</link>', item)
            if title:
                t = re.sub(r'<[^>]+>|<!\[CDATA\[|\]\]>', '', title.group(1)).strip()
                if t:
                    headlines.append({
                        'title':     t,
                        'publisher': 'Bizportal 🇮🇱',
                        'published': '',
                        'url':       link.group(1).strip() if link else '',
                        'source':    'Bizportal',
                    })
    except Exception:
        pass
    return headlines


def _fetch_calcalist_rss() -> list:
    """Fetch from Calcalist RSS."""
    headlines = []
    try:
        url = "https://www.calcalist.co.il/rss/AID-1523266706869"
        resp = requests.get(url, timeout=8, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code != 200:
            return []
        items = re.findall(r'<item>(.*?)</item>', resp.text, re.DOTALL)
        for item in items[:6]:
            title = re.search(r'<title>(.*?)</title>', item)
            link  = re.search(r'<link>(.*?)</link>', item)
            if title:
                t = re.sub(r'<[^>]+>|<!\[CDATA\[|\]\]>', '', title.group(1)).strip()
                if t:
                    headlines.append({
                        'title':     t,
                        'publisher': 'Calcalist IL 🇮🇱',
                        'published': '',
                        'url':       link.group(1).strip() if link else '',
                        'source':    'Calcalist',
                    })
    except Exception:
        pass
    return headlines


def fetch_all_news() -> list:
    """Aggregate news from all sources, deduplicated."""
    all_headlines = []
    seen = set()

    for fn in [_fetch_yahoo_news, _fetch_google_news_rss,
               _fetch_seeking_alpha_rss, _fetch_bizportal_rss,
               _fetch_calcalist_rss]:
        try:
            items = fn()
            for item in items:
                t = item.get('title', '').strip()
                if t and t not in seen and len(t) > 10:
                    seen.add(t)
                    all_headlines.append(item)
        except Exception:
            pass

    return all_headlines[:60]


# ══════════════════════════════════════════════════════════════
#  2. VIX SPIKE HISTORY ANALYSIS
# ══════════════════════════════════════════════════════════════

def _get_historical_vix(period: str = "2y") -> pd.DataFrame:
    """Download VIX history."""
    try:
        t = yf.Ticker("^VIX")
        df = t.history(period=period, interval="1d", auto_adjust=True, actions=False)
        return df[['Close']].rename(columns={'Close': 'VIX'}) if not df.empty else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _get_stock_returns_on_dates(tickers: list, dates: list,
                                 forward_days: int = 10) -> dict:
    """
    For each ticker, compute average return over `forward_days` after `dates`.
    Returns {ticker: avg_return_pct}
    """
    results = {}
    for ticker in tickers:
        try:
            t   = yf.Ticker(ticker)
            df  = t.history(period="2y", interval="1d", auto_adjust=True, actions=False)
            if df.empty:
                continue
            close = df['Close']
            returns = []
            for date in dates:
                # Find index of date or closest after
                idx_list = close.index[close.index >= date]
                if len(idx_list) < forward_days:
                    continue
                entry = float(close.loc[idx_list[0]])
                exit_ = float(close.loc[idx_list[min(forward_days-1, len(idx_list)-1)]])
                if entry > 0:
                    returns.append((exit_ - entry) / entry * 100)
            if returns:
                results[ticker] = round(float(np.mean(returns)), 1)
        except Exception:
            pass
    return results


def analyze_vix_spikes(vix_threshold: float = 25.0,
                        forward_days: int = 10) -> dict:
    """
    Find historical dates when VIX crossed above threshold.
    For each spike, measure which stocks went up vs down over next N days.
    Returns {
        spike_dates: [...],
        winners: [{ticker, avg_return, times_positive}],
        losers:  [{ticker, avg_return}],
        analysis: str
    }
    """
    vix_df = _get_historical_vix("2y")
    if vix_df.empty:
        return {"error": "Could not fetch VIX history"}

    # Find dates where VIX crossed ABOVE threshold (was below, now above)
    vix   = vix_df['VIX']
    cross = (vix > vix_threshold) & (vix.shift(1) <= vix_threshold)
    spike_dates = vix_df.index[cross].tolist()

    if not spike_dates:
        return {
            "spike_dates": [],
            "threshold": vix_threshold,
            "message": f"No VIX spikes above {vix_threshold} found in last 2 years."
        }

    # Sample of tickers to analyze (defensive + risky)
    watch_tickers = list(set(
        DEFENSIVE_STOCKS + VIX_BENEFICIARIES + VIX_LOSERS +
        ["SPY","QQQ","GLD","TLT","XOM","COIN","NVDA","AMD","TSLA","META",
         "RTX","LMT","ESLT","JNJ","PG","WMT","KO","MCD","DUK","SO"]
    ))

    returns = _get_stock_returns_on_dates(watch_tickers, spike_dates, forward_days)

    # Sort by return
    sorted_ret = sorted(returns.items(), key=lambda x: x[1], reverse=True)
    winners = [{"ticker": t, "avg_return": r,
                "type": "safe_haven" if t in DEFENSIVE_STOCKS else "other"}
               for t, r in sorted_ret if r > 0]
    losers  = [{"ticker": t, "avg_return": r}
               for t, r in sorted_ret if r < 0]

    # Format spike dates
    spike_strs = [d.strftime('%Y-%m-%d') for d in spike_dates[-10:]]  # last 10

    return {
        "threshold":     vix_threshold,
        "spike_dates":   spike_strs,
        "total_spikes":  len(spike_dates),
        "forward_days":  forward_days,
        "winners":       winners[:15],
        "losers":        losers[:10],
        "current_vix":   round(float(vix.iloc[-1]), 2),
    }


# ══════════════════════════════════════════════════════════════
#  3. CLAUDE AI ANALYSIS
# ══════════════════════════════════════════════════════════════

def _call_claude(headlines: list) -> dict:
    """Send headlines to Claude API for analysis."""
    headlines_text = "\n".join(
        f"[{h.get('source','?')}] {h.get('published','')} — {h['title']}"
        for h in headlines[:40]
    )

    prompt = f"""You are a professional stock market analyst with deep knowledge of sector rotation and macro trends.

Analyze these market headlines and identify:
1. Stocks/sectors to WATCH (likely to benefit from current news)
2. Stocks/sectors to AVOID (likely to be hurt)
3. Key macro themes

Headlines from multiple sources:
{headlines_text}

Respond ONLY with valid JSON (no markdown fences):
{{
  "watch": [
    {{"ticker": "XOM", "reason": "Oil supply cuts expected to push prices higher", "confidence": "HIGH", "theme": "oil/energy"}},
    {{"ticker": "COIN", "reason": "Bitcoin ETF approval boosts crypto demand", "confidence": "MEDIUM", "theme": "crypto"}}
  ],
  "avoid": [
    {{"ticker": "RIVN", "reason": "EV demand weakening, high cash burn risk", "confidence": "HIGH", "theme": "EV"}}
  ],
  "summary": "2-3 sentence market overview based on today's headlines.",
  "key_themes": ["energy rally", "crypto momentum", "rate uncertainty"],
  "macro_signal": "BULLISH" or "BEARISH" or "NEUTRAL"
}}

Rules:
- Use real US stock ticker symbols
- confidence: HIGH / MEDIUM / LOW
- 3-8 watch stocks, 2-5 avoid stocks
- Focus on clear news-driven catalysts
- Consider both US and global market news"""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model":      "claude-sonnet-4-20250514",
                "max_tokens": 1200,
                "messages":   [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        if resp.status_code != 200:
            return {}
        data    = resp.json()
        content = data.get('content', [{}])[0].get('text', '').strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1].rsplit('```', 1)[0]
        return json.loads(content)
    except Exception:
        return {}


# ══════════════════════════════════════════════════════════════
#  PUBLIC ENTRY POINTS
# ══════════════════════════════════════════════════════════════

def run_news_intelligence() -> dict:
    """Fetch multi-source news + Claude AI analysis."""
    headlines = fetch_all_news()
    if not headlines:
        return {"error": "Could not fetch market news.", "headlines": []}

    analysis = _call_claude(headlines)

    return {
        "watch":       analysis.get("watch", []),
        "avoid":       analysis.get("avoid", []),
        "summary":     analysis.get("summary", ""),
        "key_themes":  analysis.get("key_themes", []),
        "macro_signal":analysis.get("macro_signal", "NEUTRAL"),
        "headlines":   headlines,
        "timestamp":   datetime.utcnow() + timedelta(hours=3),  # Israel time
        "source_count": len(set(h.get('source','') for h in headlines)),
    }


def run_vix_analysis(threshold: float = 25.0, forward_days: int = 10) -> dict:
    """Run VIX spike historical analysis."""
    return analyze_vix_spikes(threshold, forward_days)

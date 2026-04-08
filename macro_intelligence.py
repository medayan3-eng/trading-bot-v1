"""
Macro Intelligence Engine
========================
1. Fetches live news headlines from multiple sources
2. Uses Claude AI to identify the macro theme (war, ceasefire, rate decision, etc.)
3. Matches theme to historical precedents (what happened to markets last time)
4. Outputs: what to BUY, what to SELL/SHORT, what to WATCH

Historical macro playbooks based on real market behavior:
"""

import requests
import json
import re
import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


# ──────────────────────────────────────────────────────────────
#  MACRO PLAYBOOKS — historical precedents
#  Each theme maps to expected market reactions
# ──────────────────────────────────────────────────────────────
MACRO_PLAYBOOKS = {
    "oil_supply_shock": {
        "triggers": ["strait of hormuz", "opec cut", "oil supply", "pipeline attack",
                     "saudi", "embargo", "oil sanction"],
        "description": "Oil supply disruption — historically prices surge +15-40%",
        "historical_examples": ["Gulf War 1990 (+120%)", "Arab Spring 2011 (+30%)", "Ukraine 2022 (+60%)"],
        "buy":   ["XOM","CVX","COP","SLB","HAL","PSX","MPC","OXY","DVN","USO","UCO","ERX"],
        "sell":  ["RIVN","NIO","TSLA","AAL","DAL","UAL","LUV","UPS","FDX"],
        "watch": ["GLD","TLT","VZ","PG"],
        "etfs":  {"long": "USO, XLE, ERX (3x Energy)", "short": "SQQQ, JETS (airlines)"},
    },
    "oil_price_drop": {
        "triggers": ["ceasefire", "opec increase", "oil glut", "oil oversupply",
                     "peace deal", "hormuz open", "iran deal"],
        "description": "Oil price decline — airlines/transport surge, energy falls",
        "historical_examples": ["2014 oil crash (-50%)", "COVID 2020 (-70%)"],
        "buy":   ["AAL","DAL","UAL","LUV","UPS","FDX","AMZN","COST","WMT"],
        "sell":  ["XOM","CVX","COP","SLB","HAL","OXY","USO","ERX"],
        "watch": ["XLP","XLU","IEF"],
        "etfs":  {"long": "JETS (airlines), XLY", "short": "XLE, USO"},
    },
    "war_escalation": {
        "triggers": ["war", "invasion", "military strike", "missile attack", "conflict escalation",
                     "nato", "sanctions", "troops", "bombardment", "iran attack", "nuclear threat"],
        "description": "Geopolitical escalation — defense stocks surge, risk assets fall",
        "historical_examples": ["Ukraine invasion 2022 (LMT +40%)", "Gulf War (RTX +60%)", "9/11 (GLD +8%)"],
        "buy":   ["LMT","RTX","NOC","GD","ESLT","AXON","HEI","GLD","SLV","TLT","XOM","CVX"],
        "sell":  ["COIN","TSLA","META","NVDA","ARKK","RIVN","NIO","SHOP"],
        "watch": ["VIX","TLT","GLD","SHY"],
        "etfs":  {"long": "GLD, ITA (defense), TLT", "short": "ARKK, SOXL, TQQQ"},
    },
    "ceasefire_peace": {
        "triggers": ["ceasefire", "peace agreement", "peace deal", "hostilities end",
                     "truce", "diplomatic", "negotiations", "de-escalation"],
        "description": "Peace/ceasefire — risk-on returns, defense falls, markets rally",
        "historical_examples": ["Israel-Hamas ceasefire 2024 (markets +2%)", "Ukraine talks 2022"],
        "buy":   ["QQQ","SPY","NVDA","META","TSLA","COIN","IWM","XLY"],
        "sell":  ["LMT","RTX","NOC","GD","GLD","TLT","XOM"],
        "watch": ["COIN","ARKK","RIVN"],
        "etfs":  {"long": "QQQ, TQQQ, IWM", "short": "GLD, TLT, ITA"},
    },
    "fed_rate_hike": {
        "triggers": ["rate hike", "interest rate increase", "fed raises", "hawkish fed",
                     "tightening", "inflation fight", "powell hawkish"],
        "description": "Fed rate hike — financials benefit, growth stocks hurt",
        "historical_examples": ["2022 hiking cycle (QQQ -33%)", "2018 hikes (banks +10%)"],
        "buy":   ["JPM","GS","MS","BX","KKR","V","MA","BK","USB","WFC"],
        "sell":  ["ARKK","RIVN","COIN","ZM","SHOP","PLTR","HOOD","MSTR"],
        "watch": ["SHY","TBT","XLF"],
        "etfs":  {"long": "XLF, KRE (banks), TBT (short bonds)", "short": "TLT, ARKK, TQQQ"},
    },
    "fed_rate_cut": {
        "triggers": ["rate cut", "interest rate cut", "fed cuts", "dovish fed",
                     "pivot", "easing", "powell dovish", "quantitative easing"],
        "description": "Fed rate cut — growth stocks, crypto, real estate surge",
        "historical_examples": ["2019 cuts (QQQ +38%)", "COVID cuts (TSLA +700%)"],
        "buy":   ["QQQ","NVDA","TSLA","COIN","MSTR","ARKK","RIVN","PLTR","IWM","XLRE"],
        "sell":  ["JPM","GS","USB","BK","SHY","BIL"],
        "watch": ["GLD","TLT","REIT"],
        "etfs":  {"long": "TQQQ, ARKK, SOXL, GLD", "short": "KRE, XLF"},
    },
    "inflation_surge": {
        "triggers": ["inflation", "cpi above", "prices surge", "cost of living",
                     "stagflation", "hyperinflation", "price spike"],
        "description": "Inflation surge — commodities, energy, gold outperform",
        "historical_examples": ["1970s stagflation (gold +2000%)", "2021-2022 (XLE +60%)"],
        "buy":   ["GLD","SLV","XOM","CVX","COP","CF","MOS","NEM","GOLD","WPM","FCX"],
        "sell":  ["TLT","IEF","BOND","ZM","SHOP","growth stocks"],
        "watch": ["TIPS","UNG","USO","ALB"],
        "etfs":  {"long": "GLD, XLE, XLB, PDBC (commodities)", "short": "TLT, IEF"},
    },
    "recession_fear": {
        "triggers": ["recession", "gdp contraction", "unemployment surge", "yield curve invert",
                     "economic slowdown", "layoffs", "bankruptcy surge"],
        "description": "Recession fears — defensive stocks, gold, bonds outperform",
        "historical_examples": ["2008 (GLD +25%)", "COVID (WMT +20%, KO held)"],
        "buy":   ["PG","KO","PEP","WMT","JNJ","UNH","NEE","DUK","GLD","TLT","SHY","BIL"],
        "sell":  ["COIN","TSLA","NVDA","META","RIVN","AAL","XOM"],
        "watch": ["VIX","TLT","SHY","XLU"],
        "etfs":  {"long": "XLP, XLU, XLV, GLD, TLT", "short": "XLY, XLK, SOXL"},
    },
    "tech_earnings_beat": {
        "triggers": ["earnings beat", "revenue beat", "guidance raise", "blowout quarter",
                     "record revenue", "profit surge", "beats estimates"],
        "description": "Strong tech earnings — sector momentum, rotation into tech",
        "historical_examples": ["NVDA earnings 2023 (+24% day)", "META 2023 (+20%)"],
        "buy":   ["QQQ","NVDA","META","AAPL","MSFT","AMD","GOOGL","SMH","SOXL"],
        "sell":  ["TLT","GLD","XLU"],
        "watch": ["CRWD","DDOG","NET","PANW"],
        "etfs":  {"long": "QQQ, SMH, TQQQ", "short": "nothing specific"},
    },
    "crypto_rally": {
        "triggers": ["bitcoin surge", "btc all time high", "crypto rally", "ethereum",
                     "bitcoin etf", "crypto adoption", "coinbase"],
        "description": "Crypto bull run — crypto stocks surge, risk-on",
        "historical_examples": ["BTC ATH 2021 (COIN +300%)", "ETF approval 2024 (MSTR +100%)"],
        "buy":   ["COIN","MSTR","HUT","WULF","RIOT","MARA","HOOD","PYPL","SQ"],
        "sell":  ["GLD","TLT","BIL"],
        "watch": ["ARKK","TSLA","NVDA"],
        "etfs":  {"long": "BITO (Bitcoin ETF), COIN", "short": "GLD"},
    },
    "banking_crisis": {
        "triggers": ["bank failure", "bank collapse", "bank run", "fdic", "credit crisis",
                     "svb", "lehman", "contagion", "liquidity crisis"],
        "description": "Banking crisis — flight to safety, gold, treasuries surge",
        "historical_examples": ["SVB 2023 (GLD +5%, KRE -28%)", "2008 (GLD +25%)"],
        "buy":   ["GLD","SLV","TLT","SHY","BIL","JPM","GS","PG","WMT"],
        "sell":  ["KRE","PACW","WAL","ZION","small banks","COIN"],
        "watch": ["VIX","SPY","XLF"],
        "etfs":  {"long": "GLD, TLT, XLP", "short": "KRE, FAZ"},
    },
    "china_tension": {
        "triggers": ["china taiwan", "south china sea", "china sanctions", "tech ban",
                     "chip export", "huawei", "china trade war", "tariffs china"],
        "description": "US-China tension — semis drop, defense/energy benefit",
        "historical_examples": ["Chip ban 2022 (NVDA -25%)", "Trade war 2018 (XLK -15%)"],
        "buy":   ["LMT","RTX","NOC","GD","ESLT","AXON","XOM","CVX","domestic tech"],
        "sell":  ["NVDA","AMD","QCOM","AMAT","LRCX","KLAC","ASML","FXI"],
        "watch": ["EWJ","EEM","TSM"],
        "etfs":  {"long": "ITA (defense), XLE", "short": "FXI, SMH, SOXL"},
    },
}


# ──────────────────────────────────────────────────────────────
#  NEWS FETCHER (reuse from news_intelligence)
# ──────────────────────────────────────────────────────────────
def _fetch_headlines() -> list:
    """Fetch top headlines from multiple sources."""
    headlines = []
    seen = set()

    # Yahoo Finance
    for sym in ["SPY","QQQ","GLD","USO","BTC-USD","^VIX","^GSPC","XOM","LMT"]:
        try:
            news = yf.Ticker(sym).news or []
            for item in news[:5]:
                title = (item.get('title') or
                         item.get('content', {}).get('title') or '')
                if title and title not in seen:
                    seen.add(title)
                    headlines.append({
                        'title': title,
                        'source': 'Yahoo Finance',
                        'url': item.get('link') or item.get('url', ''),
                    })
        except Exception:
            pass

    # Google News RSS
    for query in ["stock market today", "geopolitical market", "fed reserve"]:
        try:
            url = f"https://news.google.com/rss/search?q={query.replace(' ','+')}&hl=en-US&gl=US&ceid=US:en"
            resp = requests.get(url, timeout=6, headers={'User-Agent': 'Mozilla/5.0'})
            if resp.status_code == 200:
                for item in re.findall(r'<item>(.*?)</item>', resp.text, re.DOTALL)[:8]:
                    title = re.search(r'<title>(.*?)</title>', item)
                    link  = re.search(r'<link>(.*?)</link>', item)
                    if title:
                        t = re.sub(r'<[^>]+>', '', title.group(1)).strip()
                        if t and t not in seen:
                            seen.add(t)
                            headlines.append({
                                'title': t,
                                'source': 'Google News',
                                'url': link.group(1).strip() if link else '',
                            })
        except Exception:
            pass

    return headlines[:50]


# ──────────────────────────────────────────────────────────────
#  THEME DETECTOR — rule-based fast scan
# ──────────────────────────────────────────────────────────────
def _detect_themes_fast(headlines: list) -> list:
    """Quick keyword matching to detect macro themes."""
    text = " ".join(h['title'].lower() for h in headlines)
    detected = []
    for theme_key, playbook in MACRO_PLAYBOOKS.items():
        score = sum(1 for kw in playbook['triggers'] if kw in text)
        if score >= 1:
            detected.append({
                "theme":    theme_key,
                "score":    score,
                "playbook": playbook,
            })
    detected.sort(key=lambda x: -x['score'])
    return detected[:3]  # top 3 themes


# ──────────────────────────────────────────────────────────────
#  CLAUDE AI MACRO ANALYSIS
# ──────────────────────────────────────────────────────────────
def _claude_macro_analysis(headlines: list) -> dict:
    """Send headlines to Claude for deep macro analysis."""
    headlines_text = "\n".join(
        f"[{h.get('source','?')}] {h['title']}"
        for h in headlines[:35]
    )

    playbooks_summary = "\n".join(
        f"- {k}: {v['description']}"
        for k, v in MACRO_PLAYBOOKS.items()
    )

    prompt = f"""You are a macro economist and market strategist. Analyze these real-time news headlines.

HEADLINES:
{headlines_text}

HISTORICAL MACRO PLAYBOOKS (for reference):
{playbooks_summary}

Based on the headlines, provide a market intelligence briefing. Respond ONLY with valid JSON:
{{
  "dominant_theme": "one word theme like: war / ceasefire / oil_shock / fed_hike / recession / crypto / tech / inflation",
  "situation_summary": "2-3 sentence description of what is happening right now based on headlines",
  "historical_parallel": "What historical event does this most resemble and what happened to markets then?",
  "market_impact": "HIGH/MEDIUM/LOW",
  "immediate_plays": {{
    "strong_buy": ["ticker1", "ticker2", "ticker3"],
    "consider_buy": ["ticker4", "ticker5"],
    "avoid_sell": ["ticker6", "ticker7"],
    "sectors_to_rotate_into": ["XLE", "XLU"],
    "sectors_to_avoid": ["ARKK", "XLK"]
  }},
  "reasoning": "Why these specific moves make sense given the current macro environment",
  "risk_level": "HIGH/MEDIUM/LOW",
  "time_horizon": "intraday / days / weeks"
}}"""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model":      "claude-sonnet-4-20250514",
                "max_tokens": 1000,
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


# ──────────────────────────────────────────────────────────────
#  HISTORICAL PRICE VERIFICATION
#  Check if the "buy" tickers actually performed well historically
# ──────────────────────────────────────────────────────────────
def _verify_historical_performance(tickers: list, days_back: int = 252) -> dict:
    """
    For a list of tickers, check their 1-year performance
    to validate if they are actually strong candidates.
    """
    results = {}
    for ticker in tickers[:8]:  # limit to avoid timeouts
        try:
            t  = yf.Ticker(ticker)
            df = t.history(period="1y", interval="1d", auto_adjust=True, actions=False)
            if df.empty or len(df) < 20:
                continue
            perf_1y  = (float(df['Close'].iloc[-1]) - float(df['Close'].iloc[0])) / float(df['Close'].iloc[0]) * 100
            perf_1m  = (float(df['Close'].iloc[-1]) - float(df['Close'].iloc[-21])) / float(df['Close'].iloc[-21]) * 100 if len(df) >= 21 else 0
            results[ticker] = {
                "perf_1y": round(perf_1y, 1),
                "perf_1m": round(perf_1m, 1),
                "price":   round(float(df['Close'].iloc[-1]), 2),
            }
        except Exception:
            pass
    return results


# ──────────────────────────────────────────────────────────────
#  MAIN PUBLIC FUNCTION
# ──────────────────────────────────────────────────────────────
def run_macro_intelligence() -> dict:
    """
    Main entry point:
    1. Fetch live news
    2. Detect macro themes (fast rule-based)
    3. Run Claude AI for deep analysis
    4. Verify historical performance of suggested plays
    Returns complete macro briefing dict
    """
    headlines = _fetch_headlines()
    if not headlines:
        return {"error": "Could not fetch headlines", "headlines": []}

    # Fast theme detection
    fast_themes = _detect_themes_fast(headlines)

    # AI deep analysis
    ai_analysis = _claude_macro_analysis(headlines)

    # Get the primary playbook
    primary_playbook = None
    if fast_themes:
        primary_playbook = fast_themes[0]['playbook']
    
    # Verify historical performance of buy suggestions
    buy_tickers = []
    if ai_analysis.get('immediate_plays', {}).get('strong_buy'):
        buy_tickers = ai_analysis['immediate_plays']['strong_buy']
    elif primary_playbook:
        buy_tickers = primary_playbook.get('buy', [])[:6]

    historical_perf = _verify_historical_performance(buy_tickers)

    return {
        "headlines":       headlines[:20],
        "fast_themes":     fast_themes,
        "ai_analysis":     ai_analysis,
        "primary_playbook": primary_playbook,
        "historical_perf": historical_perf,
        "timestamp":       datetime.utcnow() + timedelta(hours=3),
        "headline_count":  len(headlines),
    }

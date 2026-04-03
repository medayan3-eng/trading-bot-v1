import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import requests
import warnings
warnings.filterwarnings('ignore')

from screener import calculate_indicators, debug_ticker
from backtester import run_backtest_on_screened
from news_fetcher import fetch_news
from news_intelligence import run_news_intelligence, run_vix_analysis
from stock_universe import STOCK_UNIVERSE

st.set_page_config(
    page_title="Murphy Stock Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    .stApp { background: #0a0e1a; color: #e0e6f0; }
    .main-header { font-family:'IBM Plex Mono',monospace; font-size:2rem; font-weight:600; color:#00d4aa; letter-spacing:-1px; margin-bottom:0.1rem; }
    .sub-header  { font-family:'IBM Plex Mono',monospace; font-size:0.78rem; color:#4a5568; letter-spacing:2px; text-transform:uppercase; margin-bottom:1rem; }
    .market-bar  { background:#0d1117; border:1px solid #1e293b; border-radius:10px; padding:0.9rem 1.4rem; display:flex; gap:2rem; align-items:center; flex-wrap:wrap; margin-bottom:1.2rem; }
    .mkt-item    { display:flex; flex-direction:column; min-width:80px; }
    .mkt-label   { font-size:0.68rem; color:#4a5568; text-transform:uppercase; letter-spacing:1px; }
    .mkt-val     { font-family:'IBM Plex Mono',monospace; font-size:1.05rem; font-weight:600; }
    .mkt-chg     { font-family:'IBM Plex Mono',monospace; font-size:0.78rem; }
    .fear-box        { border-radius:8px; padding:0.5rem 1.1rem; display:flex; flex-direction:column; align-items:center; min-width:150px; }
    .fear-box-green  { background:rgba(0,212,170,0.12);  border:2px solid #00d4aa; }
    .fear-box-yellow { background:rgba(245,158,11,0.12); border:2px solid #f59e0b; }
    .fear-box-red    { background:rgba(239,68,68,0.15);  border:2px solid #ef4444; }
    .fear-label      { font-size:0.68rem; color:#9ca3af; text-transform:uppercase; letter-spacing:1px; }
    .fear-val-green  { font-family:'IBM Plex Mono',monospace; font-size:1.6rem; font-weight:700; color:#00d4aa; }
    .fear-val-yellow { font-family:'IBM Plex Mono',monospace; font-size:1.6rem; font-weight:700; color:#f59e0b; }
    .fear-val-red    { font-family:'IBM Plex Mono',monospace; font-size:1.6rem; font-weight:700; color:#ef4444; }
    .fear-msg  { font-size:0.7rem; text-align:center; margin-top:0.2rem; }
    .metric-card { background:#111827; border:1px solid #1e293b; border-radius:8px; padding:1rem; margin:0.25rem 0; border-left:3px solid #00d4aa; }
    .stock-card  { background:#111827; border:1px solid #1e293b; border-radius:10px; padding:1.4rem; margin:0.45rem 0; }
    .stock-card:hover { border-color:#00d4aa; box-shadow:0 0 18px rgba(0,212,170,0.1); }
    .ticker-symbol { font-family:'IBM Plex Mono',monospace; font-size:1.35rem; font-weight:600; color:#00d4aa; }
    .price-display { font-family:'IBM Plex Mono',monospace; font-size:1rem; color:#e0e6f0; }
    .badge        { display:inline-block; padding:0.18rem 0.55rem; border-radius:4px; font-size:0.72rem; font-family:'IBM Plex Mono',monospace; font-weight:600; margin:0.1rem; }
    .badge-green  { background:rgba(0,212,170,0.15);  color:#00d4aa; border:1px solid rgba(0,212,170,0.3); }
    .badge-yellow { background:rgba(245,158,11,0.15); color:#f59e0b; border:1px solid rgba(245,158,11,0.3); }
    .badge-red    { background:rgba(239,68,68,0.15);  color:#ef4444; border:1px solid rgba(239,68,68,0.3); }
    .badge-blue   { background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3); }
    .scan-stat  { font-family:'IBM Plex Mono',monospace; font-size:1.8rem; font-weight:600; color:#00d4aa; }
    .scan-label { font-size:0.72rem; color:#4a5568; text-transform:uppercase; letter-spacing:1px; }
    div[data-testid="stSidebar"] { background:#0d1117; border-right:1px solid #1e293b; }
    .stButton > button { background:#00d4aa; color:#0a0e1a; font-family:'IBM Plex Mono',monospace; font-weight:600; border:none; border-radius:6px; padding:0.6rem 1.5rem; letter-spacing:0.5px; width:100%; }
    .stButton > button:hover { background:#00b894; }
    .news-item { background:#111827; border:1px solid #1e293b; border-radius:8px; padding:0.9rem; margin:0.35rem 0; border-left:3px solid #3b82f6; }
    .news-title { color:#60a5fa; font-size:0.88rem; font-weight:600; }
    .news-meta  { color:#4a5568; font-size:0.72rem; font-family:'IBM Plex Mono',monospace; margin-top:0.25rem; }
    hr { border-color:#1e293b; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  MARKET DATA  (cached 3 min)
# ══════════════════════════════════════════════
@st.cache_data(ttl=180)
def fetch_market_data():
    symbols = {"^VIX":"VIX", "^GSPC":"S&P 500", "^IXIC":"Nasdaq", "^DJI":"Dow Jones"}
    result = {}
    for sym, label in symbols.items():
        try:
            hist = yf.Ticker(sym).history(period="2d", interval="1d")
            if len(hist) >= 2:
                prev  = float(hist['Close'].iloc[-2])
                curr  = float(hist['Close'].iloc[-1])
                chg_p = (curr - prev) / prev * 100
            elif len(hist) == 1:
                curr = float(hist['Close'].iloc[-1]); chg_p = 0
            else:
                curr = chg_p = 0
            result[label] = {"value": curr, "change_pct": chg_p}
        except:
            result[label] = {"value": 0, "change_pct": 0}

    # VIX3M (VXVCLS or ^VIX3M) for VIX/VIX3M ratio
    try:
        vix3m = yf.Ticker("^VIX3M").history(period="2d", interval="1d")
        if not vix3m.empty:
            result["VIX3M"] = {"value": float(vix3m['Close'].iloc[-1])}
        else:
            # fallback: try VXVCLS
            vix3m2 = yf.Ticker("VXVCLS").history(period="2d", interval="1d")
            if not vix3m2.empty:
                result["VIX3M"] = {"value": float(vix3m2['Close'].iloc[-1])}
    except:
        pass

    return result


def _vix_regime(vix: float, ratio: float) -> dict:
    """Returns regime info: color, status, preferred assets, warning."""
    if vix <= 0:
        return {"cls": "green", "msg": "No data", "assets": "", "ratio_status": ""}

    if ratio > 0:
        if ratio >= 1.0:
            ratio_status = f"🚨 BACKWARDATION ({ratio:.2f}) — Institutional panic! Safe havens only"
            ratio_color  = "#ef4444"
        elif ratio >= 0.9:
            ratio_status = f"⚠️ Contango tightening ({ratio:.2f}) — Caution"
            ratio_color  = "#f59e0b"
        else:
            ratio_status = f"✅ Normal Contango ({ratio:.2f}) — Market cruising"
            ratio_color  = "#00d4aa"
    else:
        ratio_status = ""
        ratio_color  = "#4a5568"

    if vix < 15:
        return {
            "cls":    "green",
            "msg":    "✅ VIX Low — Growth mode",
            "assets": "💹 Preferred: Technology (XLK) · Small Caps (IWM) · Consumer Discretionary (XLY)",
            "assets_color": "#00d4aa",
            "ratio_status": ratio_status,
            "ratio_color":  ratio_color,
        }
    elif vix < 20:
        return {
            "cls":    "green",
            "msg":    "✅ Low fear — Safe to trade",
            "assets": "💹 Preferred: Growth stocks · Technology · Small Caps",
            "assets_color": "#00d4aa",
            "ratio_status": ratio_status,
            "ratio_color":  ratio_color,
        }
    elif vix < 30:
        return {
            "cls":    "yellow",
            "msg":    "⚠️ VIX Elevated — Rotate to defensives",
            "assets": "🛡️ Preferred: Utilities (XLU) · Healthcare (XLV) · Consumer Staples (XLP) · Dividend stocks",
            "assets_color": "#f59e0b",
            "ratio_status": ratio_status,
            "ratio_color":  ratio_color,
        }
    else:
        return {
            "cls":    "red",
            "msg":    "🚫 VIX Extreme — Emergency shelters only",
            "assets": "🏦 Preferred: Cash · Gold (GLD) · Silver (SLV) · Short-term Treasuries (SHY/BIL)",
            "assets_color": "#ef4444",
            "ratio_status": ratio_status,
            "ratio_color":  ratio_color,
        }


def render_market_bar():
    data   = fetch_market_data()
    vix    = data.get("VIX",   {}).get("value", 0)
    vix3m  = data.get("VIX3M", {}).get("value", 0)
    ratio  = round(vix / vix3m, 3) if vix3m > 0 else 0
    regime = _vix_regime(vix, ratio)

    vix_str   = f"{vix:.2f}"   if vix   else "—"
    vix3m_str = f"{vix3m:.2f}" if vix3m else "—"
    ratio_str = f"{ratio:.3f}" if ratio else "—"

    def tile(label, d):
        v, chg = d.get("value", 0), d.get("change_pct", 0)
        col   = "#00d4aa" if chg >= 0 else "#ef4444"
        arrow = "▲" if chg >= 0 else "▼"
        return (f'<div class="mkt-item"><span class="mkt-label">{label}</span>'
                f'<span class="mkt-val">{v:,.2f}</span>'
                f'<span class="mkt-chg" style="color:{col}">{arrow} {abs(chg):.2f}%</span></div>')

    tiles = "".join(tile(k, v) for k, v in data.items() if k not in ("VIX","VIX3M"))

    ratio_badge = ""
    if ratio > 0:
        rc = regime["ratio_color"]
        ratio_badge = (f'<div style="font-family:IBM Plex Mono,monospace;font-size:0.7rem;'
                       f'color:{rc};margin-top:0.2rem;">'
                       f'VIX/VIX3M: <b>{ratio_str}</b></div>')

    st.markdown(f"""
    <div class="market-bar">
      <div class="fear-box fear-box-{regime['cls']}">
        <span class="fear-label">😨 VIX Fear Index</span>
        <span class="fear-val-{regime['cls']}">{vix_str}</span>
        <span class="fear-msg" style="color:{'#00d4aa' if regime['cls']=='green' else '#f59e0b' if regime['cls']=='yellow' else '#ef4444'};">{regime['msg']}</span>
        {ratio_badge}
      </div>
      <div style="width:1px;background:#1e293b;align-self:stretch;"></div>
      {tiles}
      <div style="margin-left:auto;font-family:'IBM Plex Mono',monospace;font-size:0.68rem;color:#374151;">
        🕐 {(datetime.utcnow() + timedelta(hours=3)).strftime('%H:%M:%S')} 🇮🇱
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Sector rotation guidance bar
    assets       = regime.get("assets", "")
    assets_color = regime.get("assets_color", "#e0e6f0")
    ratio_line   = regime.get("ratio_status", "")
    rc           = regime.get("ratio_color", "#4a5568")

    if assets:
        st.markdown(f"""
        <div style="background:#0d1117;border:1px solid #1e293b;border-radius:8px;
                    padding:0.6rem 1.2rem;margin-bottom:0.8rem;display:flex;
                    flex-direction:column;gap:0.2rem;">
          <div style="font-size:0.82rem;color:{assets_color};">{assets}</div>
          {'<div style="font-size:0.78rem;color:' + rc + ';">' + ratio_line + '</div>' if ratio_line else ''}
          <div style="font-size:0.68rem;color:#4a5568;">
            VIX: {vix_str} &nbsp;|&nbsp; VIX3M: {vix3m_str} &nbsp;|&nbsp; Ratio: {ratio_str}
            {'&nbsp;|&nbsp; <b style="color:#ef4444;">BACKWARDATION — Institutions pulling money from markets!</b>' if ratio >= 1.0 else ''}
          </div>
        </div>
        """, unsafe_allow_html=True)

    return vix


# ══════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ Parameters")
        st.markdown("---")
        min_price  = st.slider("Min Price ($)", 15, 100, 15)
        min_volume = st.number_input("Min Avg Volume (M)", 0.1, 10.0, 0.5, 0.1)
        min_beta   = st.slider("Min Beta", 0.5, 3.0, 1.0, 0.1)
        st.markdown("---")
        st.markdown("**RSI**")
        rsi_range  = st.slider("RSI Range", 10, 90, (10, 50))
        rsi_min    = rsi_range[0]
        rsi_max    = rsi_range[1]
        rsi_period = st.number_input("RSI Period", 5, 20, 14)
        st.caption(f"Stocks with RSI between {rsi_min} – {rsi_max}")
        st.markdown("---")
        st.markdown("**Trend Filters**")
        req200       = st.checkbox("Above MA200", value=True)
        req50        = st.checkbox("Above MA50",  value=True)
        req20        = st.checkbox("Above MA20 (optional)", value=False)
        req_uptrend  = st.checkbox("📈 52-Week Uptrend (Murphy)", value=True,
                                   help="Price higher than 1 year ago, MA50 > MA200, price above MA200")
        st.markdown("---")
        st.markdown("**Bollinger Bands**")
        bb_period = st.number_input("BB Period", 10, 30, 20)
        bb_std    = st.slider("BB Std Dev", 1.5, 3.0, 2.0, 0.1)
        st.markdown("---")
        st.markdown("**Institutional**")
        min_inst    = st.slider("Min Institutional %", 0, 80, 0)
        fresh_only  = st.checkbox("🟢 Fresh Signals (≤3 days)", value=False)
        apply_qf    = st.checkbox("🔍 Quality Filter (no traps)", value=True,
                                   help="Filters out extended stocks, sideways chop, bull traps")
        st.markdown("---")
        max_stocks = st.slider("Max stocks to scan", 50, 1548, 1548)
        st.markdown("---")

        run_scan = st.button("🔍 STEP 1 — RUN SCAN", use_container_width=True)
        st.caption("Live data — scans market right now")
        st.markdown("")
        run_bt = st.button("📊 STEP 2 — BACKTEST", use_container_width=True)
        st.caption("Tests only stocks from Step 1 — 1 year, many trades")
        st.markdown("")
        debug_ticker_input = st.text_input("🔧 Debug ticker (e.g. COIN)", value="").upper().strip()
        run_debug = st.button("🔧 Debug single stock", use_container_width=True)

        return dict(
            min_price=min_price, min_volume=min_volume*1_000_000,
            min_beta=min_beta, rsi_min=rsi_min, rsi_max=rsi_max, rsi_period=int(rsi_period),
            require_above_200=req200, require_above_50=req50, require_above_20=req20,
            require_uptrend_52w=req_uptrend,
            bb_period=int(bb_period), bb_std=bb_std,
            min_institutional=min_inst, show_fresh_only=fresh_only,
            apply_quality_filter=apply_qf,
            max_stocks=max_stocks, run_scan=run_scan, run_backtest=run_bt,
            run_debug=run_debug, debug_ticker=debug_ticker_input,
        )


# ══════════════════════════════════════════════
#  STOCK CARD
# ══════════════════════════════════════════════
def render_stock_card(stock, bt_summary=None):
    score    = stock.get('score', 0)
    rsi      = stock.get('rsi', 0)
    bb_pct   = stock.get('bb_pct', 0.5)
    trend_4w = stock.get('trend_4w', 0)
    beta     = stock.get('beta', 0)
    macd_hist    = stock.get('macd_hist', 0)
    macd_bullish = stock.get('macd_bullish', False)
    inst_pct = stock.get('institutional_pct')
    fresh    = stock.get('signal_fresh', False)
    sig_date = stock.get('signal_date', '')
    price    = stock.get('price', 0)
    sig_col  = "#00d4aa" if score >= 7 else "#f59e0b" if score >= 5 else "#ef4444"

    badges = []
    if stock.get('above_200'):  badges.append('<span class="badge badge-green">MA200 ✓</span>')
    if stock.get('above_50'):   badges.append('<span class="badge badge-green">MA50 ✓</span>')
    if stock.get('above_20'):   badges.append('<span class="badge badge-blue">MA20 ✓</span>')
    if rsi < 30:                badges.append('<span class="badge badge-red">RSI EXTREME</span>')
    elif rsi < 40:              badges.append('<span class="badge badge-yellow">RSI OVERSOLD</span>')
    if bb_pct < 0.2:            badges.append('<span class="badge badge-green">BB LOWER ✓</span>')
    if trend_4w > 0:            badges.append('<span class="badge badge-green">4W UPTREND</span>')
    if macd_bullish:            badges.append('<span class="badge badge-green">MACD ✓</span>')
    else:                       badges.append('<span class="badge badge-red">MACD ✗</span>')
def render_stock_card(stock, bt_summary=None):
    score       = stock.get('score', 0)
    rsi         = stock.get('rsi', 0)
    bb_pct      = stock.get('bb_pct', 0.5)
    trend_4w    = stock.get('trend_4w', 0)
    beta        = stock.get('beta', 0)
    macd_hist   = stock.get('macd_hist', 0)
    macd_bullish= stock.get('macd_bullish', False)
    inst_pct    = stock.get('institutional_pct')
    fresh       = stock.get('signal_fresh', False)
    sig_date    = stock.get('signal_date', '')
    price       = stock.get('price', 0)
    rs          = stock.get('rs', 1.0)
    vol_ratio   = stock.get('volume_ratio', 1.0)
    vol_spike   = stock.get('volume_spike', False)
    support     = stock.get('support')
    resistance  = stock.get('resistance')
    near_sup    = stock.get('near_support', False)
    patterns    = stock.get('patterns', [])
    uptrend_52w = stock.get('uptrend_52w', False)
    rr_ratio    = stock.get('rr_ratio', 0)
    rr_valid    = stock.get('rr_valid', False)
    rr_stop     = stock.get('rr_stop')
    rr_target   = stock.get('rr_target')
    summary     = stock.get('summary', '')
    ticker      = stock['ticker']
    sig_col     = "#00d4aa" if score >= 7 else "#f59e0b" if score >= 5 else "#ef4444"

    tv_url = f"https://www.tradingview.com/chart/?symbol={ticker}&interval=D"

    badges = []
    if stock.get('above_200'):  badges.append('<span class="badge badge-green">MA200 ✓</span>')
    if stock.get('above_50'):   badges.append('<span class="badge badge-green">MA50 ✓</span>')
    if uptrend_52w:             badges.append('<span class="badge badge-green">📈 52W UPTREND</span>')
    if stock.get('vix_priority'): badges.append('<span class="badge badge-blue">⭐ VIX PRIORITY</span>')
    if rsi < 30:                badges.append('<span class="badge badge-red">RSI EXTREME</span>')
    elif rsi < 40:              badges.append('<span class="badge badge-yellow">RSI OVERSOLD</span>')
    if bb_pct < 0.2:            badges.append('<span class="badge badge-green">BB LOWER ✓</span>')
    if trend_4w > 0:            badges.append('<span class="badge badge-green">4W UPTREND</span>')
    if macd_bullish:            badges.append('<span class="badge badge-green">MACD ✓</span>')
    else:                       badges.append('<span class="badge badge-red">MACD ✗</span>')
    if vol_spike:               badges.append('<span class="badge badge-yellow">⚡ VOL SPIKE</span>')
    if near_sup:                badges.append('<span class="badge badge-green">🎯 NEAR SUPPORT</span>')
    if patterns:                badges.append(f'<span class="badge badge-blue">📐 {patterns[0]}</span>')
    if rr_valid:                badges.append(f'<span class="badge badge-green">R/R 1:{rr_ratio}</span>')
    if inst_pct and inst_pct >= 30:
        badges.append(f'<span class="badge badge-blue">🏦 {inst_pct:.0f}%</span>')
    badges.append('<span class="badge badge-green">🟢 FRESH</span>' if fresh else
                  '<span class="badge badge-yellow">⚠️ LATE</span>')

    bt_html = ""
    if bt_summary:
        wr, tot, avg_r = bt_summary.get('win_rate',0), bt_summary.get('total_trades',0), bt_summary.get('avg_return',0)
        wc = "#00d4aa" if wr>=60 else "#f59e0b" if wr>=45 else "#ef4444"
        bt_html = f"""<div style="margin-top:0.5rem;padding:0.5rem 0.9rem;background:#0d1117;border-radius:6px;border:1px solid #1e293b;display:flex;gap:2rem;">
          <div><div class="scan-label">📊 Win Rate</div><div style="font-family:'IBM Plex Mono',monospace;font-size:1rem;font-weight:700;color:{wc};">{wr:.0f}%</div></div>
          <div><div class="scan-label">Trades</div><div style="font-family:'IBM Plex Mono',monospace;font-size:1rem;color:#e0e6f0;">{tot}</div></div>
          <div><div class="scan-label">Avg Return</div><div style="font-family:'IBM Plex Mono',monospace;font-size:1rem;color:{'#00d4aa' if avg_r>=0 else '#ef4444'};">{avg_r:+.1f}%</div></div>
        </div>"""

    sr_parts = []
    if support:    sr_parts.append(f'<span style="color:#00d4aa;">🟩 Support: ${support}</span>')
    if resistance: sr_parts.append(f'<span style="color:#ef4444;">🟥 Resistance: ${resistance}</span>')
    if rr_valid:   sr_parts.append(f'<span style="color:#f59e0b;">Stop: ${rr_stop} → Target: ${rr_target} (1:{rr_ratio})</span>')
    sr_html = f'<div style="margin-top:0.4rem;font-size:0.78rem;font-family:\'IBM Plex Mono\',monospace;">{" &nbsp;|&nbsp; ".join(sr_parts)}</div>' if sr_parts else ""

    summary_html = f'<div style="margin-top:0.5rem;padding:0.5rem 0.8rem;background:rgba(0,212,170,0.06);border-left:3px solid #00d4aa;border-radius:0 6px 6px 0;font-size:0.8rem;color:#9ca3af;line-height:1.5;">💡 {summary}</div>' if summary else ""

    st.markdown(f"""
    <div class="stock-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div><span class="ticker-symbol">{ticker}</span>
             <span style="color:#6b7280;font-size:0.78rem;margin-left:0.6rem;">{stock.get('name','')}</span></div>
        <div style="text-align:right;">
          <div class="price-display">${price:.2f}</div>
          <div style="font-weight:600;color:{sig_col};font-size:0.85rem;">Score: {score}/10</div>
        </div>
      </div>
      <div style="margin:0.5rem 0;">{''.join(badges)}</div>
      <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:0.4rem;margin-top:0.6rem;">
        <div><div class="scan-label">RSI(14)</div>
             <div style="font-family:'IBM Plex Mono',monospace;font-size:0.9rem;font-weight:600;
                  color:{'#ef4444' if rsi<30 else '#f59e0b' if rsi<40 else '#e0e6f0'};">{rsi:.1f}</div></div>
        <div><div class="scan-label">MACD Hist</div>
             <div style="font-family:'IBM Plex Mono',monospace;font-size:0.9rem;font-weight:600;
                  color:{'#00d4aa' if macd_bullish else '#ef4444'};">{macd_hist:+.3f}</div></div>
        <div><div class="scan-label">BB%B</div>
             <div style="font-family:'IBM Plex Mono',monospace;font-size:0.9rem;font-weight:600;
                  color:{'#00d4aa' if bb_pct<0.2 else '#e0e6f0'};">{bb_pct:.2f}</div></div>
        <div><div class="scan-label">RS vs SPY</div>
             <div style="font-family:'IBM Plex Mono',monospace;font-size:0.9rem;font-weight:600;
                  color:{'#00d4aa' if rs>1 else '#ef4444'};">{rs:+.2f}</div></div>
        <div><div class="scan-label">Vol Ratio</div>
             <div style="font-family:'IBM Plex Mono',monospace;font-size:0.9rem;font-weight:600;
                  color:{'#f59e0b' if vol_spike else '#e0e6f0'};"> {'⚡' if vol_spike else ''}{vol_ratio:.1f}x</div></div>
        <div><div class="scan-label">4W Trend</div>
             <div style="font-family:'IBM Plex Mono',monospace;font-size:0.9rem;font-weight:600;
                  color:{'#00d4aa' if trend_4w>0 else '#ef4444'};"> {'▲' if trend_4w>0 else '▼'} {abs(trend_4w):.1f}%</div></div>
      </div>
      {sr_html}
      {summary_html}
      <div style="margin-top:0.5rem;font-size:0.7rem;font-family:'IBM Plex Mono',monospace;color:#4a5568;">
        📅 {sig_date} &nbsp;{'✅ Buy now' if fresh else '⚠️ Verify'}
        &nbsp;&nbsp;<a href="{tv_url}" target="_blank" style="color:#60a5fa;text-decoration:none;">📊 TradingView Chart →</a>
      </div>
      {bt_html}
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  CHART
# ══════════════════════════════════════════════
def render_chart(ticker, params):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df.empty or len(df) < 50: return
        close = df['Close'].squeeze()
        df['MA20']  = close.rolling(20).mean()
        df['MA50']  = close.rolling(50).mean()
        df['MA200'] = close.rolling(200).mean()
        df['BBm'] = close.rolling(params['bb_period']).mean()
        df['BBs'] = close.rolling(params['bb_period']).std()
        df['BBu'] = df['BBm'] + params['bb_std'] * df['BBs']
        df['BBl'] = df['BBm'] - params['bb_std'] * df['BBs']
        delta = close.diff()
        g = delta.clip(lower=0).rolling(params['rsi_period']).mean()
        l = (-delta.clip(upper=0)).rolling(params['rsi_period']).mean()
        df['RSI'] = 100 - 100 / (1 + g / l)

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7,0.3], vertical_spacing=0.04)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'], name=ticker,
            increasing_line_color='#00d4aa', decreasing_line_color='#ef4444'), row=1, col=1)
        for ma, col, w in [('MA20','#f59e0b',1),('MA50','#60a5fa',1.5),('MA200','#a78bfa',1.5)]:
            fig.add_trace(go.Scatter(x=df.index, y=df[ma], name=ma,
                line=dict(color=col, width=w), opacity=0.8), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBu'], name='BB Upper',
            line=dict(color='#4a5568', width=1, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BBl'], name='BB Lower',
            line=dict(color='#4a5568', width=1, dash='dot'),
            fill='tonexty', fillcolor='rgba(74,85,104,0.08)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI',
            line=dict(color='#f59e0b', width=1.5)), row=2, col=1)
        fig.add_hline(y=40, line_dash="dot", line_color="#00d4aa", opacity=0.5, row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#ef4444", opacity=0.5, row=2, col=1)
        fig.update_layout(
            plot_bgcolor='#111827', paper_bgcolor='#0a0e1a',
            font=dict(color='#e0e6f0', family='IBM Plex Mono'),
            xaxis_rangeslider_visible=False, height=500,
            margin=dict(l=10,r=10,t=30,b=10),
            title=dict(text=f"{ticker} — 6M Chart", font=dict(color='#00d4aa', size=14)),
            legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=9)))
        fig.update_xaxes(gridcolor='#1e293b')
        fig.update_yaxes(gridcolor='#1e293b')
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Chart error: {e}")


# ══════════════════════════════════════════════
#  BACKTEST RESULTS PANEL
# ══════════════════════════════════════════════
def render_backtest_panel(bt_data):
    st.markdown("### 📊 Backtest Results — 12 months, scanned stocks only")
    overall   = bt_data.get('overall', {})
    per_stock = bt_data.get('per_stock', {})

    total = overall.get('total_trades', 0)
    wins  = overall.get('wins', 0)
    loss  = overall.get('losses', 0)
    wr    = overall.get('win_rate', 0)
    avg_r = overall.get('avg_return', 0)
    best  = overall.get('best_trade', 0)
    worst = overall.get('worst_trade', 0)
    wc    = "#00d4aa" if wr >= 60 else "#f59e0b" if wr >= 45 else "#ef4444"

    cols = st.columns(6)
    for col, lbl, val, clr in zip(cols, [
        "Total Trades","✅ Wins","❌ Losses","Win Rate","Avg Return","Best / Worst"
    ],[str(total), str(wins), str(loss), f"{wr:.1f}%",
       f"{avg_r:+.2f}%", f"{best:+.1f}% / {worst:+.1f}%"],
    ["#e0e6f0","#00d4aa","#ef4444", wc,
     "#00d4aa" if avg_r>=0 else "#ef4444", "#e0e6f0"]):
        col.markdown(
            f'<div class="metric-card"><div class="scan-label">{lbl}</div>'
            f'<div class="scan-stat" style="color:{clr};font-size:1.3rem;">{val}</div></div>',
            unsafe_allow_html=True)

    if per_stock:
        st.markdown("#### Per-Stock Statistics")
        rows = []
        for ticker, s in per_stock.items():
            rows.append({
                "Ticker":       ticker,
                "Trades":       s.get('total_trades', 0),
                "Wins":         s.get('wins', 0),
                "Losses":       s.get('losses', 0),
                "Win Rate":     f"{s.get('win_rate',0):.0f}%",
                "Avg Return":   f"{s.get('avg_return',0):+.2f}%",
                "Best Trade":   f"{s.get('best_trade',0):+.1f}%",
                "Worst Trade":  f"{s.get('worst_trade',0):+.1f}%",
                "Avg Hold (d)": s.get('avg_hold_days', 0),
            })
        df = pd.DataFrame(rows).sort_values("Win Rate", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("📋 Full Trade Log"):
        log = bt_data.get('trade_log', [])
        if log:
            st.dataframe(pd.DataFrame(log), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════
#  NEWS INTELLIGENCE PANEL
# ══════════════════════════════════════════════
def render_news_intelligence():
    st.markdown("### 🧠 AI News Intelligence")

    ni_tab1, ni_tab2 = st.tabs(["📰 News Analysis", "😨 VIX Spike History"])

    with ni_tab1:
        st.caption("Reads news from Yahoo Finance, Google News, Seeking Alpha, Bizportal, Calcalist")
        if st.button("🔍 Analyze Today's News", use_container_width=True, key="ni_btn"):
            with st.spinner("Fetching from all news sources + AI analysis..."):
                result = run_news_intelligence()
                st.session_state['news_intel'] = result

        result = st.session_state.get('news_intel')
        if not result:
            st.info("Press the button above to analyze today's market news from multiple sources.")
            return

        if result.get('error'):
            st.error(result['error'])
            return

        ts = result.get('timestamp')
        ts_str = ts.strftime('%H:%M:%S 🇮🇱') if hasattr(ts, 'strftime') else str(ts)
        src_count = result.get('source_count', 0)
        macro = result.get('macro_signal', 'NEUTRAL')
        macro_col = "#00d4aa" if macro == "BULLISH" else "#ef4444" if macro == "BEARISH" else "#f59e0b"

        st.markdown(f"""
        <div style="display:flex;gap:1rem;align-items:center;margin-bottom:0.8rem;">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:#4a5568;">🕐 {ts_str}</span>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:#4a5568;">📡 {src_count} sources</span>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:{macro_col};
                border:1px solid {macro_col};border-radius:4px;padding:0.1rem 0.4rem;">
            {macro}
          </span>
        </div>""", unsafe_allow_html=True)

        summary = result.get('summary', '')
        if summary:
            st.markdown(f'<div style="background:#111827;border:1px solid #1e293b;border-left:4px solid #00d4aa;'
                        f'border-radius:8px;padding:1rem 1.2rem;margin:0.8rem 0;">'
                        f'<div style="font-size:0.75rem;color:#4a5568;text-transform:uppercase;letter-spacing:1px;'
                        f'margin-bottom:0.4rem;">📰 Market Summary</div>'
                        f'<div style="color:#e0e6f0;font-size:0.92rem;line-height:1.6;">{summary}</div>'
                        f'</div>', unsafe_allow_html=True)

        themes = result.get('key_themes', [])
        if themes:
            html = " ".join(
                f'<span style="background:rgba(59,130,246,0.15);color:#60a5fa;border:1px solid rgba(59,130,246,0.3);'
                f'border-radius:4px;padding:0.2rem 0.6rem;font-size:0.75rem;margin:0.1rem;display:inline-block;">{t}</span>'
                for t in themes)
            st.markdown(f'<div style="margin:0.5rem 0;">{html}</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        for col, title, items, border_c in [
            (col1, "🟢 WATCH", result.get('watch', []), "#00d4aa"),
            (col2, "🔴 AVOID", result.get('avoid', []), "#ef4444"),
        ]:
            with col:
                st.markdown(f"#### {title}")
                if not items:
                    st.info("No signals.")
                for item in items:
                    conf = item.get('confidence', 'LOW')
                    cc   = border_c if conf == "HIGH" else "#f59e0b" if conf == "MEDIUM" else "#6b7280"
                    st.markdown(
                        f'<div style="background:#111827;border:1px solid #1e293b;border-left:3px solid {border_c};'
                        f'border-radius:8px;padding:0.8rem 1rem;margin:0.35rem 0;">'
                        f'<div style="display:flex;justify-content:space-between;">'
                        f'<span style="font-family:IBM Plex Mono,monospace;font-size:1.1rem;font-weight:700;color:{border_c};">'
                        f'{item.get("ticker","")}</span>'
                        f'<span style="font-family:IBM Plex Mono,monospace;font-size:0.72rem;color:{cc};'
                        f'border:1px solid {cc};border-radius:4px;padding:0.1rem 0.4rem;">{conf}</span></div>'
                        f'<div style="color:#9ca3af;font-size:0.78rem;margin-top:0.2rem;">{item.get("theme","")}</div>'
                        f'<div style="color:#e0e6f0;font-size:0.82rem;margin-top:0.2rem;">{item.get("reason","")}</div>'
                        f'</div>', unsafe_allow_html=True)

        with st.expander(f"📋 Headlines ({len(result.get('headlines',[]))})"):
            for h in result.get('headlines', [])[:30]:
                src_badge = f'<span style="background:rgba(59,130,246,0.1);color:#60a5fa;font-size:0.68rem;' \
                            f'border-radius:3px;padding:0.1rem 0.3rem;margin-right:0.3rem;">{h.get("source","")}</span>'
                st.markdown(
                    f'<div style="padding:0.3rem 0;border-bottom:1px solid #1e293b;">'
                    f'{src_badge}'
                    f'<span style="color:#4a5568;font-size:0.7rem;">{h.get("published","")}</span> '
                    f'<a href="{h.get("url","#")}" target="_blank" style="color:#60a5fa;font-size:0.82rem;">'
                    f'{h.get("title","")}</a></div>', unsafe_allow_html=True)

    with ni_tab2:
        st.markdown("### 😨 When Fear Spikes — What Happened to Stocks?")
        st.caption("Historical analysis: stocks that rose/fell when VIX crossed a threshold")

        col_a, col_b = st.columns(2)
        with col_a:
            vix_thresh = st.slider("VIX Threshold", 20.0, 45.0, 25.0, 0.5)
        with col_b:
            fwd_days = st.slider("Forward days", 3, 30, 10)

        if st.button("🔍 Analyze VIX Spikes", use_container_width=True, key="vix_btn"):
            with st.spinner(f"Analyzing historical VIX spikes above {vix_thresh}..."):
                vix_result = run_vix_analysis(vix_thresh, fwd_days)
                st.session_state['vix_analysis'] = vix_result

        vr = st.session_state.get('vix_analysis')
        if not vr:
            st.info("Press the button above to run historical analysis")
            return

        if vr.get('error'):
            st.error(vr['error'])
            return

        st.markdown(f"""
        <div style="background:#111827;border:1px solid #1e293b;border-radius:8px;padding:1rem;margin-bottom:1rem;">
          <span style="font-family:'IBM Plex Mono',monospace;color:#f59e0b;font-size:1rem;">
            Current VIX: {vr.get('current_vix','?')} &nbsp;|&nbsp;
            VIX crossed {vr.get('threshold','?')} a total of {vr.get('total_spikes',0)} times in the last 2 years
          </span><br>
          <span style="font-size:0.78rem;color:#4a5568;">
            Spike dates: {', '.join(vr.get('spike_dates',[])[-5:])}
          </span>
        </div>""", unsafe_allow_html=True)

        if vr.get('message'):
            st.info(vr['message'])
            return

        cv1, cv2 = st.columns(2)
        with cv1:
            st.markdown(f"#### 🟢 Winners — {fwd_days} days after VIX spike")
            for item in vr.get('winners', []):
                t, r = item['ticker'], item['avg_return']
                badge = "🛡️ defensive" if item.get('type') == 'safe_haven' else ""
                st.markdown(
                    f'<div style="background:#111827;border-left:3px solid #00d4aa;border-radius:6px;'
                    f'padding:0.5rem 0.8rem;margin:0.25rem 0;display:flex;justify-content:space-between;">'
                    f'<span style="font-family:IBM Plex Mono,monospace;color:#00d4aa;font-weight:700;">{t}</span>'
                    f'<span style="font-family:IBM Plex Mono,monospace;color:#00d4aa;">{r:+.1f}% {badge}</span>'
                    f'</div>', unsafe_allow_html=True)

        with cv2:
            st.markdown(f"#### 🔴 Losers — {fwd_days} days after VIX spike")
            for item in vr.get('losers', []):
                t, r = item['ticker'], item['avg_return']
                st.markdown(
                    f'<div style="background:#111827;border-left:3px solid #ef4444;border-radius:6px;'
                    f'padding:0.5rem 0.8rem;margin:0.25rem 0;display:flex;justify-content:space-between;">'
                    f'<span style="font-family:IBM Plex Mono,monospace;color:#ef4444;font-weight:700;">{t}</span>'
                    f'<span style="font-family:IBM Plex Mono,monospace;color:#ef4444;">{r:+.1f}%</span>'
                    f'</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════
def main():
    st.markdown('<div class="main-header">📈 MURPHY STOCK SCANNER</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Live Screener · Murphy Method · Signal Backtester</div>', unsafe_allow_html=True)

    vix    = render_market_bar()
    params = render_sidebar()

    if vix >= 30:
        st.error("🚫 **VIX above 30 — Emergency! Cash, Gold (GLD), Short Treasuries (SHY) only. Do NOT buy stocks.**")
    elif vix >= 20:
        st.warning("⚠️ **VIX 20–30 — Rotate to defensives: Utilities (XLU), Healthcare (XLV), Consumer Staples (XLP). Avoid high-beta tech.**")

    for k in ['scan_results', 'backtest_results']:
        if k not in st.session_state:
            st.session_state[k] = None

    # ── DEBUG single ticker ────────────────────────────────
    if params.get('run_debug') and params.get('debug_ticker'):
        t = params['debug_ticker']
        with st.spinner(f"Debugging {t}..."):
            msg = debug_ticker(t, params)
        st.info(msg)

    # ── STEP 1: SCAN ──────────────────────────────────────
    if params['run_scan']:
        import random, time
        random.seed(int(time.time()))  # different seed every scan
        universe_pool = STOCK_UNIVERSE.copy()
        random.shuffle(universe_pool)
        max_s = params['max_stocks']
        universe = universe_pool[:max_s] if max_s < len(universe_pool) else universe_pool
        st.info(f"🔍 Scanning {len(universe)} stocks...")
        pb = st.progress(0)
        st_txt = st.empty()
        lock_results = []

        for i, ticker in enumerate(universe):
            pb.progress((i + 1) / len(universe))
            st_txt.caption(f"Scanning {ticker}… ({i+1}/{len(universe)}) — found: {len(lock_results)}")
            try:
                r = calculate_indicators(ticker, params)
                if r and r.get('passes_filter'):
                    lock_results.append(r)
            except Exception:
                pass

        lock_results.sort(key=lambda x: (-x.get('score', 0), x.get('ticker', '')))
        st.session_state.scan_results     = lock_results
        st.session_state.backtest_results = None
        pb.empty(); st_txt.empty()

        if len(lock_results) == 0:
            st.warning("⚠️ 0 stocks passed. Try: RSI Max=60, uncheck MA200/MA50, Min Beta=0, Min Institutional=0")


    # ── STEP 2: BACKTEST (only scanned stocks) ─────────────
    if params['run_backtest']:
        scan_res = st.session_state.scan_results
        if not scan_res:
            st.warning("⚠️ Run Step 1 first!")
        else:
            tickers = [r['ticker'] for r in scan_res]
            st.info(f"📊 Backtesting {len(tickers)} stocks with RSI range {params.get('rsi_min',0)}–{params.get('rsi_max',90)}…")
            pb2 = st.progress(0)
            st2 = st.empty()
            bt = run_backtest_on_screened(tickers, params, pb2, st2)
            st.session_state.backtest_results = bt
            pb2.empty(); st2.empty()
            # Show note if 0 trades
            note = bt.get('note','')
            if note:
                st.warning(f"⚠️ {note}")

    # ── DISPLAY ───────────────────────────────────────────
    results = st.session_state.scan_results
    bt_data = st.session_state.backtest_results

    if results is not None:
        if not results:
            st.info("No stocks matched filters. Try relaxing RSI or BB thresholds.")
        else:
            st.markdown("---")
            c1, c2, c3, c4 = st.columns(4)
            strong   = sum(1 for r in results if r.get('score',0) >= 7)
            avg_rsi  = np.mean([r.get('rsi',0) for r in results])
            below_bb = sum(1 for r in results if r.get('bb_pct',1) < 0.2)
            for col, lbl, val in [(c1,"Stocks Found",str(len(results))),
                                   (c2,"Strong ≥7",str(strong)),
                                   (c3,"Avg RSI",f"{avg_rsi:.1f}"),
                                   (c4,"Near BB Lower",str(below_bb))]:
                col.markdown(f'<div class="metric-card"><div class="scan-label">{lbl}</div>'
                              f'<div class="scan-stat">{val}</div></div>', unsafe_allow_html=True)
            st.markdown("---")

            # VIX Regime priority panel
            try:
                from screener import VIX_REGIMES, get_vix_regime
                vix_val = data.get("VIX", {}).get("value", 0) if 'data' in dir() else 0
                try:
                    vix_hist = yf.Ticker("^VIX").history(period="2d", interval="1d", actions=False)
                    vix_val  = float(vix_hist['Close'].iloc[-1]) if not vix_hist.empty else vix_val
                except Exception:
                    pass
                regime_key  = get_vix_regime(vix_val)
                regime      = VIX_REGIMES[regime_key]
                priority_found = [r for r in results if r.get('vix_priority')]
                if priority_found:
                    st.markdown(f"""
                    <div style="background:#111827;border:1px solid #1e293b;border-left:4px solid {regime['color']};
                                border-radius:8px;padding:0.8rem 1.2rem;margin-bottom:0.8rem;">
                      <div style="font-size:0.75rem;color:#4a5568;text-transform:uppercase;letter-spacing:1px;">
                        ⭐ VIX REGIME PRIORITY — {regime['label']}
                      </div>
                      <div style="font-size:0.82rem;color:{regime['color']};margin-top:0.3rem;">{regime['desc']}</div>
                      <div style="font-family:'IBM Plex Mono',monospace;font-size:0.85rem;margin-top:0.4rem;color:#e0e6f0;">
                        {' · '.join(r['ticker'] for r in priority_found[:10])}
                      </div>
                    </div>""", unsafe_allow_html=True)
            except Exception:
                pass

            cf1, cf2, cf3 = st.columns(3)
            with cf1: min_score  = st.slider("Min Score", 0, 10, 0)
            with cf2: sort_by    = st.selectbox("Sort by", ["Score","RSI (lowest)","Win Rate (backtest)"])
            with cf3: fresh_only = st.checkbox("Fresh signals only", value=False)

            filtered = [r for r in results if r.get('score',0) >= min_score]
            if fresh_only:
                filtered = [r for r in filtered if r.get('signal_fresh', False)]
            st.caption(f"🔍 Passed screener: {len(results)} stocks | Showing: {len(filtered)}")
            if sort_by == "RSI (lowest)":
                filtered.sort(key=lambda x: x.get('rsi',100))
            elif sort_by == "Win Rate (backtest)" and bt_data:
                ps = bt_data.get('per_stock', {})
                filtered.sort(key=lambda x: ps.get(x['ticker'],{}).get('win_rate',0), reverse=True)

            st.markdown(f"### 🎯 {len(filtered)} Opportunities")

            t1, t2, t3, t4, t5 = st.tabs(["📋 Stocks", "📈 Charts", "📰 News", "🧠 AI News Intel", "📊 Backtest"])

            with t1:
                for stock in filtered:
                    bts = bt_data.get('per_stock',{}).get(stock['ticker']) if bt_data else None
                    render_stock_card(stock, bts)

            with t2:
                if filtered:
                    sel = st.selectbox("Chart", [r['ticker'] for r in filtered[:30]])
                    if sel: render_chart(sel, params)

            with t3:
                if filtered:
                    sn = st.selectbox("News for", [r['ticker'] for r in filtered[:30]], key="ns")
                    if sn:
                        with st.spinner("Fetching…"):
                            news = fetch_news(sn)
                        for item in news:
                            st.markdown(
                                f'<div class="news-item">'
                                f'<a href="{item.get("url","#")}" target="_blank" class="news-title">{item.get("title","")}</a>'
                                f'<div class="news-meta">{item.get("publisher","")} · {item.get("published","")}</div>'
                                f'</div>', unsafe_allow_html=True)
                        if not news: st.info("No news found.")

            with t4:
                render_news_intelligence()

            with t5:
                if bt_data:
                    render_backtest_panel(bt_data)
                else:
                    st.info("Press **STEP 2 — BACKTEST** in the sidebar after scanning.")
    else:
        st.markdown("""
        <div style="text-align:center;padding:5rem 2rem;color:#4a5568;">
          <div style="font-size:3.5rem;margin-bottom:1rem;">📡</div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:1.1rem;color:#6b7280;">
            Press <b style="color:#00d4aa;">STEP 1 — RUN SCAN</b> to start
          </div>
          <div style="font-size:0.82rem;margin-top:0.5rem;">
            Then STEP 2 to backtest the scanned stocks only
          </div>
        </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()

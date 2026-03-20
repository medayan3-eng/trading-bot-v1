import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

from screener import run_screener, calculate_indicators
from backtester import run_backtest
from news_fetcher import fetch_news
from stock_universe import STOCK_UNIVERSE

st.set_page_config(
    page_title="Murphy Stock Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }
    
    .stApp {
        background: #0a0e1a;
        color: #e0e6f0;
    }
    
    .main-header {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2.2rem;
        font-weight: 600;
        color: #00d4aa;
        letter-spacing: -1px;
        margin-bottom: 0.2rem;
    }
    
    .sub-header {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        color: #4a5568;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 1.2rem;
        margin: 0.3rem 0;
        border-left: 3px solid #00d4aa;
    }
    
    .stock-card {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        transition: all 0.2s ease;
    }
    
    .stock-card:hover {
        border-color: #00d4aa;
        box-shadow: 0 0 20px rgba(0, 212, 170, 0.1);
    }
    
    .signal-strong { color: #00d4aa; font-weight: 600; }
    .signal-medium { color: #f59e0b; font-weight: 600; }
    .signal-weak { color: #ef4444; font-weight: 600; }
    
    .ticker-symbol {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.4rem;
        font-weight: 600;
        color: #00d4aa;
    }
    
    .price-display {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.1rem;
        color: #e0e6f0;
    }
    
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
        margin: 0.1rem;
    }
    
    .badge-green { background: rgba(0,212,170,0.15); color: #00d4aa; border: 1px solid rgba(0,212,170,0.3); }
    .badge-yellow { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }
    .badge-red { background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }
    .badge-blue { background: rgba(59,130,246,0.15); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); }
    
    div[data-testid="stSidebar"] {
        background: #0d1117;
        border-right: 1px solid #1e293b;
    }
    
    .stButton > button {
        background: #00d4aa;
        color: #0a0e1a;
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
        border: none;
        border-radius: 6px;
        padding: 0.6rem 1.5rem;
        letter-spacing: 0.5px;
        width: 100%;
    }
    
    .stButton > button:hover {
        background: #00b894;
        transform: translateY(-1px);
    }
    
    .scan-stat {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2rem;
        font-weight: 600;
        color: #00d4aa;
    }
    
    .scan-label {
        font-size: 0.75rem;
        color: #4a5568;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    hr { border-color: #1e293b; }
    
    .stDataFrame { background: #111827; }
    
    .news-item {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.4rem 0;
        border-left: 3px solid #3b82f6;
    }
    
    .news-title {
        color: #60a5fa;
        font-size: 0.9rem;
        font-weight: 600;
        text-decoration: none;
    }
    
    .news-meta {
        color: #4a5568;
        font-size: 0.75rem;
        font-family: 'IBM Plex Mono', monospace;
        margin-top: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)


def render_header():
    st.markdown('<div class="main-header">📈 MURPHY STOCK SCANNER</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Technical Screener · Oversold Opportunities · Murphy Method</div>', unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ Scan Parameters")
        st.markdown("---")
        
        min_price = st.slider("Min Price ($)", 15, 100, 15)
        min_volume = st.number_input("Min Avg Volume (M)", min_value=0.1, max_value=10.0, value=0.5, step=0.1)
        min_beta = st.slider("Min Beta", 0.5, 3.0, 1.0, 0.1)
        
        st.markdown("---")
        st.markdown("**RSI Settings**")
        rsi_max = st.slider("RSI Max (oversold)", 20, 50, 40)
        rsi_period = st.number_input("RSI Period", min_value=5, max_value=20, value=14)
        
        st.markdown("---")
        st.markdown("**Trend Filters**")
        require_above_200 = st.checkbox("Above MA200", value=True)
        require_above_50 = st.checkbox("Above MA50", value=True)
        require_above_20 = st.checkbox("Above MA20 (optional)", value=False)
        
        st.markdown("---")
        st.markdown("**Bollinger Bands**")
        bb_period = st.number_input("BB Period", min_value=10, max_value=30, value=20)
        bb_std = st.slider("BB Std Dev", 1.5, 3.0, 2.0, 0.1)
        
        st.markdown("---")
        max_stocks = st.slider("Max stocks to scan", 50, 500, 200)
        
        run_scan = st.button("🔍 RUN SCAN", use_container_width=True)
        
        st.markdown("---")
        st.markdown("**Backtest (1 Year)**")
        run_bt = st.button("📊 BACKTEST SIGNALS", use_container_width=True)
        
        return {
            "min_price": min_price,
            "min_volume": min_volume * 1_000_000,
            "min_beta": min_beta,
            "rsi_max": rsi_max,
            "rsi_period": int(rsi_period),
            "require_above_200": require_above_200,
            "require_above_50": require_above_50,
            "require_above_20": require_above_20,
            "bb_period": int(bb_period),
            "bb_std": bb_std,
            "max_stocks": max_stocks,
            "run_scan": run_scan,
            "run_backtest": run_bt
        }


def render_stock_card(stock):
    score = stock.get('score', 0)
    signal_class = "signal-strong" if score >= 7 else "signal-medium" if score >= 5 else "signal-weak"
    
    rsi = stock.get('rsi', 0)
    price = stock.get('price', 0)
    ma50 = stock.get('ma50', 0)
    ma200 = stock.get('ma200', 0)
    bb_pct = stock.get('bb_pct', 0.5)
    trend_4w = stock.get('trend_4w', 0)
    beta = stock.get('beta', 0)
    volume_ratio = stock.get('volume_ratio', 1)
    
    badges = []
    if stock.get('above_200'): badges.append('<span class="badge badge-green">MA200 ✓</span>')
    if stock.get('above_50'): badges.append('<span class="badge badge-green">MA50 ✓</span>')
    if stock.get('above_20'): badges.append('<span class="badge badge-blue">MA20 ✓</span>')
    if rsi < 30: badges.append('<span class="badge badge-red">RSI EXTREME</span>')
    elif rsi < 40: badges.append('<span class="badge badge-yellow">RSI OVERSOLD</span>')
    if bb_pct < 0.2: badges.append('<span class="badge badge-green">BB LOWER ✓</span>')
    if trend_4w > 0: badges.append('<span class="badge badge-green">4W UPTREND</span>')
    
    html = f"""
    <div class="stock-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <div class="ticker-symbol">{stock['ticker']}</div>
                <div style="color:#6b7280; font-size:0.8rem; margin-top:0.2rem;">{stock.get('name','')}</div>
            </div>
            <div style="text-align:right;">
                <div class="price-display">${price:.2f}</div>
                <div class="{signal_class}" style="font-size:0.85rem;">Score: {score}/10</div>
            </div>
        </div>
        <div style="margin: 0.8rem 0;">
            {''.join(badges)}
        </div>
        <div style="display:grid; grid-template-columns: repeat(4,1fr); gap:0.5rem; margin-top:0.8rem;">
            <div>
                <div class="scan-label">RSI(14)</div>
                <div style="font-family:'IBM Plex Mono',monospace; color:{'#ef4444' if rsi<30 else '#f59e0b' if rsi<40 else '#e0e6f0'}; font-size:1rem; font-weight:600;">{rsi:.1f}</div>
            </div>
            <div>
                <div class="scan-label">Beta</div>
                <div style="font-family:'IBM Plex Mono',monospace; color:#00d4aa; font-size:1rem; font-weight:600;">{beta:.2f}</div>
            </div>
            <div>
                <div class="scan-label">BB%</div>
                <div style="font-family:'IBM Plex Mono',monospace; color:{'#00d4aa' if bb_pct<0.2 else '#e0e6f0'}; font-size:1rem; font-weight:600;">{bb_pct:.2f}</div>
            </div>
            <div>
                <div class="scan-label">4W Trend</div>
                <div style="font-family:'IBM Plex Mono',monospace; color:{'#00d4aa' if trend_4w>0 else '#ef4444'}; font-size:1rem; font-weight:600;">{'▲' if trend_4w>0 else '▼'} {abs(trend_4w):.1f}%</div>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_chart(ticker, params):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df.empty or len(df) < 50:
            return
        
        df = df.copy()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA50'] = df['Close'].rolling(50).mean()
        df['MA200'] = df['Close'].rolling(200).mean()
        
        # Bollinger Bands
        bb_period = params['bb_period']
        df['BB_mid'] = df['Close'].rolling(bb_period).mean()
        df['BB_std'] = df['Close'].rolling(bb_period).std()
        df['BB_upper'] = df['BB_mid'] + params['bb_std'] * df['BB_std']
        df['BB_lower'] = df['BB_mid'] - params['bb_std'] * df['BB_std']
        
        # RSI
        rsi_p = params['rsi_period']
        delta = df['Close'].diff()
        gain = delta.clip(lower=0).rolling(rsi_p).mean()
        loss = (-delta.clip(upper=0)).rolling(rsi_p).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                           row_heights=[0.7, 0.3],
                           vertical_spacing=0.05)
        
        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'], name=ticker,
            increasing_line_color='#00d4aa', decreasing_line_color='#ef4444'
        ), row=1, col=1)
        
        # MAs
        for ma, color, width in [('MA20','#f59e0b',1), ('MA50','#60a5fa',1.5), ('MA200','#a78bfa',1.5)]:
            if ma in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df[ma], name=ma,
                    line=dict(color=color, width=width), opacity=0.8), row=1, col=1)
        
        # BB
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_upper'], name='BB Upper',
            line=dict(color='#4a5568', width=1, dash='dot'), opacity=0.7), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_lower'], name='BB Lower',
            line=dict(color='#4a5568', width=1, dash='dot'),
            fill='tonexty', fillcolor='rgba(74,85,104,0.1)', opacity=0.7), row=1, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI',
            line=dict(color='#f59e0b', width=1.5)), row=2, col=1)
        fig.add_hline(y=40, line_dash="dot", line_color="#00d4aa", opacity=0.5, row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#ef4444", opacity=0.5, row=2, col=1)
        
        fig.update_layout(
            plot_bgcolor='#111827', paper_bgcolor='#0a0e1a',
            font=dict(color='#e0e6f0', family='IBM Plex Mono'),
            xaxis_rangeslider_visible=False,
            legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=10)),
            height=500,
            margin=dict(l=10, r=10, t=30, b=10),
            title=dict(text=f"{ticker} — 6M Chart", font=dict(color='#00d4aa', size=14))
        )
        fig.update_xaxes(gridcolor='#1e293b', showgrid=True)
        fig.update_yaxes(gridcolor='#1e293b', showgrid=True)
        
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Chart error: {e}")


def render_backtest_results(results):
    st.markdown("### 📊 Backtest Results — Last 12 Months")
    
    if not results:
        st.warning("No backtest results available.")
        return
    
    total = results.get('total', 0)
    correct_buy = results.get('correct_buy', 0)
    correct_sell = results.get('correct_sell', 0)
    wrong = results.get('wrong', 0)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="scan-label">Total Signals</div><div class="scan-stat">{total}</div></div>', unsafe_allow_html=True)
    with col2:
        pct = correct_buy/total*100 if total else 0
        st.markdown(f'<div class="metric-card"><div class="scan-label">Correct Buy</div><div class="scan-stat" style="color:#00d4aa">{correct_buy} ({pct:.0f}%)</div></div>', unsafe_allow_html=True)
    with col3:
        pct2 = correct_sell/total*100 if total else 0
        st.markdown(f'<div class="metric-card"><div class="scan-label">Correct Sell</div><div class="scan-stat" style="color:#00d4aa">{correct_sell} ({pct2:.0f}%)</div></div>', unsafe_allow_html=True)
    with col4:
        pct3 = wrong/total*100 if total else 0
        st.markdown(f'<div class="metric-card"><div class="scan-label">Wrong</div><div class="scan-stat" style="color:#ef4444">{wrong} ({pct3:.0f}%)</div></div>', unsafe_allow_html=True)
    
    if results.get('details'):
        st.markdown("#### Signal Details")
        df = pd.DataFrame(results['details'])
        st.dataframe(df, use_container_width=True, hide_index=True)


# ─────────────────────────────── MAIN ────────────────────────────────
def main():
    render_header()
    params = render_sidebar()
    
    if 'scan_results' not in st.session_state:
        st.session_state.scan_results = []
    if 'backtest_results' not in st.session_state:
        st.session_state.backtest_results = None
    
    # Run scan
    if params['run_scan']:
        universe = STOCK_UNIVERSE[:params['max_stocks']]
        
        with st.spinner(f"🔍 Scanning {len(universe)} stocks..."):
            progress_bar = st.progress(0)
            results = []
            
            def scan_single(ticker):
                try:
                    return calculate_indicators(ticker, params)
                except:
                    return None
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(scan_single, t): t for t in universe}
                completed = 0
                for future in as_completed(futures):
                    completed += 1
                    progress_bar.progress(completed / len(universe))
                    result = future.result()
                    if result and result.get('passes_filter', False):
                        results.append(result)
            
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
            st.session_state.scan_results = results
            progress_bar.empty()
    
    # Run backtest
    if params['run_backtest']:
        universe = STOCK_UNIVERSE[:100]
        with st.spinner("📊 Running backtest on 1 year of data..."):
            bt_results = run_backtest(universe[:50], params)
            st.session_state.backtest_results = bt_results
    
    # Display
    results = st.session_state.scan_results
    
    if results:
        # Summary stats
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="metric-card"><div class="scan-label">Stocks Found</div><div class="scan-stat">{len(results)}</div></div>', unsafe_allow_html=True)
        with col2:
            strong = sum(1 for r in results if r.get('score', 0) >= 7)
            st.markdown(f'<div class="metric-card"><div class="scan-label">Strong Signals</div><div class="scan-stat" style="color:#00d4aa">{strong}</div></div>', unsafe_allow_html=True)
        with col3:
            avg_rsi = np.mean([r.get('rsi', 0) for r in results])
            st.markdown(f'<div class="metric-card"><div class="scan-label">Avg RSI</div><div class="scan-stat" style="color:#f59e0b">{avg_rsi:.1f}</div></div>', unsafe_allow_html=True)
        with col4:
            below_bb = sum(1 for r in results if r.get('bb_pct', 1) < 0.2)
            st.markdown(f'<div class="metric-card"><div class="scan-label">Near BB Lower</div><div class="scan-stat">{below_bb}</div></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Filter controls
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            min_score = st.slider("Min Score Filter", 0, 10, 5)
        with col_f2:
            sort_by = st.selectbox("Sort By", ["Score", "RSI (lowest)", "Price"])
        
        filtered = [r for r in results if r.get('score', 0) >= min_score]
        
        if sort_by == "RSI (lowest)":
            filtered.sort(key=lambda x: x.get('rsi', 100))
        elif sort_by == "Price":
            filtered.sort(key=lambda x: x.get('price', 0), reverse=True)
        
        st.markdown(f"### 🎯 {len(filtered)} Opportunities Found")
        
        tabs = st.tabs(["📋 List View", "📈 Charts", "📰 News"])
        
        with tabs[0]:
            for stock in filtered:
                render_stock_card(stock)
        
        with tabs[1]:
            if filtered:
                selected = st.selectbox("Select stock for chart", [r['ticker'] for r in filtered[:20]])
                if selected:
                    render_chart(selected, params)
        
        with tabs[2]:
            if filtered:
                selected_news = st.selectbox("Select stock for news", [r['ticker'] for r in filtered[:20]], key="news_select")
                if selected_news:
                    with st.spinner("Fetching news..."):
                        news = fetch_news(selected_news)
                    if news:
                        for item in news:
                            st.markdown(f"""
                            <div class="news-item">
                                <a href="{item.get('url','#')}" target="_blank" class="news-title">{item.get('title','')}</a>
                                <div class="news-meta">{item.get('publisher','')} · {item.get('published','')}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No news found for this ticker.")
    
    elif not params['run_scan']:
        st.markdown("""
        <div style="text-align:center; padding: 5rem 2rem; color: #4a5568;">
            <div style="font-size:4rem; margin-bottom:1rem;">📡</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:1.2rem; color:#6b7280;">
                Configure parameters and press RUN SCAN
            </div>
            <div style="font-size:0.85rem; margin-top:0.5rem;">
                Murphy Method · RSI Oversold · Trend Following
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Backtest results
    if st.session_state.backtest_results:
        st.markdown("---")
        render_backtest_results(st.session_state.backtest_results)


if __name__ == "__main__":
    main()

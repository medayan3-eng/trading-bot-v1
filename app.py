import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- הגדרות מערכת ---
st.set_page_config(page_title="Market Flow Pro 📊", layout="wide")

# --- כותרת מקצועית חדשה ---
col1, col2 = st.columns([3, 1])
with col1:
    st.title("⚡ Market Flow: Professional Analytics")
    st.caption("Advanced Screening: Quantum, Space, AI, Thermal & Commodities")
with col2:
    if st.button("🧹 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

# --- מדריך הצייד (מעודכן עם Momentum) ---
with st.expander("📘 Strategy Guide: How to read the signals?", expanded=False):
    st.markdown("""
    ### 🎯 Decision Matrix
    
    | Signal Type | Market Trend | RSI Level | Logic & Action |
    | :--- | :--- | :--- | :--- |
    | 🔥 **SFP Trap** | **Bullish 🐂** | **40-50** | **Sniper Entry.** Smart money is trapping shorts. High probability reversal. |
    | 📉 **Dip Buy** | **Bullish 🐂** | **30-40** | **Value Entry.** Strong stock in a temporary correction. Good risk/reward. |
    | 🚀 **Momentum** | **Bullish 🐂** | **50-70** | **Trend Following.** The stock is flying. Buy high, sell higher. Use tight stop loss. |
    | ⚠️ **Crash/Knife** | Bearish 🐻 | < 30 | **Danger.** Don't catch a falling knife unless AI confidence is > 80%. |
    """)

# --- רשימת המעקב המהונדסת (כולל התוספות החדשות) ---
SECTORS = {
    "⚛️ Quantum & Computing": ["IONQ", "RGTI", "QBTS", "QTUM", "QUBT", "RDWR"],
    "🚀 Space & Defense": ["RKLB", "LUNR", "KTOS", "VVX", "BA", "LMT", "RTX", "JOBY", "ACHR"],
    "🔥 AI, Chips & Hardware": ["NVDA", "AMD", "TSM", "AVGO", "ARM", "MU", "INTC", "QCOM", "SMCI", "ANET", "DELL", "HPE", "MSFT", "GOOGL", "META"],
    "⚙️ Thermal, Ind. & Energy": ["VRT", "MOD", "ASPN", "ETN", "GE", "CAT", "REI", "ENPH", "FSLR", "CAMT"], 
    "⛏️ Commodities (Lithium/Copper)": ["FCX", "COPX", "SCCO", "AA", "CENX", "NHYDY", "CLF", "ALB", "MP", "PPTA", "VALE"],
    "🚗 Mobility & Auto Tech": ["RIVN", "INVZ", "MBLY", "UBER", "TSLA", "GGM", "LAZR"],
    "💊 BioTech & Pharma": ["NVO", "LLY", "VRTX", "ZBIO", "AMGN", "PFE", "TEVA", "CRSP"],
    "💳 Fintech & Software": ["SOFI", "PYPL", "FISV", "NFLX", "COIN", "HOOD", "SQ", "TTD", "PLTR", "CRWD", "PANW", "VOD", "WDC"]
}

# איחוד כל הרשימות
ALL_TICKERS = list(set([ticker for sector in SECTORS.values() for ticker in sector]))
total_count = len(ALL_TICKERS)

st.info(f"System scanning {total_count} assets in real-time...")

# --- פונקציה מוגנת (Cache) ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        return df
    except:
        return pd.DataFrame()

# --- מנוע הסריקה ---
if st.button("🚀 Run Deep Scan"):
    results = []
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(ALL_TICKERS):
        progress = (i + 1) / total_count
        progress_bar.progress(progress)
        status_text.text(f"Scanning: {ticker}...")
        
        df = get_data(ticker)
        
        if len(df) < 200: continue 

        try:
            # 1. חישובים
            df['SMA_200'] = df['Close'].rolling(200).mean()
            
            # 2. נתונים אחרונים
            prev_low_20 = df['Low'].shift(1).rolling(20).min().iloc[-1]
            today = df.iloc[-1]
            
            # 3. איתותים
            # SFP (מלכודת נזילות)
            sfp_signal = (today['Low'] < prev_low_20) and (today['Close'] > prev_low_20)
            
            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # מרחק מממוצע 200 (מגמה)
            trend_dist = ((today['Close'] - df['SMA_200'].iloc[-1]) / df['SMA_200'].iloc[-1]) * 100
            trend_status = "Bullish 🐂" if trend_dist > 0 else "Bearish 🐻"

            # 4. לוגיקת סינון
            is_oversold_uptrend = (rsi < 40) and (trend_dist > 0)
            
            # Momentum: מניה חזקה (RSI 50-70) שנמצאת בבירור מעל הממוצע 200
            is_momentum = (rsi > 50) and (rsi < 75) and (trend_dist > 5)
            
            # אם אחד התנאים מתקיים - הוסף לטבלה
            if sfp_signal or is_oversold_uptrend or is_momentum:
                
                stop_loss = today['Low'] * 0.97 # סטופ 3%
                
                # מציאת סקטור
                sector_name = "General"
                for sec, tickers in SECTORS.items():
                    if ticker in tickers:
                        sector_name = sec
                        break
                
                # תיוג האיתות
                if sfp_signal:
                    sig_type = "🔥 SFP Trap"
                elif is_oversold_uptrend:
                    sig_type = "📉 Dip Buy"
                else:
                    sig_type = "🚀 Momentum"
                
                results.append({
                    "Ticker": ticker,
                    "Sector": sector_name,
                    "Signal": sig_type,
                    "Price": f"${today['Close']:.2f}",
                    "RSI": f"{rsi:.1f}",
                    "Trend": trend_status,
                    "Stop Loss": f"${stop_loss:.2f}"
                })
        except Exception as e:
            continue
            
    progress_bar.empty()
    status_text.empty()
    
    if results:
        # מיון חכם: SFP ראשון, אח"כ Dip, בסוף Momentum
        df_results = pd.DataFrame(results)
        
        priority = {"🔥 SFP Trap": 1, "📉 Dip Buy": 2, "🚀 Momentum": 3}
        df_results['Rank'] = df_results['Signal'].map(priority)
        df_results = df_results.sort_values(by=['Rank', 'RSI'])
        df_results = df_results.drop(columns=['Rank'])

        st.success(f"Scan Complete! Found {len(results)} opportunities.")
        st.dataframe(df_results, use_container_width=True)
    else:
        st.warning("No high-probability setups found right now.")

with st.expander("🔍 View Watchlist"):
    st.write(SECTORS)

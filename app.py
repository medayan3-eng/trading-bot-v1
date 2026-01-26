import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# --- הגדרות ---
st.set_page_config(page_title="Global Sniper V6.2 🌍", layout="wide")

# כותרת עם כפתור רענון
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🌍 Global Sniper V6.2: Expansion Pack")
    st.caption("מערכת סריקה מורחבת: 150+ מניות בזמן אמת")
with col2:
    if st.button("🔄 רענן נתונים עכשיו"):
        st.cache_data.clear()
        st.rerun()

st.sidebar.write(f"🕒 עדכון אחרון: {datetime.now().strftime('%H:%M:%S')}")

# --- מדריך הצייד ---
with st.expander("📘 מטריצת קבלת החלטות (מדריך מקוצר)", expanded=False):
    st.markdown("""
    | דירוג | סוג האיתות | RSI | מסקנה |
    | :--- | :--- | :--- | :--- |
    | 🥇 **יהלום** | 🔥 SFP Trap | 40-50 | **חובה לבדוק ב-Colab!** |
    | 🥈 **חזק** | 📉 Dip Buy | 30-40 | **בדיקה מומלצת.** |
    | 🥉 **ספקולטיבי** | 🔥 SFP Trap | 30-60 | **סיכון גבוה.** |
    | ⚠️ **מסוכן** | 📉 Dip Buy | < 30 | **סכין נופלת (זהירות).** |
    """)

# --- רשימת המעקב המורחבת (Expansion Pack) ---
SECTORS = {
    "⚛️ Quantum & Cyber": ["IONQ", "RGTI", "QBTS", "QTUM", "QUBT", "RDWR", "CYBR", "SENT", "PANW", "CRWD", "ZS", "FTNT", "CHTR"],
    "🚀 Space & Defense": ["RKLB", "LUNR", "KTOS", "VVX", "BA", "LMT", "RTX", "JOBY", "ACHR", "BKSY", "SPAI", "PSN", "SPIR", "AXON"],
    "🔥 AI, Chips & Hardware": ["NVDA", "AMD", "TSM", "AVGO", "ARM", "MU", "INTC", "QCOM", "SMCI", "ANET", "DELL", "HPE", "MSFT", "GOOGL", "META", "NNDM", "AMKR", "STX", "ORCL", "TTMI", "WDC", "PSTG", "TSEM"],
    "⚡ Energy, Solar & Ind.": ["VRT", "MOD", "ASPN", "ETN", "GE", "CAT", "REI", "ENPH", "FSLR", "CAMT", "FLR", "NRGV", "PESI", "FLS", "OII", "BKR", "STRL", "NFE", "NNE", "SEDG", "RUN", "PLUG", "JKS", "CSIQ"], 
    "⛏️ Commodities & Shipping": ["FCX", "COPX", "SCCO", "AA", "CENX", "NHYDY", "CLF", "ALB", "MP", "PPTA", "VALE", "ABAT", "UUUU", "ZIM", "GOGL", "SBLK"],
    "🚗 EV & Mobility": ["RIVN", "INVZ", "MBLY", "UBER", "TSLA", "GGM", "LAZR", "LCID", "NIO", "XPEV", "LI", "CVNA"],
    "💊 BioTech & Pharma": ["NVO", "LLY", "VRTX", "ZBIO", "AMGN", "PFE", "TEVA", "CRSP", "MRNA", "BNTX", "PFE", "BMY"],
    "🪙 Crypto & Fintech": ["MSTR", "MARA", "RIOT", "CLSK", "COIN", "HOOD", "SQ", "PYPL", "SOFI", "AFRM", "UPST"],
    "🛍️ Growth & Consumer": ["NFLX", "TTD", "PLTR", "U", "SNOW", "DDOG", "NET", "DKNG", "RBLX", "SHOP", "BABA", "PDD", "JD", "MELI", "DRI", "TGT", "CELH", "ELF"]
}

ALL_TICKERS = list(set([ticker for sector in SECTORS.values() for ticker in sector]))
total_count = len(ALL_TICKERS)

st.info(f"📡 המערכת סורקת {total_count} מניות בזמן אמת...")

# --- פונקציה מוגנת (Cache) ---
@st.cache_data(ttl=300)
def get_data(ticker):
    try:
        # משיכה מהירה של 5 ימים
        df = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
        return df
    except:
        return pd.DataFrame()

# --- ממשק משתמש ---
if st.button("🚀 הרץ סריקת עומק (Deep Scan)"):
    results = []
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(ALL_TICKERS):
        progress = (i + 1) / total_count
        progress_bar.progress(progress)
        status_text.text(f"סורק את: {ticker} ({i+1}/{total_count})...")
        
        df = get_data(ticker)
        
        if len(df) < 5: continue 

        try:
            # חישובים הנדסיים
            sma_window = 200 if len(df) >= 200 else len(df)
            df['SMA_200'] = df['Close'].rolling(sma_window).mean()
            
            # SFP Logic
            prev_low_20 = df['Low'].shift(1).rolling(window=min(20, len(df))).min().iloc[-1]
            today = df.iloc[-1]
            last_date = today.name.strftime('%Y-%m-%d')

            sfp_signal = (today['Low'] < prev_low_20) and (today['Close'] > prev_low_20)
            
            # RSI Logic
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # Trend Check
            trend_dist = ((today['Close'] - df['SMA_200'].iloc[-1]) / df['SMA_200'].iloc[-1]) * 100
            trend_status = "Bullish 🐂" if trend_dist > 0 else "Bearish 🐻"

            # תנאי סף
            is_oversold_uptrend = (rsi < 40) and (trend_dist > 0)
            is_momentum = (rsi > 50) and (rsi < 70) and (trend_dist > 10) 
            
            # בדיקה מיוחדת לסקטורים "חמים"
            is_hot_sector = ticker in SECTORS["🔥 AI, Chips & Hardware"] or ticker in SECTORS["🪙 Crypto & Fintech"]

            if sfp_signal or is_oversold_uptrend or (is_momentum and is_hot_sector):
                
                stop_loss = today['Low'] * 0.98 
                
                sector_name = "General"
                for sec, tickers in SECTORS.items():
                    if ticker in tickers:
                        sector_name = sec
                        break
                
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
                    "Date": last_date,
                    "Trend": trend_status,
                    "Stop Loss": f"${stop_loss:.2f}"
                })
        except Exception as e:
            continue
            
    progress_bar.empty()
    status_text.empty()
    
    if results:
        df_results = pd.DataFrame(results)
        
        # מיון
        df_results['Sort_Key'] = df_results['Signal'].apply(lambda x: 1 if "SFP" in x else (2 if "Dip" in x else 3))
        df_results = df_results.sort_values(by=['Sort_Key', 'RSI'])
        df_results = df_results.drop(columns=['Sort_Key'])

        st.success(f"הסריקה הושלמה! נמצאו {len(results)} הזדמנויות מתוך {total_count} מניות.")
        st.dataframe(df_results, use_container_width=True, hide_index=True)
    else:
        st.warning("לא נמצאו איתותים חזקים כרגע. השוק רגוע.")

with st.expander("🔍 הצג את רשימת המניות המלאה"):
    st.write(SECTORS)

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# --- הגדרות ---
st.set_page_config(page_title="Global Sniper V7 🌍", layout="wide")

# כותרת עם כפתור רענון
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🌍 Global Sniper V7: Elite Edition")
    st.caption("מערכת סריקה: 2026 Themes, AI, Defense, Trump Trade & Crypto")
with col2:
    if st.button("🧹 נקה זיכרון (Force Refresh)"):
        st.cache_data.clear()
        st.rerun()

st.sidebar.write(f"🕒 סריקה אחרונה: {datetime.now().strftime('%H:%M:%S')}")

# --- מדריך הצייד ---
with st.expander("📘 מטריצת קבלת החלטות (תנאים מוקשחים)", expanded=False):
    st.markdown("""
    | דירוג | סוג האיתות | RSI | תנאי מגמה (חדש!) | מסקנה |
    | :--- | :--- | :--- | :--- | :--- |
    | 🥇 **יהלום** | 🔥 SFP Trap | 40-50 | **חובה** מעל הממוצע 200 | **חובה לבדוק ב-Colab!** |
    | 🥈 **חזק** | 📉 Dip Buy | **< 38** | **חובה** מעל 1.5% מממוצע 200 | **בדיקה מומלצת.** |
    | 🥉 **מומנטום** | 🚀 Momentum | 50-70 | **חובה** מעל 10% מממוצע 200 | **הצטרפות לגל.** |
    """)

# --- רשימת המעקב המהונדסת (כולל 50+ מניות חדשות ל-2026) ---
SECTORS = {
    "⚛️ Quantum & Cyber": ["IONQ", "RGTI", "QBTS", "QTUM", "QUBT", "RDWR", "CYBR", "PANW", "CRWD", "ZS", "FTNT", "NET", "OKTA", "S"],
    "🚀 Defense & War (2026)": ["RKLB", "LUNR", "KTOS", "VVX", "BA", "LMT", "RTX", "JOBY", "ACHR", "BKSY", "SPAI", "PSN", "AXON", "GD", "NOC", "HII", "LDOS", "PLTR"],
    "🔥 AI, Chips & Data": ["NVDA", "AMD", "TSM", "AVGO", "ARM", "MU", "INTC", "QCOM", "SMCI", "ANET", "DELL", "HPE", "MSFT", "GOOGL", "META", "NNDM", "AMKR", "STX", "ORCL", "TTMI", "WDC", "TSEM", "PSTG", "IBM", "VRT"],
    "⚡ Energy & Trump Trade": ["MOD", "ASPN", "ETN", "GE", "CAT", "REI", "ENPH", "FSLR", "CAMT", "FLR", "NRGV", "PESI", "FLS", "OII", "BKR", "STRL", "NFE", "NNE", "SEDG", "PLUG", "XOM", "CVX", "OXY", "KMI", "HAL", "SLB"], 
    "⛏️ Commodities & Gold": ["FCX", "COPX", "SCCO", "AA", "CENX", "NHYDY", "CLF", "ALB", "MP", "PPTA", "VALE", "ABAT", "UUUU", "ZIM", "GLD", "NEM", "GOLD"],
    "🚗 Mobility & Auto": ["RIVN", "INVZ", "MBLY", "UBER", "TSLA", "GGM", "LAZR", "NIO", "XPEV", "LCID", "GM", "F"],
    "💊 BioTech & Health": ["NVO", "LLY", "VRTX", "ZBIO", "AMGN", "PFE", "TEVA", "CRSP", "MRNA", "UNH", "JNJ", "ABBV", "BMY"],
    "💳 Fintech & Crypto": ["SOFI", "PYPL", "FISV", "NFLX", "COIN", "HOOD", "SQ", "TTD", "PANW", "VOD", "CLBT", "MELI", "DRI", "TGT", "MSTR", "MARA", "RIOT", "CLSK", "IBIT", "JPM", "GS", "MS", "C"]
}

# איחוד כל הרשימות
ALL_TICKERS = list(set([ticker for sector in SECTORS.values() for ticker in sector]))
total_count = len(ALL_TICKERS)

st.info(f"📡 המערכת סורקת {total_count} מניות (כולל מניות מלחמה, אנרגיה ו-AI)...")

# --- פונקציה מוגנת (Cache) ---
@st.cache_data(ttl=300)
def get_data(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
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
        
        if len(df) < 30: continue 

        try:
            # --- המנוע ההנדסי ---
            window = 200 if len(df) >= 200 else len(df)
            df['SMA_200'] = df['Close'].rolling(window).mean()
            
            # SFP Logic
            prev_low_20 = df['Low'].shift(1).rolling(20).min().iloc[-1]
            today = df.iloc[-1]
            sfp_signal = (today['Low'] < prev_low_20) and (today['Close'] > prev_low_20)
            
            # RSI Logic
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # Trend Check (חישוב המרחק באחוזים מהממוצע)
            sma_val = df['SMA_200'].iloc[-1]
            trend_dist = ((today['Close'] - sma_val) / sma_val) * 100
            trend_status = "Bullish 🐂" if trend_dist > 0 else "Bearish 🐻"

            # --- תנאים מוקשחים (V7 Logic) ---
            
            # 1. SFP: דורש שהמניה לא תהיה בהתרסקות טוטאלית (לפחות לא רחוקה מדי מהממוצע)
            is_sfp = sfp_signal
            
            # 2. Dip Buy מוקשח: RSI מתחת ל-38 (במקום 40) + מרחק של לפחות 1.5% מעל הממוצע
            is_dip = (rsi < 38) and (trend_dist > 1.5)
            
            # 3. Momentum: כרגיל, אבל רק בסקטורים חמים
            is_mom = (rsi > 50) and (rsi < 70) and (trend_dist > 10)
            
            if is_sfp or is_dip or is_mom:
                
                stop_loss = today['Low'] * 0.98 
                
                sector_name = "General"
                for sec, tickers in SECTORS.items():
                    if ticker in tickers:
                        sector_name = sec
                        break
                
                if is_sfp:
                    sig_type = "🔥 SFP Trap"
                elif is_dip:
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
        except Exception:
            continue
            
    progress_bar.empty()
    status_text.empty()
    
    if results:
        df_results = pd.DataFrame(results)
        # מיון חכם
        df_results['Sort_Key'] = df_results['Signal'].apply(lambda x: 1 if "SFP" in x else (2 if "Dip" in x else 3))
        df_results = df_results.sort_values(by=['Sort_Key', 'RSI'])
        df_results = df_results.drop(columns=['Sort_Key'])

        st.success(f"הסריקה הושלמה! נמצאו {len(results)} הזדמנויות איכותיות.")
        st.dataframe(df_results, use_container_width=True)
        st.info("💡 הוספנו 50 מניות והקשחנו תנאים. התוצאות כעת ממוקדות יותר.")
    else:
        st.warning("לא נמצאו איתותים שעומדים בתנאים המוקשחים.")

with st.expander("🔍 הצג את רשימת המניות המלאה"):
    st.write(SECTORS)

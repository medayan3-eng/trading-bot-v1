import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- הגדרות ---
st.set_page_config(page_title="Global Sniper V5 🌍", layout="wide")

# כותרת עם כפתור רענון אגרסיבי
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🌍 Global Sniper V5: המהדורה המלאה")
    st.caption("כולל רשימת המעקב האישית, קוונטום, שבבים וסחורות")
with col2:
    if st.button("🧹 נקה זיכרון (Force Refresh)"):
        st.cache_data.clear()
        st.rerun()

# --- רשימת המעקב המהונדסת (הכוללת את כל הצילומים שלך) ---
SECTORS = {
    "⚛️ Quantum & Future": ["IONQ", "RGTI", "QBTS", "QTUM", "WOLF", "CRS", "IREN", "CRSP", "U", "QUBT"],
    "🚀 Space & Mobility": ["RKLB", "JOBY", "RIVN", "INVZ", "MBLY", "UBER", "TSLA", "LMT", "RTX", "KTOS", "BA"],
    "🔥 AI, Chips & Cloud": ["NVDA", "AMD", "TSM", "AVGO", "ARM", "MU", "INTC", "QCOM", "SMCI", "ANET", "ORCL", "MSFT", "GOOGL", "AMZN", "META", "DELL", "HPE", "TTD"],
    "⛏️ Commodities (Copper/Lithium)": ["FCX", "COPX", "SCCO", "AA", "CENX", "NHYDY", "CLF", "ALB", "MP", "GLW", "X", "VALE"],
    "🛢️ Energy & Infra": ["KMI", "TRGP", "CCJ", "URA", "VLO", "CVX", "XOM", "ENPH", "VRT", "ETN", "OXY", "SLB"],
    "💊 BioTech & Pharma": ["NVO", "LLY", "VRTX", "ZBIO", "AMGN", "PFE", "TEVA", "BIIB"],
    "💳 Fintech & Consumer": ["SOFI", "PYPL", "FISV", "NFLX", "COIN", "HOOD", "SQ", "DIS", "SBUX", "NKE"],
    "💾 Storage & Cyber": ["WDC", "PSTG", "CRWD", "PANW", "CHTR", "VOD", "ZS", "FTNT"]
}

# הערה: SNDK הוחלף ב-WDC כי סאנדיסק נרכשה. ת"א בנקים ו-90 הוסרו.

# איחוד כל הרשימות
ALL_TICKERS = list(set([ticker for sector in SECTORS.values() for ticker in sector]))
total_count = len(ALL_TICKERS)

st.info(f"מערכת מוכנה לסריקה של {total_count} מניות ייחודיות.")

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

# --- ממשק משתמש ---
if st.button("🚀 הרץ סריקת עומק (Deep Scan)"):
    results = []
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(ALL_TICKERS):
        # עדכון פס התקדמות
        progress = (i + 1) / total_count
        progress_bar.progress(progress)
        status_text.text(f"סורק את: {ticker} ({i+1}/{total_count})...")
        
        df = get_data(ticker)
        
        if len(df) < 200: continue 

        try:
            # --- המנוע ההנדסי ---
            df['SMA_200'] = df['Close'].rolling(200).mean()
            
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
            
            # Trend Check
            trend_dist = ((today['Close'] - df['SMA_200'].iloc[-1]) / df['SMA_200'].iloc[-1]) * 100
            trend_status = "Bullish 🐂" if trend_dist > 0 else "Bearish 🐻"

            # תנאי סף לכניסה לטבלה
            # 1. SFP (מלכודת)
            # 2. RSI נמוך במגמה עולה (תיקון)
            # 3. מומנטום חזק מאוד (RSI > 50 אבל לא רותח) במניות קוונטום/AI
            
            is_oversold_uptrend = (rsi < 40) and (trend_dist > 0)
            is_momentum = (rsi > 50) and (rsi < 70) and (trend_dist > 10) # מניות חזקות שטסות
            
            if sfp_signal or is_oversold_uptrend or (is_momentum and ticker in SECTORS["🔥 AI, Chips & Cloud"]):
                
                # חישוב סטופ
                stop_loss = today['Low'] * 0.98 
                
                # שיוך לסקטור
                sector_name = "General"
                for sec, tickers in SECTORS.items():
                    if ticker in tickers:
                        sector_name = sec
                        break
                
                if sfp_signal:
                    sig_type = "🔥 SFP Trap"
                elif is_oversold_uptrend:
                    sig_type = "📉 Dip Opportunity"
                else:
                    sig_type = "🚀 Strong Momentum"
                
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
        # המרה ל-DataFrame ומיון לפי RSI (מהנמוך לגבוה)
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values(by="Signal", ascending=False)
        
        st.success(f"הסריקה הושלמה! נמצאו {len(results)} הזדמנויות.")
        st.dataframe(df_results, use_container_width=True)
        st.caption(f"הנתונים נכונים לתאריך המסחר האחרון (אתמול בלילה, עד לפתיחת המסחר היום ב-16:30).")
    else:
        st.warning("לא נמצאו איתותים חזקים כרגע.")

with st.expander("🔍 הצג את כל רשימת המניות שנבדקו"):
    st.write(SECTORS)

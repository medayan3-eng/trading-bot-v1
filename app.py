import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- הגדרות ---
st.set_page_config(page_title="Global Sniper 🌎", layout="wide")
st.title("🌎 Global Sniper: מערכת סריקה גלובלית (100 הנבחרות)")
st.caption("ניתוח הנדסי: גרעין, AI, ביטחון, קריפטו, סחורות וטראמפ-טרייד")

# --- רשימת ה-100 המהונדסת ---
# חילקתי לקטגוריות כדי שיהיה סדר בעיניים, אבל הקוד מאחד אותן
SECTORS = {
    "🔥 AI & Chips (The Kings)": ["NVDA", "AMD", "TSM", "AVGO", "ARM", "MU", "INTC", "QCOM", "SMCI", "DELL"],
    "❄️ Cooling & Data Center Infra": ["VRT", "ETN", "ANET", "JBL", "CLS", "GLW", "HPE"],
    "☢️ Nuclear & Uranium (AI Power)": ["CCJ", "URA", "UEC", "BWXT", "LEU", "OKLO", "SMR", "CEG", "VST"],
    "🛡️ Defense & War (Geopolitics)": ["LMT", "RTX", "GD", "NOC", "KTOS", "PLTR", "BA", "AXON", "ESLT"],
    "₿ Crypto & Fintech (Trump Trade)": ["COIN", "MSTR", "MARA", "RIOT", "HOOD", "PYPL", "SQ", "SOFI", "V", "MA"],
    "⛏️ Commodities: Copper, Gold, Lithium": ["FCX", "SCCO", "NEM", "GOLD", "PAAS", "ALB", "MP", "CLF", "X", "VALE"],
    "🛢️ Energy & Oil (Venezuela/Iran)": ["XOM", "CVX", "OXY", "VLO", "HAL", "SLB", "EOG", "PBR"],
    "💊 BioTech & Pharma": ["LLY", "NVO", "PFE", "MRK", "AMGN", "BIIB", "CRSP"],
    "🛍️ Consumer & Turnaround Giants": ["AMZN", "GOOGL", "META", "MSFT", "AAPL", "TSLA", "NFLX", "DIS", "SBUX", "NKE", "BABA", "PDD"],
    "💻 Cyber Security": ["PANW", "CRWD", "FTNT", "ZS", "CYBR"]
}

# איחוד כל הרשימות לרשימה אחת שטוחה
ALL_TICKERS = [ticker for sector in SECTORS.values() for ticker in sector]

# --- פונקציה מוגנת (Cache) למניעת חסימות ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    try:
        # מוריד שנה אחורה כדי שיהיה מספיק לממוצע 200
        df = yf.download(ticker, period="1y", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        return df
    except:
        return pd.DataFrame()

# --- ממשק משתמש ---
if st.button("🚀 הרץ סריקת עומק (100 מניות)"):
    results = []
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    total_stocks = len(ALL_TICKERS)
    
    for i, ticker in enumerate(ALL_TICKERS):
        # עדכון פס התקדמות
        progress = (i + 1) / total_stocks
        progress_bar.progress(progress)
        status_text.text(f"סורק את: {ticker} ({i+1}/{total_stocks})...")
        
        df = get_data(ticker)
        
        if len(df) < 200: continue # צריך מספיק דאטה

        try:
            # --- המנוע ההנדסי (SFP + Trend) ---
            
            # 1. חישוב אינדיקטורים
            df['SMA_200'] = df['Close'].rolling(200).mean()
            
            # 2. לוגיקת SFP (מלכודת נזילות)
            # מחפשים נר שירד מתחת לנמוך של 20 יום - וסגר מעליו
            prev_low_20 = df['Low'].shift(1).rolling(20).min().iloc[-1]
            today = df.iloc[-1]
            prev = df.iloc[-2]
            
            # התנאי: הנמוך של אתמול שבר שפל, אבל הסגירה הייתה חזקה
            # או: הנמוך של היום שבר שפל, והמחיר עכשיו מעליו (בזמן אמת)
            sfp_signal = (today['Low'] < prev_low_20) and (today['Close'] > prev_low_20)
            
            # 3. RSI (לוודא שלא רותח)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # 4. מרחק מ-SMA200 (מגמה)
            trend_dist = ((today['Close'] - df['SMA_200'].iloc[-1]) / df['SMA_200'].iloc[-1]) * 100
            trend_status = "Bullish 🐂" if trend_dist > 0 else "Bearish 🐻"

            # --- סינון תוצאות ---
            # מציג הזדמנויות SFP, או מניות שנמצאות בתיקון חזק (RSI נמוך) במגמה עולה
            is_oversold_uptrend = (rsi < 40) and (trend_dist > 0)
            
            if sfp_signal or is_oversold_uptrend:
                stop_loss = today['Low'] * 0.98 # סטופ 2% מתחת לנמוך
                
                # זיהוי הסקטור
                sector_name = "General"
                for sec, tickers in SECTORS.items():
                    if ticker in tickers:
                        sector_name = sec
                        break
                
                signal_type = "🔥 SFP Trap" if sfp_signal else "📉 Dip Buy"
                
                results.append({
                    "Ticker": ticker,
                    "Sector": sector_name,
                    "Signal": signal_type,
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
        st.success(f"הסריקה הושלמה! נמצאו {len(results)} הזדמנויות פוטנציאליות.")
        # הצגת התוצאות בטבלה אינטראקטיבית
        st.dataframe(pd.DataFrame(results))
        st.caption("הערה: SFP Trap = מלכודת נזילות (חזק יותר). Dip Buy = קנייה בירידה במגמה עולה.")
    else:
        st.warning("השוק קשוח היום. מתוך 100 מניות, אף אחת לא נתנה איתות מושלם. זה הזמן לשבת על הגדר.")

# --- הצגת רשימת המעקב למטה ---
with st.expander("ראה את כל רשימת ה-100 (לחץ לפתיחה)"):
    st.write(SECTORS)

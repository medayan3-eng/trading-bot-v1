import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- הגדרות ---
st.set_page_config(page_title="Global Sniper V6 🌍", layout="wide")

# כותרת עם כפתור רענון
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🌍 Global Sniper V6: המהדורה המלאה")
    st.caption("מערכת סריקה: קוונטום, חלל, שבבים, ביוטק, סחורות וקריפטו (כולל המניות החדשות)")
with col2:
    if st.button("🧹 נקה זיכרון (Force Refresh)"):
        st.cache_data.clear()
        st.rerun()

# --- מדריך הצייד (הטבלה המקורית) ---
with st.expander("📘 איך לקרוא את האיתותים? (מדריך מקוצר)", expanded=False):
    st.markdown("""
    ### 🎯 מטריצת קבלת החלטות
    
    | סוג האיתות | המצב בשטח | לוגיקה |
    | :--- | :--- | :--- |
    | 🔥 **SFP Trap** | **מלכודת נזילות** | ניעור של סוחרים ("סטופים") במגמה עולה. האיתות הכי חזק להיפוך. |
    | 📉 **Dip Buy** | **קנייה בירידה** | מניה במגמה עולה שחטפה מכה זמנית (RSI < 40). הזדמנות ערך. |
    | 🚀 **Momentum** | **הצטרפות לגל** | מניה שטסה למעלה (RSI 50-70) ובורחת מהממוצעים. לרוץ עם המגמה. |
    """)

# --- רשימת המעקב המעודכנת (V6 + בקשות חדשות) ---
SECTORS = {
    "⚛️ Quantum & Cyber": ["IONQ", "RGTI", "QBTS", "QTUM", "QUBT", "RDWR", "WOLF", "CRWD", "PANW", "ZS", "FTNT"],
    "🚀 Space & Defense": ["RKLB", "LUNR", "KTOS", "VVX", "BA", "LMT", "RTX", "JOBY", "ACHR", "INVZ"],
    "🔥 AI, Chips & Cloud": ["NVDA", "AMD", "TSM", "AVGO", "ARM", "MU", "INTC", "QCOM", "SMCI", "ANET", "ORCL", "MSFT", "GOOGL", "AMZN", "META", "DELL", "HPE", "TTD"],
    "⚙️ Thermal, Energy & Ind.": ["VRT", "MOD", "ASPN", "ETN", "GE", "CAT", "REI", "ENPH", "FSLR", "CAMT", "CEG", "KMI", "TRGP", "CCJ", "URA"], 
    "⛏️ Commodities (Materials)": ["FCX", "COPX", "SCCO", "AA", "CENX", "NHYDY", "CLF", "ALB", "MP", "PPTA", "VALE", "GLW", "X"],
    "🚗 Mobility & Auto": ["RIVN", "MBLY", "UBER", "TSLA", "GGM", "LAZR"],
    "💊 BioTech & Pharma": ["NVO", "LLY", "VRTX", "ZBIO", "AMGN", "PFE", "TEVA", "CRSP", "BIIB"],
    "💳 Fintech & Services": ["SOFI", "PYPL", "FISV", "NFLX", "COIN", "HOOD", "SQ", "DIS", "SBUX", "NKE", "VOD"]
}

# איחוד כל הרשימות
ALL_TICKERS = list(set([ticker for sector in SECTORS.values() for ticker in sector]))
total_count = len(ALL_TICKERS)

st.info(f"המערכת סורקת {total_count} נכסים בזמן אמת...")

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

# --- מנוע הסריקה (לוגיקה V6 מקורית) ---
if st.button("🚀 הרץ סריקת עומק (Deep Scan)"):
    results = []
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(ALL_TICKERS):
        progress = (i + 1) / total_count
        progress_bar.progress(progress)
        status_text.text(f"סורק את: {ticker} ({i+1}/{total_count})...")
        
        df = get_data(ticker)
        
        if len(df) < 200: continue 

        try:
            # 1. חישובים טכניים
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

            # 2. לוגיקת האיתותים (V6 Original - בלי החמרות יתר)
            
            # Dip Buy: ירידה (RSI < 40) במגמה עולה
            is_oversold_uptrend = (rsi < 40) and (trend_dist > 0)
            
            # Momentum: מניה חזקה (RSI 50-70) שרצה מעל הממוצע (מעל 10% מרחק)
            is_momentum = (rsi > 50) and (rsi < 70) and (trend_dist > 10) 
            
            # אם יש איתות כלשהו -> הוסף לטבלה
            if sfp_signal or is_oversold_uptrend or is_momentum:
                
                stop_loss = today['Low'] * 0.98 # סטופ של 2% מתחת לנמוך היומי
                
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
                    "Trend": trend_status,
                    "Stop Loss": f"${stop_loss:.2f}"
                })
        except Exception as e:
            continue
            
    progress_bar.empty()
    status_text.empty()
    
    if results:
        # מיון התוצאות
        df_results = pd.DataFrame(results)
        
        # טריק למיון: נותנים ציון מספרי לסוג האיתות
        # SFP מקבל עדיפות עליונה, אחריו Dip Buy, ובסוף Momentum
        priority = {"🔥 SFP Trap": 1, "📉 Dip Buy": 2, "🚀 Momentum": 3}
        df_results['Sort_Key'] = df_results['Signal'].map(priority)
        
        # מיון משני לפי RSI (נמוך לגבוה בתוך הקטגוריה)
        df_results = df_results.sort_values(by=['Sort_Key', 'RSI'])
        df_results = df_results.drop(columns=['Sort_Key'])

        st.success(f"הסריקה הושלמה! נמצאו {len(results)} הזדמנויות.")
        st.dataframe(df_results, use_container_width=True)
        st.caption("הנתונים נכונים לסגירת המסחר האחרונה בארה\"ב (או נתונים חיים אם השוק פתוח).")
    else:
        st.warning("לא נמצאו איתותים חזקים כרגע.")

with st.expander("🔍 הצג את כל רשימת המניות שנבדקו"):
    st.write(SECTORS)

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
    st.caption("מערכת סריקה: קוונטום, חלל, שבבים, ביוטק, סחורות וקריפטו")
with col2:
    if st.button("🧹 נקה זיכרון (Force Refresh)"):
        st.cache_data.clear()
        st.rerun()

# --- מדריך הצייד (התוספת החדשה) ---
with st.expander("📘 איך לבחור מניה לבדיקה ב-Colab? (טבלת הסבר)", expanded=False):
    st.markdown("""
    ### 🎯 מטריצת קבלת החלטות
    לפני שאתה רץ ל-Colab, בדוק את השילוב הבא בטבלה למטה:

    | דירוג איכות | סוג האיתות (Signal) | מגמה (Trend) | RSI | מסקנה הנדסית |
    | :--- | :--- | :--- | :--- | :--- |
    | 🥇 **יהלום (Top Tier)** | 🔥 **SFP Trap** | **Bullish 🐂** | **40-50** | **חובה לבדוק ב-Colab!** זהו מצב אידיאלי: מלכודת נזילות במגמה עולה. |
    | 🥈 **חזק (Strong)** | 📉 **Dip Buy** | **Bullish 🐂** | **30-40** | **בדיקה מומלצת.** המניה במגמה עולה אבל בתיקון חד (מכירת יתר). |
    | 🥉 **ספקולטיבי** | 🔥 **SFP Trap** | Bearish 🐻 | 30-60 | **סיכון גבוה.** ניסיון לתפוס "תחתית" במגמה יורדת. לבדוק רק אם ה-AI נותן ציון גבוה מאוד. |
    | ⚠️ **מסוכן** | 📉 Dip Buy | Bearish 🐻 | < 30 | **סכין נופלת.** המניה מתרסקת. ה-AI כנראה יגיד WAIT. |
    
    **מקרא מקוצר:**
    * **SFP Trap:** ניעור של סוחרים חלשים (סימן שכסף חכם נכנס). חזק יותר מסתם ירידה.
    * **RSI:** מתחת ל-30 זה "זול מאוד" (אולי מדי). סביב 40-50 זה "זול בריא".
    """)

# --- רשימת המעקב המהונדסת ---
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

st.info(f"מערכת סורקת {total_count} מניות בזמן אמת...")

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
            is_oversold_uptrend = (rsi < 40) and (trend_dist > 0)
            is_momentum = (rsi > 50) and (rsi < 70) and (trend_dist > 10) 
            
            if sfp_signal or is_oversold_uptrend or (is_momentum and ticker in SECTORS["🔥 AI, Chips & Cloud"]):
                
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
                    "Trend": trend_status,
                    "Stop Loss": f"${stop_loss:.2f}"
                })
        except Exception as e:
            continue
            
    progress_bar.empty()
    status_text.empty()
    
    if results:
        # מיון חכם: SFP ראשון, אח"כ לפי RSI נמוך
        df_results = pd.DataFrame(results)
        
        # טריק למיון: נותנים ציון מספרי לסוג האיתות
        df_results['Sort_Key'] = df_results['Signal'].apply(lambda x: 1 if "SFP" in x else (2 if "Dip" in x else 3))
        df_results = df_results.sort_values(by=['Sort_Key', 'RSI'])
        df_results = df_results.drop(columns=['Sort_Key'])

        st.success(f"הסריקה הושלמה! נמצאו {len(results)} הזדמנויות.")
        st.dataframe(df_results, use_container_width=True)
        st.info("💡 טיפ: השתמש בטבלת ההסבר למעלה כדי לבחור את המועמדת הטובה ביותר לבדיקה ב-Colab.")
    else:
        st.warning("לא נמצאו איתותים חזקים כרגע.")

with st.expander("🔍 הצג את כל רשימת המניות שנבדקו"):
    st.write(SECTORS)

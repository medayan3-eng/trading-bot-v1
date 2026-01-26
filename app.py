import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# --- הגדרות ---
st.set_page_config(page_title="Global Sniper V6.4 🌍", layout="wide")

# כותרת
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🌍 Global Sniper V6.4: Bulk Edition")
    st.caption("מערכת סריקה מהירה: פרוטוקול משיכה מרוכז (למניעת חסימות)")
with col2:
    if st.button("🔄 רענן נתונים (Force Refresh)"):
        st.cache_data.clear()
        st.rerun()

st.sidebar.write(f"🕒 זמן אמת: {datetime.now().strftime('%H:%M:%S')}")

# --- רשימת המעקב המלאה ---
SECTORS = {
    "⚛️ Quantum & Cyber": ["IONQ", "RGTI", "QBTS", "QTUM", "QUBT", "RDWR", "CYBR", "SENT", "PANW", "CRWD", "ZS", "FTNT", "CHTR"],
    "🚀 Space & Defense": ["RKLB", "LUNR", "KTOS", "VVX", "BA", "LMT", "RTX", "JOBY", "ACHR", "BKSY", "SPAI", "PSN", "SPIR", "AXON"],
    "🔥 AI, Chips & Hardware": ["NVDA", "AMD", "TSM", "AVGO", "ARM", "MU", "INTC", "QCOM", "SMCI", "ANET", "DELL", "HPE", "MSFT", "GOOGL", "META", "NNDM", "AMKR", "STX", "ORCL", "TTMI", "WDC", "PSTG", "TSEM"],
    "⚡ Energy, Solar & Ind.": ["VRT", "MOD", "ASPN", "ETN", "GE", "CAT", "REI", "ENPH", "FSLR", "CAMT", "FLR", "NRGV", "PESI", "FLS", "OII", "BKR", "STRL", "NFE", "NNE", "SEDG", "RUN", "PLUG", "JKS", "CSIQ"], 
    "⛏️ Commodities & Shipping": ["FCX", "COPX", "SCCO", "AA", "CENX", "NHYDY", "CLF", "ALB", "MP", "PPTA", "VALE", "ABAT", "UUUU", "ZIM", "GOGL", "SBLK"],
    "🚗 EV & Mobility": ["RIVN", "INVZ", "MBLY", "UBER", "TSLA", "GGM", "LAZR", "LCID", "NIO", "XPEV", "LI", "CVNA"],
    "💊 BioTech & Pharma": ["NVO", "LLY", "VRTX", "ZBIO", "AMGN", "PFE", "TEVA", "CRSP", "MRNA", "BNTX", "BMY"],
    "🪙 Crypto & Fintech": ["MSTR", "MARA", "RIOT", "CLSK", "COIN", "HOOD", "SQ", "PYPL", "SOFI", "AFRM", "UPST"],
    "🛍️ Growth & Consumer": ["NFLX", "TTD", "PLTR", "U", "SNOW", "DDOG", "NET", "DKNG", "RBLX", "SHOP", "BABA", "PDD", "JD", "MELI", "DRI", "TGT", "CELH", "ELF"]
}

# יצירת רשימה שטוחה
ALL_TICKERS = list(set([ticker for sector in SECTORS.values() for ticker in sector]))
ALL_TICKERS_STR = " ".join(ALL_TICKERS) # המרה למחרוזת אחת לבקשה מרוכזת

# --- מנוע משיכה מרוכז (Bulk Download) ---
@st.cache_data(ttl=300)
def get_batch_data():
    try:
        # כאן הקסם: בקשה אחת לכל המניות ביחד
        # group_by='ticker' מבטיח שנקבל מבנה נוח לעבודה
        data = yf.download(ALL_TICKERS_STR, period="1y", group_by='ticker', progress=False, auto_adjust=True)
        return data
    except Exception as e:
        st.error(f"שגיאת תקשורת: {e}")
        return pd.DataFrame()

# --- ממשק משתמש ---
st.info(f"📡 מוריד נתונים עבור {len(ALL_TICKERS)} מניות בבקשה אחת...")

if st.button("🚀 הרץ סריקת עומק (Deep Scan)"):
    
    # 1. משיכת כל הנתונים
    bulk_data = get_batch_data()
    
    if bulk_data.empty:
        st.error("הנתונים לא התקבלו. נסה שוב בעוד דקה.")
        st.stop()
        
    results = []
    
    # 2. מעבר על המניות (עכשיו זה מקומי ומהיר)
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(ALL_TICKERS):
        progress_bar.progress((i + 1) / len(ALL_TICKERS))
        
        try:
            # חילוץ הדאטה של המניה הספציפית מתוך המאגר הגדול
            df = bulk_data[ticker].copy()
            
            # ניקוי נתונים ריקים (קורה לפעמים במשיכה המונית)
            df = df.dropna()
            
            if len(df) < 30: continue

            # --- חישובים הנדסיים ---
            sma_window = 200 if len(df) >= 200 else len(df)
            df['SMA_200'] = df['Close'].rolling(sma_window).mean()
            
            # נתונים אחרונים
            today = df.iloc[-1]
            last_date = today.name.strftime('%Y-%m-%d')
            
            # SFP Logic
            prev_low_20 = df['Low'].shift(1).rolling(window=min(20, len(df))).min().iloc[-1]
            sfp_signal = (today['Low'] < prev_low_20) and (today['Close'] > prev_low_20)
            
            # RSI Logic
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # Trend Logic (חישוב מרחק באחוזים מהממוצע)
            trend_dist = ((today['Close'] - df['SMA_200'].iloc[-1]) / df['SMA_200'].iloc[-1]) * 100
            
            # קביעת סטטוס מגמה
            if trend_dist > 0:
                trend_status = "Bullish 🐂"
            elif trend_dist > -5:
                trend_status = "Correction 📉" # מגמה עולה בתיקון קל
            else:
                trend_status = "Bearish 🐻"

            # --- הפילטרים (הגמשנו מעט) ---
            
            # Dip Buy: RSI נמוך, והמחיר לא קרס טוטאלית (עד 5% מתחת לממוצע זה סביר לתיקון)
            is_dip_buy = (rsi < 40) and (trend_dist > -5)
            
            # Momentum: RSI חזק ומחיר טס
            is_momentum = (rsi > 50) and (rsi < 70) and (trend_dist > 5)
            
            if sfp_signal or is_dip_buy or is_momentum:
                
                stop_loss = today['Low'] * 0.98 
                
                # מציאת הסקטור
                sector_name = "General"
                for sec, tickers in SECTORS.items():
                    if ticker in tickers:
                        sector_name = sec
                        break
                
                # סוג האיתות
                if sfp_signal:
                    sig_type = "🔥 SFP Trap"
                elif is_dip_buy:
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
                
        except Exception:
            continue

    progress_bar.empty()
    
    if results:
        df_results = pd.DataFrame(results)
        
        # מיון: SFP למעלה, ואז לפי RSI נמוך
        df_results['Sort_Key'] = df_results['Signal'].apply(lambda x: 1 if "SFP" in x else (2 if "Dip" in x else 3))
        df_results = df_results.sort_values(by=['Sort_Key', 'RSI'])
        df_results = df_results.drop(columns=['Sort_Key'])

        st.success(f"נמצאו {len(results)} הזדמנויות מסחר!")
        st.dataframe(df_results, use_container_width=True, hide_index=True)
    else:
        st.warning("לא נמצאו איתותים. השוק כנראה 'פרווה' היום.")

# --- מדריך ---
with st.expander("📘 מקרא איתותים מעודכן"):
    st.markdown("""
    * **🔥 SFP Trap:** מלכודת נזילות (היפוך חזק).
    * **📉 Dip Buy:** מניה זולה (RSI נמוך) שעדיין קרובה למגמה הראשית.
    * **🚀 Momentum:** מניה במגמה חזקה שרק ממשיכה.
    * **Correction:** המניה ירדה קצת מתחת לממוצע 200, אבל זה עשוי להיות אזור איסוף.
    """)

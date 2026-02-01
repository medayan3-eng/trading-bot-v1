import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# --- הגדרות ---
st.set_page_config(page_title="Global Sniper V7 (Non-S&P)", layout="wide")

# כותרת עם כפתור רענון
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🌍 Global Sniper V7: Underdog Edition")
    st.caption("מערכת סריקה: מניות צמיחה, Small Caps, והזדמנויות מחוץ ל-S&P 500")
with col2:
    if st.button("🧹 נקה זיכרון (Force Refresh)"):
        st.cache_data.clear()
        st.rerun()

st.sidebar.write(f"🕒 סריקה אחרונה: {datetime.now().strftime('%H:%M:%S')}")

# --- מדריך הצייד ---
with st.expander("📘 מטריצת קבלת החלטות (תנאים מוקשחים)", expanded=False):
    st.markdown("""
    | דירוג | סוג האיתות | RSI | תנאי מגמה | מסקנה |
    | :--- | :--- | :--- | :--- | :--- |
    | 🥇 **יהלום** | 🔥 SFP Trap | 40-50 | **חובה** מעל הממוצע 200 | **חובה לבדוק ב-Colab!** |
    | 🥈 **חזק** | 📉 Dip Buy | **< 38** | **חובה** מעל 1.5% מממוצע 200 | **בדיקה מומלצת.** |
    | 🥉 **מומנטום** | 🚀 Momentum | 50-70 | **חובה** מעל 10% מממוצע 200 | **הצטרפות לגל.** |
    """)

# --- רשימת המעקב החדשה (ללא S&P 500) ---
# נבחרו מניות עם ווליום גבוה, תנודתיות בריאה ופוטנציאל צמיחה
SECTORS = {
    "⚛️ Emerging Tech & Quantum": [
        "IONQ", "RGTI", "QBTS", "QUBT", "D-WAVE", "RDWR", "LAZR", "INVZ", "MVIS", 
        "HIMX", "KOPN", "VUZI", "EMAN", "PLTR", "PATH", "AI", "SOUN", "BBAI"
    ],
    "🚀 Space & Speculative Defense": [
        "RKLB", "LUNR", "ASTS", "SPCE", "VORB", "RDBX", "SPIR", "BKSY", "PL", 
        "LLAP", "SIDU", "MNTS", "JOBY", "ACHR", "EVTL", "EH"
    ],
    "💊 BioTech (High Volatility)": [
        "CRSP", "NTLA", "BEAM", "EDIT", "PACB", "TXG", "DNA", "SDGR", "RXRX", 
        "NVTA", "BNGO", "SENS", "OCGN", "SESN", "CTXR", "ATOS", "JAGX", "VXRT"
    ],
    "⚡ Clean Energy & EV (Non-Major)": [
        "PLUG", "FCEL", "BE", "BLDP", "NKLA", "HYZN", "WKHS", "RIDE", "GOEV", 
        "MULN", "CENN", "SOL", "JKS", "DQ", "CSIQ", "RUN", "NOVA", "SPWR"
    ], 
    "⛏️ Rare Earths & Lithium (Miners)": [
        "MP", "LAC", "LTHM", "SGML", "PLL", "SLI", "ABAT", "TMC", "UEC", "UUUU", 
        "DNN", "NXE", "CCJ", "LODE", "HYMC", "AUY"
    ],
    "💳 Fintech, Crypto & Growth": [
        "SOFI", "UPST", "AFRM", "LC", "MQ", "HOOD", "COIN", "MARA", "RIOT", 
        "HUT", "BITF", "HIVE", "CLSK", "MSTR", "SI", "BKKT", "OPAD", "OPEN"
    ],
    "🎮 Gaming, Metaverse & Penny Favorites": [
        "U", "RBLX", "DKNG", "PENN", "FUBO", "SKLZ", "GNUS", "BB", "AMC", "GME", 
        "KOSS", "EXPR", "TLRY", "SNDL", "CGC", "ACB", "CRON"
    ]
}

# איחוד כל הרשימות
ALL_TICKERS = list(set([ticker for sector in SECTORS.values() for ticker in sector]))
total_count = len(ALL_TICKERS)

st.info(f"📡 המערכת סורקת {total_count} מניות צמיחה ו-Small Caps (מחוץ ל-S&P 500)...")

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
        
        # סינון: צריך לפחות חודש של דאטה ומחיר מינימלי של 1 דולר (כדי להימנע מזבל מוחלט)
        if len(df) < 30: continue 
        if df['Close'].iloc[-1] < 0.50: continue # סינון מניות מתחת לחצי דולר

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
            
            is_sfp = sfp_signal
            is_dip = (rsi < 38) and (trend_dist > 1.5)
            # במומנטום של מניות קטנות, אפשר להיות קצת יותר גמישים עם ה-RSI העליון
            is_mom = (rsi > 50) and (rsi < 75) and (trend_dist > 10)
            
            if is_sfp or is_dip or is_mom:
                
                stop_loss = today['Low'] * 0.95 # סטופ רחב יותר (5%) למניות תנודתיות
                
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

        st.success(f"הסריקה הושלמה! נמצאו {len(results)} הזדמנויות (מניות Small/Mid Cap).")
        st.dataframe(df_results, use_container_width=True)
        st.info("💡 המניות ברשימה זו הן תנודתיות יותר. הקפד על ניהול סיכונים.")
    else:
        st.warning("לא נמצאו איתותים שעומדים בתנאים המוקשחים.")

with st.expander("🔍 הצג את רשימת המניות המלאה"):
    st.write(SECTORS)

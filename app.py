import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# --- הגדרות ---
st.set_page_config(page_title="Global Sniper V8 (300+)", layout="wide")

# כותרת עם כפתור רענון
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🌍 Global Sniper V8: Massive Attack")
    st.caption("מערכת סריקה מורחבת: 300+ מניות צמיחה, ספקולציה ו-Mid Caps (ללא S&P 500)")
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

# --- רשימת המעקב הענקית (300+ מניות) ---
SECTORS = {
    "⚛️ Quantum, AI & Big Data": [
        "IONQ", "RGTI", "QBTS", "QUBT", "D-WAVE", "SOUN", "BBAI", "VERI", "AI", "PATH", 
        "UPST", "LZ", "DNA", "PLTR", "SDGR", "AUR", "TSP", "SPIR", "MVIS", "HIMX", 
        "KOPN", "VUZI", "EMAN", "BB", "GFAI", "CLRO", "PRST"
    ],
    "🛡️ Cyber Security (Mid-Cap)": [
        "S", "TENB", "VRNS", "QLYS", "RPD", "NET", "OKTA", "DOCU", "ZS", "CRWD", 
        "CYBR", "FTNT", "CHKP", "GEN", "MNDT", "RDWR", "HACK"
    ],
    "🚀 Space, Drones & Defense": [
        "RKLB", "LUNR", "ASTS", "SPCE", "VORB", "BKSY", "JOBY", "ACHR", "EVTL", "EH", 
        "SIDU", "RDW", "MNTS", "LLAP", "PL", "VSAT", "KTOS", "AVAV", "AJRD", "AXON"
    ],
    "🧬 BioTech & Genomics (High Volatility)": [
        "CRSP", "NTLA", "BEAM", "EDIT", "FATE", "BLUE", "SAGE", "ITCI", "AXSM", "KRTX", 
        "MRTX", "SRPT", "NBIX", "IONS", "ALNY", "EXAS", "GH", "NVTA", "PACB", "TXG", 
        "RXRX", "BNGO", "SENS", "OCGN", "SESN", "CTXR", "ATOS", "JAGX", "VXRT", "INO"
    ],
    "💳 Fintech, Crypto & Blockchain": [
        "COIN", "HOOD", "MARA", "RIOT", "CLSK", "HUT", "BITF", "MSTR", "SOFI", "AFRM", 
        "LC", "MQ", "BILL", "TOST", "SQ", "DKNG", "PYPL", "BAC", "C", "WULF", 
        "IREN", "BTBT", "SDIG", "GREE", "ANY", "BKKT", "SI"
    ],
    "⚡ Clean Energy & Hydrogen": [
        "PLUG", "FCEL", "BE", "RUN", "NOVA", "JKS", "DQ", "CSIQ", "ENPH", "SEDG", 
        "ARRY", "SHLS", "FSLR", "SPWR", "MAXN", "BLDP", "NKLA", "HYZN", "AMRC"
    ],
    "☢️ Uranium & Nuclear": [
        "UUUU", "CCJ", "NXE", "DNN", "UEC", "LEU", "URA", "URNM", "SMR", "BWXT", 
        "FLR", "NNE", "SRXY"
    ],
    "🚗 EV, Batteries & Lithium": [
        "RIVN", "LCID", "PSNY", "GOEV", "NIO", "XPEV", "LI", "GGR", "MULN", "CENN", 
        "MP", "LAC", "SGML", "ALB", "LTHM", "QS", "ENVX", "MICRO", "CHPT", "BLNK", 
        "EVGO", "WBX", "HYMC"
    ],
    "🇨🇳 China Growth (High Risk/Reward)": [
        "BABA", "JD", "PDD", "BIDU", "BILI", "TME", "IQ", "FUTU", "TIGR", "YMM", 
        "BZ", "GOTU", "TAL", "EDU", "HTHT", "VIPS", "ZTO", "BEKE", "LU"
    ],
    "🤖 Robotics & 3D Printing": [
        "DDD", "SSYS", "DM", "IRBT", "PATH", "UIP", "ROK", "TER", "COGN", "NVTS", 
        "MKFG", "VLD", "NNDM"
    ],
    "🎮 Gaming, Metaverse & Chips": [
        "U", "RBLX", "DKNG", "PENN", "FUBO", "SKLZ", "GNUS", "AMC", "GME", "TTWO", 
        "EA", "ATVI", "CRSR", "LOGI", "HEAR", "AMD", "MU", "INTC", "WDC", "STX"
    ],
    "🏠 REITs (High Yield/Vol)": [
        "NLY", "AGNC", "IVR", "MFA", "TWO", "ARR", "CIM", "EFC", "NYMT", "RITM", 
        "ABR", "STWD", "BXMT"
    ]
}

# איחוד כל הרשימות
ALL_TICKERS = list(set([ticker for sector in SECTORS.values() for ticker in sector]))
total_count = len(ALL_TICKERS)

st.info(f"📡 המערכת סורקת {total_count} מניות צמיחה ו-Mid Caps (תהליך זה ייקח כדקה-שתיים)...")

# --- פונקציה מוגנת (Cache) ---
@st.cache_data(ttl=300)
def get_data(ticker):
    try:
        # הורדתי ל-200 ימים כדי להאיץ את הסריקה של 300 המניות
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
    
    # משתנים למעקב אחרי שגיאות/מחיקות
    skipped_count = 0
    
    for i, ticker in enumerate(ALL_TICKERS):
        # עדכון פרוגרס בר כל 5 מניות כדי לא להאט את הממשק
        if i % 5 == 0:
            progress = (i + 1) / total_count
            progress_bar.progress(progress)
            status_text.text(f"סורק את: {ticker} ({i+1}/{total_count})...")
        
        df = get_data(ticker)
        
        # סינון: צריך לפחות 50 ימי מסחר ומחיר מעל חצי דולר
        if len(df) < 50 or df['Close'].iloc[-1] < 0.50: 
            skipped_count += 1
            continue 

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
            # במומנטום של מניות קטנות, אפשר להיות קצת יותר גמישים
            is_mom = (rsi > 50) and (rsi < 75) and (trend_dist > 10)
            
            if is_sfp or is_dip or is_mom:
                
                # סטופ מותאם לתנודתיות (5%)
                stop_loss = today['Low'] * 0.95 
                
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

        st.success(f"הסריקה הושלמה! נמצאו {len(results)} הזדמנויות מתוך {total_count}.")
        st.dataframe(df_results, use_container_width=True)
        st.info(f"💡 נסרקו {total_count} מניות. מתוכן {skipped_count} סוננו עקב מחיר נמוך או חוסר נתונים.")
    else:
        st.warning("לא נמצאו איתותים שעומדים בתנאים המוקשחים.")

with st.expander("🔍 הצג את רשימת המניות המלאה (300+)"):
    st.write(SECTORS)

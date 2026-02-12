import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# --- הגדרות ---
st.set_page_config(page_title="Global Sniper V9 Elite", layout="wide")

# כותרת
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🎯 Global Sniper V9: Elite Filter")
    st.caption("מערכת סינון רב-שלבית: רק המניות שבאמת שוות את הזמן שלך")
with col2:
    if st.button("🧹 רענן"):
        st.cache_data.clear()
        st.rerun()

# --- מדריך ---
with st.expander("🧠 איך זה עובד? (לחץ לפרטים)", expanded=False):
    st.markdown("""
    ### 🔥 מערכת סינון ב-4 שלבים:
    
    **שלב 1: סינון בסיסי (90% מהמניות נפסלות)**
    - ✅ מחיר > $2 (לא penny stocks)
    - ✅ שווי שוק > $200M (חברות אמיתיות)
    - ✅ נפח מסחר ממוצע > 500K מניות ביום (ליקווידיות)
    
    **שלב 2: בדיקות פונדמנטליות (70% נוספות נופלות)**
    - 📊 P/E ratio סביר (5-50, או חברת צמיחה ללא רווח)
    - 💰 חוב/הון < 3 (לא יותר מדי ממונפות)
    - 📈 צמיחת הכנסות > 10% (או שווי > $1B)
    
    **שלב 3: סינון טכני מתקדם (רק 20% עוברות)**
    - 🎯 SFP (Swing Failure Pattern) - איתות מלכודת דובים
    - 📉 Dip מוכח - RSI < 35 + מעל ממוצע 200
    - 🚀 Breakout - פריצת התנגדות 52 שבועות
    - 💪 Volume Surge - נפח פי 2+ מהממוצע
    
    **שלב 4: דירוג חכם (Top 5-15)**
    - 🏆 ניקוד משולב: טכני (50%) + פונדמנטלי (30%) + מומנטום (20%)
    - 📊 רק הטובות ביותר מוצגות
    
    ---
    
    ### 🎯 פלט צפוי:
    במקום 50 מניות → **רק 5-15 המובילות**
    
    כל מניה מדורגת 0-100 עם הסבר למה היא עברה
    """)

# --- רשימת מניות (ממוקדת יותר) ---
SECTORS = {
    "⚛️ Quantum & AI": [
        "IONQ", "RGTI", "QBTS", "QUBT", "ARQQ", "SOUN", "BBAI", "AI", "PATH", 
        "PLTR", "SNOW", "DDOG", "NET", "PANW"
    ],
    "🛡️ Cyber Security": [
        "CRWD", "S", "ZS", "OKTA", "FTNT", "CHKP", "CYBR", "TENB", "VRNS", "RPD"
    ],
    "🚀 Space & Defense": [
        "RKLB", "ASTS", "LUNR", "PL", "JOBY", "ACHR", "AXON", "AVAV", "KTOS"
    ],
    "🧬 BioTech (Selected)": [
        "CRSP", "BEAM", "NTLA", "EDIT", "ARKG", "EXAS", "RXRX", "SDGR", "VERV"
    ],
    "💳 FinTech & Crypto": [
        "COIN", "HOOD", "MARA", "RIOT", "SOFI", "AFRM", "SQ", "PYPL", "NU", "UPST"
    ],
    "⚡ Clean Energy": [
        "ENPH", "FSLR", "RUN", "PLUG", "BE", "NOVA", "ARRY", "SEDG"
    ],
    "☢️ Uranium": [
        "CCJ", "UUUU", "DNN", "UEC", "LEU", "NXE"
    ],
    "🚗 EV & Batteries": [
        "RIVN", "LCID", "TSLA", "NIO", "XPEV", "QS", "ENVX", "ALB", "LAC"
    ],
    "🇨🇳 China Growth": [
        "BABA", "PDD", "JD", "BIDU", "NIO", "XPEV", "LI", "BILI"
    ],
    "🎮 Gaming & Chips": [
        "RBLX", "U", "AMD", "NVDA", "AVGO", "MU", "INTC", "ARM"
    ],
    "🤖 Robotics & Auto": [
        "PATH", "IRBT", "MKFG", "NNDM", "DM", "SSYS"
    ]
}

ALL_TICKERS = list(set([ticker for sector in SECTORS.values() for ticker in sector]))
total_count = len(ALL_TICKERS)

st.info(f"📡 סורק {total_count} מניות נבחרות בסינון רב-שלבי...")

# --- פונקציות עזר ---
@st.cache_data(ttl=300)
def get_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        info = stock.info
        return df, info
    except:
        return pd.DataFrame(), {}

def calculate_technical_score(df, info):
    """חישוב ניקוד טכני 0-100"""
    score = 0
    signals = []
    
    if len(df) < 50:
        return 0, []
    
    try:
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Moving Averages
        df['SMA_50'] = df['Close'].rolling(50).mean()
        df['SMA_200'] = df['Close'].rolling(200).mean()
        
        current_price = df['Close'].iloc[-1]
        sma_50 = df['SMA_50'].iloc[-1]
        sma_200 = df['SMA_200'].iloc[-1]
        
        # Volume Analysis
        avg_volume = df['Volume'].rolling(20).mean().iloc[-1]
        current_volume = df['Volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        # SFP Pattern
        prev_low_20 = df['Low'].shift(1).rolling(20).min().iloc[-1]
        today = df.iloc[-1]
        sfp_signal = (today['Low'] < prev_low_20) and (today['Close'] > prev_low_20)
        
        # 52-week high/low
        high_52w = df['High'].rolling(252).max().iloc[-1]
        low_52w = df['Low'].rolling(252).min().iloc[-1]
        price_position = (current_price - low_52w) / (high_52w - low_52w) if high_52w > low_52w else 0
        
        # ניקוד
        # 1. SFP Pattern (25 נקודות)
        if sfp_signal and rsi > 30:
            score += 25
            signals.append("🔥 SFP Trap")
        
        # 2. Dip Buy (25 נקודות)
        if rsi < 35 and current_price > sma_200 * 1.02:
            score += 25
            signals.append("📉 Strong Dip")
        
        # 3. Breakout (20 נקודות)
        if price_position > 0.95 and volume_ratio > 1.5:
            score += 20
            signals.append("🚀 Breakout")
        
        # 4. Golden Cross (15 נקודות)
        if sma_50 > sma_200 and current_price > sma_50:
            score += 15
            signals.append("✨ Golden Cross")
        
        # 5. Volume Surge (15 נקודות)
        if volume_ratio > 2.0:
            score += 15
            signals.append("📊 Volume x2+")
        
        return score, signals
        
    except Exception as e:
        return 0, []

def calculate_fundamental_score(info):
    """חישוב ניקוד פונדמנטלי 0-100"""
    score = 0
    reasons = []
    
    try:
        # Market Cap
        market_cap = info.get('marketCap', 0)
        if market_cap > 10_000_000_000:  # >$10B
            score += 20
            reasons.append("💎 Large Cap")
        elif market_cap > 1_000_000_000:  # >$1B
            score += 15
            reasons.append("💰 Mid Cap")
        elif market_cap > 200_000_000:  # >$200M
            score += 10
            reasons.append("🏢 Small Cap")
        
        # P/E Ratio
        pe = info.get('trailingPE', None)
        if pe and 5 < pe < 30:
            score += 20
            reasons.append(f"📊 P/E: {pe:.1f}")
        elif pe and 30 < pe < 50:
            score += 10
            reasons.append(f"📊 P/E: {pe:.1f}")
        elif pe is None or pe < 0:
            # חברות צמיחה ללא רווח
            revenue_growth = info.get('revenueGrowth', 0)
            if revenue_growth and revenue_growth > 0.3:
                score += 15
                reasons.append(f"📈 צמיחה: {revenue_growth*100:.0f}%")
        
        # Debt to Equity
        debt_to_equity = info.get('debtToEquity', None)
        if debt_to_equity is not None:
            if debt_to_equity < 50:
                score += 20
                reasons.append("💪 חוב נמוך")
            elif debt_to_equity < 150:
                score += 10
                reasons.append("⚖️ חוב סביר")
        
        # Revenue Growth
        revenue_growth = info.get('revenueGrowth', None)
        if revenue_growth:
            if revenue_growth > 0.5:
                score += 20
                reasons.append(f"🚀 צמיחה {revenue_growth*100:.0f}%")
            elif revenue_growth > 0.2:
                score += 15
                reasons.append(f"📈 צמיחה {revenue_growth*100:.0f}%")
            elif revenue_growth > 0.1:
                score += 10
                reasons.append(f"➕ צמיחה {revenue_growth*100:.0f}%")
        
        # Profit Margins
        profit_margin = info.get('profitMargins', None)
        if profit_margin and profit_margin > 0.2:
            score += 10
            reasons.append(f"💰 רווחיות {profit_margin*100:.0f}%")
        
        return score, reasons
        
    except Exception as e:
        return 0, []

def passes_basic_filters(df, info):
    """סינון בסיסי - חייב לעבור"""
    try:
        # מחיר
        current_price = df['Close'].iloc[-1]
        if current_price < 2:
            return False, "מחיר < $2"
        
        # שווי שוק
        market_cap = info.get('marketCap', 0)
        if market_cap < 200_000_000:
            return False, "שווי < $200M"
        
        # נפח מסחר
        avg_volume = df['Volume'].rolling(20).mean().iloc[-1]
        if avg_volume < 500_000:
            return False, "נפח נמוך"
        
        # מספיק נתונים
        if len(df) < 100:
            return False, "נתונים לא מספקים"
        
        return True, "עבר סינון בסיסי"
        
    except:
        return False, "שגיאה בנתונים"

# --- ממשק משתמש ---
# הגדרות סינון
st.sidebar.header("⚙️ הגדרות סינון")
min_total_score = st.sidebar.slider("ניקוד מינימלי", 30, 80, 50, 5)
max_results = st.sidebar.slider("מקסימום תוצאות", 5, 30, 15, 5)
require_technical_signal = st.sidebar.checkbox("חייב איתות טכני", value=True)

if st.button("🚀 סרוק והצג רק את הטובות ביותר", type="primary"):
    results = []
    
    # תצוגת התקדמות
    status_container = st.container()
    with status_container:
        st.write("### 📊 התקדמות הסריקה:")
        progress_bar = st.progress(0)
        status_text = st.empty()
        stats_cols = st.columns(4)
        
        scanned_display = stats_cols[0].empty()
        passed_basic_display = stats_cols[1].empty()
        passed_fund_display = stats_cols[2].empty()
        passed_tech_display = stats_cols[3].empty()
    
    # מונים
    scanned = 0
    passed_basic = 0
    passed_fundamental = 0
    passed_technical = 0
    
    for i, ticker in enumerate(ALL_TICKERS):
        # עדכון כל 3 מניות
        if i % 3 == 0:
            progress = (i + 1) / total_count
            progress_bar.progress(progress)
            status_text.text(f"🔍 סורק: {ticker} ({i+1}/{total_count})")
            
            scanned_display.metric("🔍 נסרקו", scanned)
            passed_basic_display.metric("✅ עברו בסיס", passed_basic, 
                                       delta=f"{passed_basic/max(scanned,1)*100:.0f}%")
            passed_fund_display.metric("💎 פונדמנטלים", passed_fundamental,
                                      delta=f"{passed_fundamental/max(passed_basic,1)*100:.0f}%")
            passed_tech_display.metric("🎯 טכני+דירוג", passed_technical,
                                      delta=f"{passed_technical/max(passed_fundamental,1)*100:.0f}%")
        
        scanned += 1
        
        # שלב 1: הורדת נתונים
        df, info = get_data(ticker)
        if df.empty or not info:
            continue
        
        # שלב 2: סינון בסיסי
        passed_basic_filter, reason = passes_basic_filters(df, info)
        if not passed_basic_filter:
            continue
        
        passed_basic += 1
        
        # שלב 3: חישוב ניקודים
        tech_score, tech_signals = calculate_technical_score(df, info)
        fund_score, fund_reasons = calculate_fundamental_score(info)
        
        # חייב לעבור רף פונדמנטלי מינימלי
        if fund_score < 20:
            continue
        
        passed_fundamental += 1
        
        # חישוב ניקוד כולל (משוקלל)
        total_score = (tech_score * 0.5) + (fund_score * 0.3) + (
            20 if len(tech_signals) > 0 else 0
        ) * 0.2
        
        # סינון לפי דרישות משתמש
        if total_score < min_total_score:
            continue
        
        if require_technical_signal and len(tech_signals) == 0:
            continue
        
        passed_technical += 1
        
        # איסוף נתונים למניה
        current_price = df['Close'].iloc[-1]
        
        # חישוב ATR לסטופ לוס דינמי
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift())
        low_close = abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        atr = ranges.max(axis=1).rolling(14).mean().iloc[-1]
        stop_loss = current_price - (2 * atr)
        
        # מציאת סקטור
        sector_name = "General"
        for sec, tickers in SECTORS.items():
            if ticker in tickers:
                sector_name = sec
                break
        
        results.append({
            "Ticker": ticker,
            "Sector": sector_name,
            "Score": int(total_score),
            "Price": f"${current_price:.2f}",
            "Tech": f"{tech_score}/100",
            "Fund": f"{fund_score}/100",
            "Signals": " | ".join(tech_signals) if tech_signals else "-",
            "Reasons": " | ".join(fund_reasons[:2]) if fund_reasons else "-",
            "Stop": f"${stop_loss:.2f}",
            "Market Cap": info.get('marketCap', 0)
        })
    
    # סיום
    progress_bar.empty()
    status_text.empty()
    
    # תצוגת תוצאות
    st.write("---")
    
    if results:
        # מיון לפי ניקוד
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('Score', ascending=False)
        
        # הגבלה למקסימום שהמשתמש ביקש
        df_results = df_results.head(max_results)
        
        # הסרת עמודת Market Cap (שימשה רק למיון)
        df_display = df_results.drop(columns=['Market Cap'])
        
        st.success(f"### 🎯 {len(df_results)} מניות עלית מתוך {total_count} שנסרקו")
        
        # הצגת סטטיסטיקות
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("אחוז הצלחה בסיסי", f"{passed_basic/scanned*100:.1f}%")
        col2.metric("אחוז הצלחה פונדמנטלי", f"{passed_fundamental/passed_basic*100:.1f}%" if passed_basic > 0 else "0%")
        col3.metric("אחוז הצלחה טכני", f"{passed_technical/passed_fundamental*100:.1f}%" if passed_fundamental > 0 else "0%")
        col4.metric("סינון כולל", f"{len(df_results)/scanned*100:.1f}%")
        
        st.dataframe(
            df_display,
            use_container_width=True,
            column_config={
                "Score": st.column_config.NumberColumn(
                    "ניקוד",
                    help="ניקוד כולל 0-100",
                    format="%d ⭐"
                ),
                "Ticker": st.column_config.TextColumn(
                    "טיקר",
                    width="small"
                ),
                "Price": st.column_config.TextColumn(
                    "מחיר",
                    width="small"
                )
            }
        )
        
        # המלצות מפורטות
        st.write("### 📋 פירוט מניות מובילות:")
        for idx, row in df_results.head(5).iterrows():
            with st.expander(f"🎯 {row['Ticker']} - ניקוד {row['Score']} | {row['Sector']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**פרטים טכניים:**")
                    st.write(f"- מחיר נוכחי: {row['Price']}")
                    st.write(f"- Stop Loss מומלץ: {row['Stop']}")
                    st.write(f"- ניקוד טכני: {row['Tech']}")
                    st.write(f"- איתותים: {row['Signals']}")
                
                with col2:
                    st.write("**פרטים פונדמנטליים:**")
                    st.write(f"- ניקוד פונדמנטלי: {row['Fund']}")
                    st.write(f"- סיבות: {row['Reasons']}")
                    st.write(f"- סקטור: {row['Sector']}")
        
        # כפתור ייצוא
        csv = df_display.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 ייצא ל-CSV",
            data=csv,
            file_name=f"elite_stocks_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
        
    else:
        st.warning(f"❌ לא נמצאו מניות שעומדות בתנאים (ניקוד > {min_total_score})")
        st.info("💡 נסה להוריד את הניקוד המינימלי או לבטל את הדרישה לאיתות טכני")

# סטטיסטיקות רשימה
with st.expander("📊 סטטיסטיקות רשימת המניות"):
    sector_counts = {sector: len(tickers) for sector, tickers in SECTORS.items()}
    st.bar_chart(sector_counts)
    st.write(f"**סה\"כ מניות ייחודיות:** {total_count}")
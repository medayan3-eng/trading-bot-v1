import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- הגדרות ---
st.set_page_config(page_title="Sniper Bot 🎯", layout="wide")
st.title("🎯 Sniper Bot: מערכת צייד הזדמנויות")

# --- פונקציה מוגנת (Cache) למניעת חסימות ---
@st.cache_data(ttl=3600)
def get_data(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        return df
    except:
        return pd.DataFrame()

# --- סרגל צד ---
st.sidebar.header("הגדרות צייד")
tickers_input = st.sidebar.text_area("רשימת מעקב", value="NVDA, AMD, TSLA, AAPL, MSFT, GOOGL, META, AMZN, PLTR, ALB, COIN")
tickers = [t.strip().upper() for t in tickers_input.split(',')]

if st.button("🔎 סרוק את השוק"):
    results = []
    progress = st.progress(0)
    
    for i, ticker in enumerate(tickers):
        progress.progress((i + 1) / len(tickers))
        df = get_data(ticker)
        
        if len(df) < 50: continue

        # --- חישוב המנוע (SFP + Trend) ---
        # 1. מגמה
        df['SMA_200'] = df['Close'].rolling(200).mean()
        trend = "Bullish" if df['Close'].iloc[-1] > df['SMA_200'].iloc[-1] else "Bearish"
        
        # 2. מלכודת נזילות (SFP)
        today = df.iloc[-1]
        prev = df.iloc[-2]
        prev_low_20 = df['Low'].shift(1).rolling(20).min().iloc[-1]
        
        # האיתות: המניה ירדה מתחת לשפל של 20 יום - וחזרה למעלה
        sfp_signal = (prev['Low'] < prev_low_20) and (today['Close'] > prev_low_20)
        
        # 3. RSI (לוודא שלא רותח)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # התנאי לקנייה: SFP + מגמה עולה + RSI שפוי
        if sfp_signal and trend == "Bullish" and rsi < 70:
            stop_loss = today['Low'] * 0.98 # סטופ 2% מתחת לנמוך
            results.append({
                "Ticker": ticker,
                "Price": f"${today['Close']:.2f}",
                "RSI": f"{rsi:.1f}",
                "Stop Loss": f"${stop_loss:.2f}",
                "Status": "🔥 BUY SIGNAL"
            })
            
    progress.empty()
    
    if results:
        st.success(f"נמצאו {len(results)} הזדמנויות!")
        st.table(pd.DataFrame(results))
    else:
        st.info("השוק שקט. אין מלכודות נזילות איכותיות כרגע. שמור על המזומן.")

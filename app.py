import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import math
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="The Commander 🚀", layout="wide")
st.title("⚡ The Commander: AI Trading Scanner")

# --- פונקציות הנדסיות עם Caching (מונע חסימות) ---
@st.cache_data(ttl=3600) # שומר נתונים בזיכרון למשך שעה
def get_data(ticker, period="1y"):
    """פונקציה מוגנת למשיכת נתונים"""
    try:
        df = yf.download(ticker, period=period, progress=False)
        # תיקון למבנה החדש של yfinance
        if not df.empty and isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        return df
    except Exception as e:
        return pd.DataFrame()

# --- סרגל צד ---
st.sidebar.header("⚙️ הגדרות משתמש")
account_size = st.sidebar.number_input("גודל תיק ($)", value=10000, step=1000)
risk_per_trade = st.sidebar.slider("סיכון לעסקה (%)", 0.5, 3.0, 2.0) / 100
tickers_input = st.sidebar.text_area("רשימת מניות", value="NVDA, AMD, MSFT, AAPL, GOOGL, META, TSLA, AVGO, PLTR, GEV, AMZN, INTC")
tickers = [t.strip().upper() for t in tickers_input.split(',')]

# --- לוגיקה ראשית ---
def run_scanner():
    results = []
    
    # שלב 1: משיכת נתוני מדד ייחוס (SPY)
    spy_df = get_data("SPY", period="3mo")
    
    if spy_df.empty:
        st.error("⚠️ תקלה בחיבור ל-Yahoo Finance (SPY). נסה שוב בעוד דקה.")
        return []
        
    spy_return = (spy_df['Close'].iloc[-1] - spy_df['Close'].iloc[0]) / spy_df['Close'].iloc[0]

    # סרגל התקדמות
    progress_bar = st.progress(0)
    status = st.empty()
    
    total = len(tickers)
    for i, ticker in enumerate(tickers):
        status.text(f"סורק נתונים עבור: {ticker}...")
        progress_bar.progress((i + 1) / total)
        
        # משיכת נתונים למניה
        df = get_data(ticker, period="1y")
        
        if df.empty or len(df) < 200: continue # דלג אם אין מספיק נתונים

        try:
            # חישוב אינדיקטורים
            df['SMA_50'] = df['Close'].rolling(50).mean()
            df['SMA_200'] = df['Close'].rolling(200).mean()
            df['Prev_Low'] = df['Low'].shift(1).rolling(20).min()
            
            # ATR
            df['TR'] = np.maximum((df['High'] - df['Low']), 
                       np.maximum(abs(df['High'] - df['Close'].shift(1)), 
                                  abs(df['Low'] - df['Close'].shift(1))))
            df['ATR'] = df['TR'].rolling(14).mean()

            # RS Score
            stock_ret = (df['Close'].iloc[-1] - df['Close'].iloc[-60]) / df['Close'].iloc[-60]
            rs_score = stock_ret - spy_return

            # בדיקת איתות
            today = df.iloc[-1]
            trend = "Bearish"
            if today['SMA_50'] > today['SMA_200']: trend = "Bullish"
            
            # הטריגר: מגמה עולה + SFP
            if (trend == "Bullish") and \
               (today['Low'] < today['Prev_Low']) and \
               (today['Close'] > today['Prev_Low']):
                
                stop_loss = today['Close'] - (1 * today['ATR'])
                take_profit = today['Close'] + (2 * today['ATR'])
                risk_amt = today['Close'] - stop_loss
                qty = math.floor((account_size * risk_per_trade) / risk_amt)
                
                if qty > 0:
                    results.append({
                        'Ticker': ticker,
                        'Price': float(today['Close']),
                        'RS Score': round(rs_score * 100, 2),
                        'Qty': qty,
                        'Stop Loss': round(stop_loss, 2),
                        'Take Profit': round(take_profit, 2)
                    })
        except:
            continue
            
    progress_bar.empty()
    status.empty()
    return results

# --- כפתור הפעלה ---
if st.button('🚀 הרץ סריקת שוק', use_container_width=True):
    with st.spinner('המפקד עובד...'):
        data = run_scanner()
        
    if data:
        st.success(f"נמצאו {len(data)} הזדמנויות!")
        df_res = pd.DataFrame(data).sort_values(by='RS Score', ascending=False)
        st.dataframe(df_res, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📋 פקודות לביצוע (העתק-הדבק)")
        for _, row in df_res.iterrows():
            st.code(f"{row['Ticker']} | Qty: {row['Qty']} | BUY: {row['Price']:.2f} | SL: {row['Stop Loss']:.2f} | TP: {row['Take Profit']:.2f}")
    else:
        st.info("הסריקה הסתיימה. אין איתותים כרגע. המתן למחר.")

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def get_institutional_ownership(ticker: str) -> float:
    """
    Returns institutional ownership % (0-100).
    Uses yfinance institutional holders data.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info
        inst_pct = info.get('heldPercentInstitutions', None)
        if inst_pct is not None:
            return round(float(inst_pct) * 100, 1)
        return None
    except:
        return None


def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_bollinger(series, period=20, std_dev=2.0):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    # BB%B: where is price within the bands (0 = lower band, 1 = upper band)
    pct_b = (series - lower) / (upper - lower)
    return upper, mid, lower, pct_b


def get_trend_4weeks(df):
    """Murphy: check if uptrend over last 4 weeks (higher highs + higher lows)"""
    if len(df) < 20:
        return 0
    last_4w = df.tail(20)
    # Simple: price change over 4 weeks
    start_price = last_4w['Close'].iloc[0]
    end_price = last_4w['Close'].iloc[-1]
    pct_change = ((end_price - start_price) / start_price) * 100
    
    # Also check: at least 3 of last 4 weekly closes higher than previous
    weekly = last_4w['Close'].resample('W').last()
    if len(weekly) >= 3:
        upgrades = sum(1 for i in range(1, len(weekly)) if weekly.iloc[i] > weekly.iloc[i-1])
        if upgrades >= 2:
            return float(pct_change)
    
    return float(pct_change) if pct_change > 0 else 0


def calculate_indicators(ticker: str, params: dict) -> dict | None:
    """Download data and calculate all indicators for a ticker."""
    try:
        # Download enough history
        df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 60:
            return None
        
        df = df.copy()
        close = df['Close'].squeeze()
        volume = df['Volume'].squeeze()
        
        # Basic data
        current_price = float(close.iloc[-1])
        if current_price < params['min_price']:
            return None
        
        # Volume check — average 20-day volume
        avg_vol = float(volume.rolling(20).mean().iloc[-1])
        if avg_vol < params['min_volume']:
            return None
        
        # Volume ratio (vs 50-day avg)
        avg_vol_50 = float(volume.rolling(50).mean().iloc[-1])
        volume_ratio = float(volume.iloc[-1]) / avg_vol_50 if avg_vol_50 > 0 else 1.0
        
        # Moving averages
        ma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else None
        ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
        ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
        
        # Trend filters
        above_200 = (ma200 is not None) and (current_price > ma200)
        above_50 = (ma50 is not None) and (current_price > ma50)
        above_20 = (ma20 is not None) and (current_price > ma20)
        near_50 = (ma50 is not None) and (current_price >= ma50 * 0.98)  # within 2% of MA50
        
        # Murphy: must be above 200 AND above or near 50
        if params['require_above_200'] and not above_200:
            return None
        if params['require_above_50'] and not (above_50 or near_50):
            return None
        if params['require_above_20'] and not above_20:
            return None
        
        # RSI
        rsi_series = calculate_rsi(close, params['rsi_period'])
        current_rsi = float(rsi_series.iloc[-1])
        if pd.isna(current_rsi) or current_rsi > params['rsi_max']:
            return None
        
        # Bollinger Bands
        bb_upper, bb_mid, bb_lower, bb_pct = calculate_bollinger(
            close, params['bb_period'], params['bb_std']
        )
        current_bb_pct = float(bb_pct.iloc[-1])
        if pd.isna(current_bb_pct) or current_bb_pct > 0.35:
            return None  # not near lower band
        
        # 4-Week trend (Murphy requirement)
        trend_4w = get_trend_4weeks(df)
        if trend_4w <= 0:
            return None  # must be in uptrend
        
        # ── Institutional Ownership ──────────────────────────────────
        inst_pct = get_institutional_ownership(ticker)
        min_inst = params.get('min_institutional', 0)
        if min_inst > 0 and (inst_pct is None or inst_pct < min_inst):
            return None

        # ── Signal Freshness: only pass if TODAY's bar triggers the signal ──
        # (RSI and BB%B must have crossed the threshold in the LAST 3 days)
        rsi_series_full = calculate_rsi(close, params['rsi_period'])
        _, _, _, bb_pct_series = calculate_bollinger(close, params['bb_period'], params['bb_std'])
        
        # Check: was the signal NOT active 3 days ago? (i.e., it's fresh)
        lookback = 3
        if len(rsi_series_full) > lookback and len(bb_pct_series) > lookback:
            prev_rsi = float(rsi_series_full.iloc[-lookback-1])
            prev_bb = float(bb_pct_series.iloc[-lookback-1])
            signal_is_fresh = (
                prev_rsi > params['rsi_max'] or  # RSI just crossed below threshold
                prev_bb > 0.35                    # BB just crossed into oversold zone
            )
        else:
            signal_is_fresh = True  # not enough data, assume fresh

        # ── Beta (approximate using SPY) ─────────────────────────────
        try:
            spy = yf.download("SPY", period="6mo", interval="1d", progress=False, auto_adjust=True)
            if not spy.empty and len(spy) >= 60:
                stock_ret = close.pct_change().dropna()
                spy_ret = spy['Close'].squeeze().pct_change().dropna()
                # Align
                common_idx = stock_ret.index.intersection(spy_ret.index)
                if len(common_idx) >= 30:
                    s = stock_ret.loc[common_idx]
                    m = spy_ret.loc[common_idx]
                    cov = np.cov(s, m)[0][1]
                    var_m = np.var(m)
                    beta = float(cov / var_m) if var_m > 0 else 1.0
                else:
                    beta = 1.0
            else:
                beta = 1.0
        except:
            beta = 1.0
        
        if beta < params['min_beta']:
            return None
        
        # Scoring (0-10)
        score = 0
        
        # RSI score (lower = more oversold = better opportunity)
        if current_rsi < 25: score += 3
        elif current_rsi < 30: score += 2.5
        elif current_rsi < 35: score += 2
        elif current_rsi < 40: score += 1.5
        
        # BB score (lower in band = better)
        if current_bb_pct < 0.05: score += 3
        elif current_bb_pct < 0.1: score += 2.5
        elif current_bb_pct < 0.2: score += 2
        elif current_bb_pct < 0.35: score += 1
        
        # Trend score
        if trend_4w > 5: score += 1.5
        elif trend_4w > 2: score += 1
        elif trend_4w > 0: score += 0.5
        
        # MA alignment score
        if above_200: score += 0.5
        if above_50: score += 0.5
        if above_20: score += 0.5
        
        # Volume surge bonus
        if volume_ratio > 1.5: score += 0.5
        
        # Institutional ownership bonus
        if inst_pct is not None:
            if inst_pct >= 60: score += 1.0
            elif inst_pct >= 40: score += 0.7
            elif inst_pct >= 30: score += 0.5
        
        # Fresh signal bonus
        if signal_is_fresh:
            score += 0.5

        score = min(10.0, score)
        
        # Get company info
        try:
            info = yf.Ticker(ticker).fast_info
            name = getattr(info, 'company_name', ticker)
        except:
            name = ticker
        
        return {
            "ticker": ticker,
            "name": name,
            "price": current_price,
            "rsi": current_rsi,
            "ma20": ma20,
            "ma50": ma50,
            "ma200": ma200,
            "above_200": above_200,
            "above_50": above_50,
            "above_20": above_20,
            "near_50": near_50,
            "bb_pct": current_bb_pct,
            "bb_upper": float(bb_upper.iloc[-1]) if not pd.isna(bb_upper.iloc[-1]) else None,
            "bb_lower": float(bb_lower.iloc[-1]) if not pd.isna(bb_lower.iloc[-1]) else None,
            "trend_4w": trend_4w,
            "beta": beta,
            "avg_volume": avg_vol,
            "volume_ratio": volume_ratio,
            "institutional_pct": inst_pct,
            "signal_fresh": signal_is_fresh,
            "signal_date": datetime.today().strftime('%Y-%m-%d'),
            "score": round(score, 1),
            "passes_filter": True
        }
    
    except Exception as e:
        return None


def run_screener(universe: list, params: dict) -> list:
    """Run screener on a list of tickers."""
    results = []
    for ticker in universe:
        r = calculate_indicators(ticker, params)
        if r:
            results.append(r)
    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    return results

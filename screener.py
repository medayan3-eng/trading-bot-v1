import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def get_institutional_ownership(ticker: str):
    try:
        info = yf.Ticker(ticker).info
        val = info.get('heldPercentInstitutions')
        if val is not None:
            return round(float(val) * 100, 1)
    except:
        pass
    return None


def calculate_rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_bollinger(series, period=20, std_dev=2.0):
    mid   = series.rolling(period).mean()
    std   = series.rolling(period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    pct_b = (series - lower) / (upper - lower)
    return upper, mid, lower, pct_b


def get_trend_4weeks(close):
    """
    Returns % change over last 20 trading days.
    Positive = uptrend. No weekly-resample requirement (that was too strict).
    """
    if len(close) < 21:
        return 0.0
    start = float(close.iloc[-21])
    end   = float(close.iloc[-1])
    if start <= 0:
        return 0.0
    return round((end - start) / start * 100, 2)


def calculate_indicators(ticker: str, params: dict):
    """
    Returns dict with all indicators if stock passes filters, else None.
    Also returns a 'fail_reason' for debugging (not shown in UI).
    """
    try:
        df = yf.download(
            ticker, period="1y", interval="1d",
            progress=False, auto_adjust=True
        )

        if df is None or df.empty or len(df) < 50:
            return None

        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close  = df['Close'].squeeze()
        volume = df['Volume'].squeeze()

        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        if isinstance(volume, pd.DataFrame):
            volume = volume.iloc[:, 0]

        close  = close.dropna()
        volume = volume.dropna()

        if len(close) < 50:
            return None

        # ── Price filter ──────────────────────────────────────────────
        current_price = float(close.iloc[-1])
        if current_price < params.get('min_price', 15):
            return None

        # ── Volume filter ─────────────────────────────────────────────
        avg_vol = float(volume.rolling(20).mean().iloc[-1])
        if pd.isna(avg_vol) or avg_vol < params.get('min_volume', 300_000):
            return None

        avg_vol_50   = float(volume.rolling(50).mean().iloc[-1])
        volume_ratio = float(volume.iloc[-1]) / avg_vol_50 if avg_vol_50 > 0 else 1.0

        # ── Moving averages ───────────────────────────────────────────
        ma20  = float(close.rolling(20).mean().iloc[-1])  if len(close) >= 20  else None
        ma50  = float(close.rolling(50).mean().iloc[-1])  if len(close) >= 50  else None
        ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

        above_200 = bool(ma200 and current_price > ma200)
        above_50  = bool(ma50  and current_price > ma50)
        above_20  = bool(ma20  and current_price > ma20)
        near_50   = bool(ma50  and current_price >= ma50 * 0.97)  # within 3%

        if params.get('require_above_200') and not above_200:
            return None
        if params.get('require_above_50') and not (above_50 or near_50):
            return None
        if params.get('require_above_20') and not above_20:
            return None

        # ── RSI ───────────────────────────────────────────────────────
        rsi_s       = calculate_rsi(close, params.get('rsi_period', 14))
        current_rsi = float(rsi_s.iloc[-1])
        rsi_max     = params.get('rsi_max', 45)
        if pd.isna(current_rsi) or current_rsi > rsi_max:
            return None

        # ── Bollinger Bands ───────────────────────────────────────────
        bb_upper, bb_mid, bb_lower, bb_pct_s = calculate_bollinger(
            close, params.get('bb_period', 20), params.get('bb_std', 2.0)
        )
        current_bb_pct = float(bb_pct_s.iloc[-1])
        # Relaxed: allow up to 0.5 (middle of band) — BB is informational, not hard filter
        if pd.isna(current_bb_pct):
            current_bb_pct = 0.5

        # ── 4-Week trend ──────────────────────────────────────────────
        trend_4w = get_trend_4weeks(close)
        # Murphy: must be in uptrend over 4 weeks — keep this but soften to > -2%
        # (slight pullback in uptrend is fine, that's our entry)
        if trend_4w < -5.0:
            return None

        # ── Beta ──────────────────────────────────────────────────────
        beta = 1.0
        try:
            spy     = yf.download("SPY", period="6mo", interval="1d",
                                   progress=False, auto_adjust=True)
            if spy is not None and not spy.empty and len(spy) >= 40:
                if isinstance(spy.columns, pd.MultiIndex):
                    spy.columns = spy.columns.get_level_values(0)
                spy_close  = spy['Close'].squeeze()
                stock_ret  = close.pct_change().dropna()
                spy_ret    = spy_close.pct_change().dropna()
                common     = stock_ret.index.intersection(spy_ret.index)
                if len(common) >= 30:
                    s   = stock_ret.loc[common].values
                    m   = spy_ret.loc[common].values
                    cov = np.cov(s, m)[0][1]
                    var = np.var(m)
                    if var > 0:
                        beta = round(float(cov / var), 2)
        except:
            beta = 1.0

        if beta < params.get('min_beta', 0.8):
            return None

        # ── Institutional ownership ───────────────────────────────────
        inst_pct = get_institutional_ownership(ticker)
        min_inst = params.get('min_institutional', 0)
        # Only filter if we actually got data AND min_inst > 0
        if min_inst > 0 and inst_pct is not None and inst_pct < min_inst:
            return None

        # ── Signal freshness ──────────────────────────────────────────
        lookback = 4
        signal_is_fresh = True
        if len(rsi_s) > lookback and len(bb_pct_s) > lookback:
            prev_rsi = float(rsi_s.iloc[-lookback - 1])
            prev_bb  = float(bb_pct_s.iloc[-lookback - 1])
            signal_is_fresh = (prev_rsi > rsi_max) or (prev_bb > 0.4)

        # ── Scoring ───────────────────────────────────────────────────
        score = 0.0

        # RSI (oversold depth)
        if   current_rsi < 25: score += 3.0
        elif current_rsi < 30: score += 2.5
        elif current_rsi < 35: score += 2.0
        elif current_rsi < 40: score += 1.5
        elif current_rsi < 45: score += 1.0

        # BB position
        if   current_bb_pct < 0.05: score += 3.0
        elif current_bb_pct < 0.10: score += 2.5
        elif current_bb_pct < 0.20: score += 2.0
        elif current_bb_pct < 0.35: score += 1.5
        elif current_bb_pct < 0.50: score += 0.5

        # Trend
        if   trend_4w >  5: score += 1.5
        elif trend_4w >  1: score += 1.0
        elif trend_4w > -2: score += 0.5   # slight pullback still counts

        # MA alignment
        if above_200: score += 0.5
        if above_50:  score += 0.5
        if above_20:  score += 0.3

        # Volume surge
        if volume_ratio > 2.0: score += 0.7
        elif volume_ratio > 1.5: score += 0.4

        # Institutional
        if inst_pct:
            if   inst_pct >= 60: score += 1.0
            elif inst_pct >= 40: score += 0.7
            elif inst_pct >= 30: score += 0.5

        # Fresh signal bonus
        if signal_is_fresh:
            score += 0.5

        score = round(min(10.0, score), 1)

        # Company name
        name = ticker
        try:
            fi   = yf.Ticker(ticker).fast_info
            name = getattr(fi, 'company_name', ticker) or ticker
        except:
            pass

        return {
            "ticker":           ticker,
            "name":             name,
            "price":            current_price,
            "rsi":              round(current_rsi, 1),
            "ma20":             ma20,
            "ma50":             ma50,
            "ma200":            ma200,
            "above_200":        above_200,
            "above_50":         above_50,
            "above_20":         above_20,
            "near_50":          near_50,
            "bb_pct":           round(current_bb_pct, 3),
            "bb_upper":         float(bb_upper.iloc[-1]) if not pd.isna(bb_upper.iloc[-1]) else None,
            "bb_lower":         float(bb_lower.iloc[-1]) if not pd.isna(bb_lower.iloc[-1]) else None,
            "trend_4w":         trend_4w,
            "beta":             beta,
            "avg_volume":       avg_vol,
            "volume_ratio":     round(volume_ratio, 2),
            "institutional_pct":inst_pct,
            "signal_fresh":     signal_is_fresh,
            "signal_date":      datetime.today().strftime('%Y-%m-%d'),
            "score":            score,
            "passes_filter":    True,
        }

    except Exception:
        return None


def run_screener(universe: list, params: dict) -> list:
    results = []
    for ticker in universe:
        r = calculate_indicators(ticker, params)
        if r:
            results.append(r)
    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    return results

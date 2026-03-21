import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _get_ohlcv(ticker: str, period: str = "1y") -> pd.DataFrame:
    """
    Download OHLCV for a single ticker — thread-safe version.
    Uses download() with a single ticker string (no MultiIndex).
    """
    try:
        df = yf.download(
            tickers=ticker,
            period=period,
            interval="1d",
            auto_adjust=True,
            actions=False,
            progress=False,
            threads=False,      # critical: no internal threading
            group_by="ticker",  # single ticker → flat columns
        )

        if df is None or df.empty:
            return pd.DataFrame()

        # With a single ticker and group_by="ticker",
        # columns may be MultiIndex like (metric, ticker) — flatten
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Verify Close column exists
        if 'Close' not in df.columns:
            return pd.DataFrame()

        return df[['Open','High','Low','Close','Volume']].dropna(subset=['Close']).copy()

    except Exception:
        return pd.DataFrame()


def _rsi(close: pd.Series, period: int = 14) -> float:
    """
    RSI using Wilder's smoothing method (EWM with alpha=1/period).
    This matches TradingView, investing.com, and most professional platforms.
    """
    if len(close) < period * 2:
        return 50.0
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta.clip(upper=0))
    # Wilder's smoothing = EWM with com=period-1
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    val = float(rsi.iloc[-1])
    return round(val, 1) if not np.isnan(val) else 50.0


def _bb_pct(close: pd.Series, period: int = 20, std_dev: float = 2.0):
    if len(close) < period + 2:
        return 0.5, None, None
    mid   = close.rolling(period).mean()
    sigma = close.rolling(period).std()
    upper = mid + std_dev * sigma
    lower = mid - std_dev * sigma
    pct   = (close - lower) / (upper - lower)
    val   = float(pct.iloc[-1])
    u     = float(upper.iloc[-1])
    l     = float(lower.iloc[-1])
    return (round(val, 3) if not np.isnan(val) else 0.5,
            round(u, 2)   if not np.isnan(u)   else None,
            round(l, 2)   if not np.isnan(l)   else None)


def _trend_pct(close: pd.Series, days: int = 20) -> float:
    if len(close) < days + 2:
        return 0.0
    start = float(close.iloc[-days - 1])
    end   = float(close.iloc[-1])
    if start <= 0:
        return 0.0
    return round((end - start) / start * 100, 2)


def _beta(close: pd.Series) -> float:
    """Calculate beta vs SPY."""
    try:
        spy_df = _get_ohlcv("SPY", period="6mo")
        if spy_df.empty or len(spy_df) < 40:
            return 1.0
        spy_close  = spy_df['Close']
        stock_ret  = close.pct_change().dropna()
        spy_ret    = spy_close.pct_change().dropna()
        common     = stock_ret.index.intersection(spy_ret.index)
        if len(common) < 30:
            return 1.0
        s = stock_ret.loc[common].values.astype(float)
        m = spy_ret.loc[common].values.astype(float)
        cov = np.cov(s, m)[0][1]
        var = np.var(m)
        return round(float(cov / var), 2) if var > 0 else 1.0
    except Exception:
        return 1.0


def calculate_indicators(ticker: str, params: dict):
    try:
        df = _get_ohlcv(ticker, period="1y")
        if df.empty or len(df) < 50:
            return None

        close  = df['Close']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series(dtype=float)

        # ── Price ─────────────────────────────────────────────────────
        price = round(float(close.iloc[-1]), 2)
        if price < params.get('min_price', 15):
            return None

        # ── Volume ────────────────────────────────────────────────────
        if not volume.empty:
            avg_vol = float(volume.rolling(20).mean().iloc[-1])
            avg_vol_50 = float(volume.rolling(50).mean().iloc[-1])
            if np.isnan(avg_vol) or avg_vol < params.get('min_volume', 200_000):
                return None
            volume_ratio = float(volume.iloc[-1]) / avg_vol_50 if avg_vol_50 > 0 else 1.0
        else:
            avg_vol = 0
            volume_ratio = 1.0

        # ── Moving Averages ───────────────────────────────────────────
        ma20  = round(float(close.rolling(20).mean().iloc[-1]),  2) if len(close) >= 20  else None
        ma50  = round(float(close.rolling(50).mean().iloc[-1]),  2) if len(close) >= 50  else None
        ma200 = round(float(close.rolling(200).mean().iloc[-1]), 2) if len(close) >= 200 else None

        def valid(v): return v is not None and not np.isnan(v)

        above_200 = valid(ma200) and price > ma200
        above_50  = valid(ma50)  and price > ma50
        above_20  = valid(ma20)  and price > ma20
        near_50   = valid(ma50)  and price >= ma50 * 0.97

        if params.get('require_above_200') and not above_200:
            return None
        if params.get('require_above_50') and not (above_50 or near_50):
            return None
        if params.get('require_above_20') and not above_20:
            return None

        # ── RSI ───────────────────────────────────────────────────────
        rsi_period  = params.get('rsi_period', 14)
        rsi_max     = params.get('rsi_max', 50)
        rsi_min     = params.get('rsi_min', 0)
        current_rsi = _rsi(close, rsi_period)
        if current_rsi > rsi_max or current_rsi < rsi_min:
            return None

        # ── Bollinger Bands ───────────────────────────────────────────
        bb_period = params.get('bb_period', 20)
        bb_std    = params.get('bb_std', 2.0)
        current_bb_pct, bb_upper_v, bb_lower_v = _bb_pct(close, bb_period, bb_std)

        # ── 4-Week Trend ──────────────────────────────────────────────
        trend_4w = _trend_pct(close, 20)
        if trend_4w < -15.0:
            return None

        # ── Beta ──────────────────────────────────────────────────────
        min_beta = params.get('min_beta', 0.5)
        beta = _beta(close)
        if min_beta > 0 and beta < min_beta:
            return None

        # ── Institutional % (optional, don't reject if N/A) ──────────
        inst_pct = None
        min_inst = params.get('min_institutional', 0)
        if min_inst > 0:
            try:
                info = yf.Ticker(ticker).info
                raw  = info.get('heldPercentInstitutions')
                if raw is not None:
                    inst_pct = round(float(raw) * 100, 1)
                    if inst_pct < min_inst:
                        return None
            except Exception:
                pass  # don't reject, just no data

        # ── Signal Freshness ─────────────────────────────────────────
        signal_is_fresh = True
        try:
            delta = close.diff().dropna()
            g = delta.clip(lower=0).rolling(rsi_period).mean()
            l = (-delta.clip(upper=0)).rolling(rsi_period).mean()
            rsi_series = 100 - (100 / (1 + g / l))
            if len(rsi_series) > 5:
                prev_rsi = float(rsi_series.iloc[-5])
                signal_is_fresh = (not np.isnan(prev_rsi)) and (prev_rsi > rsi_max)
        except Exception:
            signal_is_fresh = True

        # ── Scoring ───────────────────────────────────────────────────
        score = 0.0

        if   current_rsi < 20: score += 4.0
        elif current_rsi < 25: score += 3.0
        elif current_rsi < 30: score += 2.5
        elif current_rsi < 35: score += 2.0
        elif current_rsi < 40: score += 1.5
        elif current_rsi < 50: score += 1.0
        else:                  score += 0.5

        if   current_bb_pct < 0.05: score += 3.0
        elif current_bb_pct < 0.10: score += 2.5
        elif current_bb_pct < 0.20: score += 2.0
        elif current_bb_pct < 0.35: score += 1.5
        elif current_bb_pct < 0.50: score += 0.5

        if   trend_4w >  5: score += 1.5
        elif trend_4w >  0: score += 1.0
        elif trend_4w > -5: score += 0.3

        if above_200: score += 0.5
        if above_50:  score += 0.5
        if above_20:  score += 0.3

        if volume_ratio > 2.0:   score += 0.7
        elif volume_ratio > 1.5: score += 0.4

        if signal_is_fresh: score += 0.5

        if inst_pct:
            if   inst_pct >= 60: score += 1.0
            elif inst_pct >= 40: score += 0.7
            elif inst_pct >= 30: score += 0.5

        score = round(min(10.0, score), 1)

        # ── Company name ──────────────────────────────────────────────
        name = ticker
        try:
            fi   = yf.Ticker(ticker).fast_info
            name = getattr(fi, 'company_name', None) or ticker
        except Exception:
            pass

        return {
            "ticker":            ticker,
            "name":              name,
            "price":             price,
            "rsi":               current_rsi,
            "ma20":              ma20,
            "ma50":              ma50,
            "ma200":             ma200,
            "above_200":         above_200,
            "above_50":          above_50,
            "above_20":          above_20,
            "near_50":           near_50,
            "bb_pct":            current_bb_pct,
            "bb_upper":          bb_upper_v,
            "bb_lower":          bb_lower_v,
            "trend_4w":          trend_4w,
            "beta":              beta,
            "avg_volume":        round(avg_vol, 0),
            "volume_ratio":      round(volume_ratio, 2),
            "institutional_pct": inst_pct,
            "signal_fresh":      signal_is_fresh,
            "signal_date":       datetime.today().strftime('%Y-%m-%d'),
            "score":             score,
            "passes_filter":     True,
        }

    except Exception:
        return None

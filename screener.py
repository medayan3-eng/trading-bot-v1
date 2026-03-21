import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def _safe_download(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Download and always return a clean single-level DataFrame or empty."""
    try:
        df = yf.download(ticker, period=period, interval="1d",
                         progress=False, auto_adjust=True, actions=False)
        if df is None or df.empty:
            return pd.DataFrame()
        # Flatten MultiIndex (yfinance ≥ 0.2.x returns MultiIndex when group_by='column')
        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(1, axis=1)
        # Keep only standard OHLCV columns
        cols = [c for c in ['Open','High','Low','Close','Volume'] if c in df.columns]
        return df[cols].copy()
    except Exception:
        return pd.DataFrame()


def _rsi(close: pd.Series, period: int = 14) -> float:
    """Return latest RSI value."""
    if len(close) < period + 5:
        return 50.0
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss
    rsi   = 100 - (100 / (1 + rs))
    val   = float(rsi.iloc[-1])
    return val if not np.isnan(val) else 50.0


def _bb_pct(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> float:
    """Return latest BB %B value (0=lower band, 1=upper band)."""
    if len(close) < period + 5:
        return 0.5
    mid   = close.rolling(period).mean()
    sigma = close.rolling(period).std()
    upper = mid + std_dev * sigma
    lower = mid - std_dev * sigma
    pct   = (close - lower) / (upper - lower)
    val   = float(pct.iloc[-1])
    return val if not np.isnan(val) else 0.5


def _trend_4w(close: pd.Series) -> float:
    """% change over last 20 trading days."""
    if len(close) < 22:
        return 0.0
    start = float(close.iloc[-21])
    end   = float(close.iloc[-1])
    if start <= 0:
        return 0.0
    return round((end - start) / start * 100, 2)


def calculate_indicators(ticker: str, params: dict):
    """
    Returns a result dict if stock passes all filters, else None.
    params keys used:
        min_price, min_volume, min_beta, rsi_max, rsi_period,
        require_above_200, require_above_50, require_above_20,
        bb_period, bb_std, min_institutional
    """
    try:
        df = _safe_download(ticker, period="1y")
        if df.empty or len(df) < 50:
            return None

        close  = df['Close'].dropna()
        volume = df['Volume'].dropna()

        if len(close) < 50:
            return None

        # ── Price ────────────────────────────────────────────────────
        price = float(close.iloc[-1])
        if price < params.get('min_price', 15):
            return None

        # ── Volume ───────────────────────────────────────────────────
        min_vol = params.get('min_volume', 200_000)
        avg_vol = float(volume.rolling(20).mean().iloc[-1])
        if np.isnan(avg_vol) or avg_vol < min_vol:
            return None
        avg_vol_50   = float(volume.rolling(50).mean().iloc[-1])
        volume_ratio = float(volume.iloc[-1]) / avg_vol_50 if avg_vol_50 > 0 else 1.0

        # ── Moving Averages ───────────────────────────────────────────
        ma20  = float(close.rolling(20).mean().iloc[-1])  if len(close) >= 20  else None
        ma50  = float(close.rolling(50).mean().iloc[-1])  if len(close) >= 50  else None
        ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

        above_200 = bool(ma200 and not np.isnan(ma200) and price > ma200)
        above_50  = bool(ma50  and not np.isnan(ma50)  and price > ma50)
        above_20  = bool(ma20  and not np.isnan(ma20)  and price > ma20)
        near_50   = bool(ma50  and not np.isnan(ma50)  and price >= ma50 * 0.97)

        if params.get('require_above_200') and not above_200:
            return None
        if params.get('require_above_50') and not (above_50 or near_50):
            return None
        if params.get('require_above_20') and not above_20:
            return None

        # ── RSI ───────────────────────────────────────────────────────
        rsi_period = params.get('rsi_period', 14)
        rsi_max    = params.get('rsi_max', 50)
        rsi_min    = params.get('rsi_min', 0)
        current_rsi = _rsi(close, rsi_period)
        if current_rsi > rsi_max or current_rsi < rsi_min:
            return None

        # ── Bollinger Bands (informational only, no hard filter) ──────
        bb_period = params.get('bb_period', 20)
        bb_std    = params.get('bb_std', 2.0)
        current_bb_pct = _bb_pct(close, bb_period, bb_std)

        bb_mid_s   = close.rolling(bb_period).mean()
        bb_sigma_s = close.rolling(bb_period).std()
        bb_upper_v = float((bb_mid_s + bb_std * bb_sigma_s).iloc[-1])
        bb_lower_v = float((bb_mid_s - bb_std * bb_sigma_s).iloc[-1])

        # ── 4-Week Trend ──────────────────────────────────────────────
        trend_4w = _trend_4w(close)
        if trend_4w < -15.0:   # only reject extreme downtrends
            return None

        # ── Beta vs SPY ───────────────────────────────────────────────
        beta = 1.0
        min_beta = params.get('min_beta', 0.5)
        if min_beta > 0:
            try:
                spy_df = _safe_download("SPY", period="6mo")
                if not spy_df.empty and len(spy_df) >= 40:
                    spy_close  = spy_df['Close'].dropna()
                    stock_ret  = close.pct_change().dropna()
                    spy_ret    = spy_close.pct_change().dropna()
                    common     = stock_ret.index.intersection(spy_ret.index)
                    if len(common) >= 30:
                        s_arr = stock_ret.loc[common].values.astype(float)
                        m_arr = spy_ret.loc[common].values.astype(float)
                        cov   = np.cov(s_arr, m_arr)[0][1]
                        var   = np.var(m_arr)
                        if var > 0:
                            beta = round(float(cov / var), 2)
            except Exception:
                beta = 1.0
            if beta < min_beta:
                return None

        # ── Institutional Ownership ───────────────────────────────────
        inst_pct = None
        min_inst = params.get('min_institutional', 0)
        if min_inst > 0:
            try:
                info     = yf.Ticker(ticker).info
                raw      = info.get('heldPercentInstitutions')
                if raw is not None:
                    inst_pct = round(float(raw) * 100, 1)
                    if inst_pct < min_inst:
                        return None
            except Exception:
                pass  # don't reject if we can't get the data

        # ── Signal Freshness ─────────────────────────────────────────
        signal_is_fresh = True
        try:
            lookback = 4
            rsi_series = close.diff()
            # simplified freshness: check if RSI crossed threshold in last 4 days
            rsi_full = pd.Series(index=close.index, dtype=float)
            delta = close.diff()
            g = delta.clip(lower=0).rolling(rsi_period).mean()
            l = (-delta.clip(upper=0)).rolling(rsi_period).mean()
            rsi_full = 100 - (100 / (1 + g / l))
            if len(rsi_full) > lookback + 1:
                prev_rsi = float(rsi_full.iloc[-lookback - 1])
                signal_is_fresh = prev_rsi > rsi_max
        except Exception:
            signal_is_fresh = True

        # ── Scoring ───────────────────────────────────────────────────
        score = 0.0

        if   current_rsi < 20: score += 4.0
        elif current_rsi < 25: score += 3.0
        elif current_rsi < 30: score += 2.5
        elif current_rsi < 35: score += 2.0
        elif current_rsi < 40: score += 1.5
        elif current_rsi < 45: score += 1.0
        elif current_rsi < 50: score += 0.5

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
        if volume_ratio > 2.0:  score += 0.7
        elif volume_ratio > 1.5: score += 0.4
        if signal_is_fresh: score += 0.5
        if inst_pct:
            if   inst_pct >= 60: score += 1.0
            elif inst_pct >= 40: score += 0.7
            elif inst_pct >= 30: score += 0.5

        score = round(min(10.0, score), 1)

        # ── Company name ─────────────────────────────────────────────
        name = ticker
        try:
            fi   = yf.Ticker(ticker).fast_info
            name = getattr(fi, 'company_name', None) or ticker
        except Exception:
            pass

        return {
            "ticker":            ticker,
            "name":              name,
            "price":             round(price, 2),
            "rsi":               round(current_rsi, 1),
            "ma20":              round(ma20, 2)  if ma20  else None,
            "ma50":              round(ma50, 2)  if ma50  else None,
            "ma200":             round(ma200, 2) if ma200 else None,
            "above_200":         above_200,
            "above_50":          above_50,
            "above_20":          above_20,
            "near_50":           near_50,
            "bb_pct":            round(current_bb_pct, 3),
            "bb_upper":          round(bb_upper_v, 2),
            "bb_lower":          round(bb_lower_v, 2),
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


def run_screener(universe: list, params: dict) -> list:
    results = []
    for ticker in universe:
        r = calculate_indicators(ticker, params)
        if r:
            results.append(r)
    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    return results

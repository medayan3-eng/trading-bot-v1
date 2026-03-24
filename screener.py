import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# ──────────────────────────────────────────────────────────────
#  DATA DOWNLOAD
# ──────────────────────────────────────────────────────────────
def _get_ohlcv(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        t  = yf.Ticker(ticker)
        df = t.history(period=period, interval="1d", auto_adjust=True, actions=False)
        if df is None or df.empty or 'Close' not in df.columns:
            return pd.DataFrame()
        cols = [c for c in ['Open','High','Low','Close','Volume'] if c in df.columns]
        return df[cols].dropna(subset=['Close']).copy()
    except Exception:
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────
#  INDICATORS
# ──────────────────────────────────────────────────────────────
def _rsi(close: pd.Series, period: int = 14) -> float:
    if len(close) < period * 2:
        return 50.0
    delta    = close.diff()
    avg_gain = delta.clip(lower=0).ewm(com=period-1, min_periods=period).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(com=period-1, min_periods=period).mean()
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    val = float(rsi.iloc[-1])
    return round(val, 1) if not np.isnan(val) else 50.0


def _bb(close: pd.Series, period: int = 20, std_dev: float = 2.0):
    if len(close) < period + 2:
        return 0.5, None, None
    mid, sigma = close.rolling(period).mean(), close.rolling(period).std()
    upper, lower = mid + std_dev * sigma, mid - std_dev * sigma
    pct = (close - lower) / (upper - lower)
    val = float(pct.iloc[-1])
    u, l = float(upper.iloc[-1]), float(lower.iloc[-1])
    return (round(val,3) if not np.isnan(val) else 0.5,
            round(u,2)   if not np.isnan(u)   else None,
            round(l,2)   if not np.isnan(l)   else None)


def _macd(close: pd.Series, fast=12, slow=26, signal=9):
    if len(close) < slow + signal + 5:
        return 0.0, 0.0, 0.0
    ema_fast   = close.ewm(span=fast, adjust=False).mean()
    ema_slow   = close.ewm(span=slow, adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line= macd_line.ewm(span=signal, adjust=False).mean()
    hist       = macd_line - signal_line
    return (round(float(macd_line.iloc[-1]),4),
            round(float(signal_line.iloc[-1]),4),
            round(float(hist.iloc[-1]),4))


def _trend_pct(close: pd.Series, days: int = 20) -> float:
    if len(close) < days + 2:
        return 0.0
    start = float(close.iloc[-days-1])
    end   = float(close.iloc[-1])
    return round((end-start)/start*100, 2) if start > 0 else 0.0


def _uptrend_52w(close: pd.Series) -> bool:
    """
    Murphy: true uptrend = price is higher now than 52 weeks ago
    AND the 50-day MA is above the 200-day MA (golden cross zone)
    AND price is above the 200-day MA.
    """
    if len(close) < 200:
        return False
    price   = float(close.iloc[-1])
    price_52w_ago = float(close.iloc[0])   # ~252 trading days, use first available
    ma50    = float(close.rolling(50).mean().iloc[-1])
    ma200   = float(close.rolling(200).mean().iloc[-1])
    return (price > price_52w_ago and   # higher than a year ago
            price > ma200 and            # above long-term trend
            ma50 > ma200)                # golden cross


def _relative_strength(close: pd.Series, spy_close: pd.Series) -> float:
    """RS = stock return / SPY return over last 63 days (3 months)."""
    try:
        if len(close) < 65 or len(spy_close) < 65:
            return 1.0
        common = close.index.intersection(spy_close.index)
        if len(common) < 60:
            return 1.0
        s = close.loc[common]
        m = spy_close.loc[common]
        stock_ret = float(s.iloc[-1]) / float(s.iloc[-63]) - 1
        spy_ret   = float(m.iloc[-1]) / float(m.iloc[-63]) - 1
        if spy_ret == 0:
            return 1.0
        return round(stock_ret / abs(spy_ret), 2)
    except Exception:
        return 1.0


def _beta(close: pd.Series, spy_close: pd.Series) -> float:
    try:
        common = close.pct_change().dropna().index.intersection(
                 spy_close.pct_change().dropna().index)
        if len(common) < 30:
            return 1.0
        s   = close.pct_change().dropna().loc[common].values.astype(float)
        m   = spy_close.pct_change().dropna().loc[common].values.astype(float)
        cov = np.cov(s, m)[0][1]
        var = np.var(m)
        return round(float(cov/var), 2) if var > 0 else 1.0
    except Exception:
        return 1.0


def _support_resistance(df: pd.DataFrame, window: int = 10, n: int = 3):
    """
    Find key static support/resistance levels.
    Returns (support, resistance, near_support).
    """
    try:
        close  = df['Close']
        high   = df['High']
        low    = df['Low']
        price  = float(close.iloc[-1])

        # Local highs and lows
        local_highs = []
        local_lows  = []
        for i in range(window, len(close)-window):
            if high.iloc[i] == high.iloc[i-window:i+window+1].max():
                local_highs.append(float(high.iloc[i]))
            if low.iloc[i] == low.iloc[i-window:i+window+1].min():
                local_lows.append(float(low.iloc[i]))

        # Cluster nearby levels (within 2%)
        def cluster(levels, pct=0.02):
            if not levels:
                return []
            levels = sorted(levels)
            clusters = [[levels[0]]]
            for lvl in levels[1:]:
                if abs(lvl - clusters[-1][-1]) / clusters[-1][-1] < pct:
                    clusters[-1].append(lvl)
                else:
                    clusters.append([lvl])
            return [round(np.mean(c), 2) for c in clusters if len(c) >= 2]

        supports    = cluster(local_lows)
        resistances = cluster(local_highs)

        # Nearest support below price
        sup  = max([s for s in supports    if s < price], default=None)
        res  = min([r for r in resistances if r > price], default=None)

        # Is price near support? (within 3%)
        near_support = sup is not None and abs(price - sup) / price < 0.03

        return sup, res, near_support
    except Exception:
        return None, None, False


def _fibonacci_levels(close: pd.Series) -> dict:
    """Fibonacci retracement from 52-week low to 52-week high."""
    try:
        low  = float(close.min())
        high = float(close.max())
        diff = high - low
        price = float(close.iloc[-1])
        levels = {
            "0%":    round(low, 2),
            "23.6%": round(high - 0.236 * diff, 2),
            "38.2%": round(high - 0.382 * diff, 2),
            "50%":   round(high - 0.500 * diff, 2),
            "61.8%": round(high - 0.618 * diff, 2),
            "100%":  round(high, 2),
        }
        # Which fib level is price nearest to?
        nearest = min(levels.items(), key=lambda x: abs(x[1] - price))
        return {"levels": levels, "nearest": nearest[0], "nearest_val": nearest[1]}
    except Exception:
        return {}


def _volume_spike(volume: pd.Series, threshold: float = 2.0) -> tuple:
    """Detects unusual volume. Returns (ratio, is_spike)."""
    try:
        avg_50 = float(volume.rolling(50).mean().iloc[-1])
        today  = float(volume.iloc[-1])
        if avg_50 <= 0:
            return 1.0, False
        ratio = round(today / avg_50, 2)
        return ratio, ratio >= threshold
    except Exception:
        return 1.0, False


def _chart_patterns(df: pd.DataFrame) -> list:
    """
    Detect basic chart patterns: double bottom, ascending triangle.
    Returns list of pattern names found.
    """
    patterns = []
    try:
        close = df['Close']
        low   = df['Low']
        high  = df['High']
        n     = len(close)
        if n < 40:
            return patterns

        price = float(close.iloc[-1])

        # ── Double Bottom (W pattern) ────────────────────────────────
        # Look for two similar lows in last 60 days with a bounce in between
        last60 = close.iloc[-60:]
        if len(last60) >= 40:
            half = len(last60) // 2
            low1 = float(last60.iloc[:half].min())
            low2 = float(last60.iloc[half:].min())
            mid_high = float(last60.iloc[half//2:half+half//2].max())
            if (abs(low1 - low2) / ((low1+low2)/2) < 0.03 and   # two similar lows
                mid_high > max(low1, low2) * 1.03 and             # bounce between
                price > mid_high * 0.98):                          # breakout
                patterns.append("Double Bottom (W)")

        # ── Ascending Triangle ───────────────────────────────────────
        # Flat resistance + rising lows
        last40_high = high.iloc[-40:]
        last40_low  = low.iloc[-40:]
        resistance_flat = (last40_high.max() - last40_high.min()) / last40_high.mean() < 0.04
        # Rising lows: fit linear trend
        lows_arr = last40_low.values
        x = np.arange(len(lows_arr))
        if len(x) > 5:
            slope = np.polyfit(x, lows_arr, 1)[0]
            if resistance_flat and slope > 0:
                patterns.append("Ascending Triangle")

    except Exception:
        pass
    return patterns


def _risk_reward(price: float, support: float, resistance: float,
                 stop_pct: float = 0.05) -> dict:
    """
    Calculate Risk/Reward ratio.
    Stop loss = support or price * (1 - stop_pct).
    Target    = resistance.
    Murphy rule: need at least 1:3 ratio.
    """
    try:
        stop_loss = support if support else price * (1 - stop_pct)
        if resistance is None or resistance <= price:
            return {"ratio": 0, "valid": False, "stop": round(stop_loss,2), "target": None}
        risk    = price - stop_loss
        reward  = resistance - price
        ratio   = round(reward / risk, 2) if risk > 0 else 0
        return {
            "ratio":  ratio,
            "valid":  ratio >= 1.5,          # lowered from 3 for more opportunities
            "stop":   round(stop_loss, 2),
            "target": round(resistance, 2),
        }
    except Exception:
        return {"ratio": 0, "valid": False, "stop": None, "target": None}


def _generate_summary(ticker, price, rsi, macd_bullish, trend_4w, above_200,
                      above_50, uptrend_52w, near_support, rs, patterns,
                      vol_spike, bb_pct, rr) -> str:
    """Generate a short plain-language summary of why this stock was selected."""
    reasons = []

    if uptrend_52w:
        reasons.append("במגמת עלייה מוכחת של 52 שבועות")
    if rsi < 30:
        reasons.append(f"RSI {rsi} — מכירת יתר קיצונית, הזדמנות כניסה מצוינת")
    elif rsi < 40:
        reasons.append(f"RSI {rsi} — oversold בתוך מגמה חיובית")
    if macd_bullish:
        reasons.append("MACD היסטוגרמה חיובית — מומנטום עולה")
    if near_support:
        reasons.append("מחיר קרוב לרמת תמיכה חזקה — כניסה בסיכון נמוך")
    if bb_pct < 0.2:
        reasons.append("מחיר נמצא ברצועת בולינגר התחתונה — פוטנציאל קפיצה")
    if rs > 1.2:
        reasons.append(f"חוזק יחסי {rs} — מנצחת את ה-S&P500")
    if vol_spike:
        reasons.append("⚡ ווליום חריג — כסף מוסדי כנראה נכנס")
    if patterns:
        reasons.append(f"תבנית גרף: {', '.join(patterns)}")
    if rr.get('valid'):
        reasons.append(f"יחס סיכוי:סיכון = 1:{rr['ratio']} ✓ (יעד ${rr['target']}, סטופ ${rr['stop']})")
    if above_200 and above_50:
        reasons.append("מחיר מעל MA200 ו-MA50 — מבנה עולה תקין")

    if not reasons:
        reasons.append("עוברת את כל פרמטרי מרפי הבסיסיים")

    return " | ".join(reasons[:5])  # max 5 reasons for readability


# ──────────────────────────────────────────────────────────────
#  DEBUG
# ──────────────────────────────────────────────────────────────
def debug_ticker(ticker: str, params: dict) -> str:
    try:
        df = _get_ohlcv(ticker, period="2y")
        if df.empty or len(df) < 50:
            return f"{ticker}: ❌ No data ({len(df)} rows)"
        close = df['Close']
        price = round(float(close.iloc[-1]), 2)
        if price < params.get('min_price', 15):
            return f"{ticker}: ❌ Price ${price} < min"
        avg_vol = float(df['Volume'].rolling(20).mean().iloc[-1])
        if avg_vol < params.get('min_volume', 200_000):
            return f"{ticker}: ❌ Volume {avg_vol:,.0f} too low"
        ma50  = float(close.rolling(50).mean().iloc[-1])  if len(close)>=50  else None
        ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close)>=200 else None
        if params.get('require_above_200') and (not ma200 or price < ma200):
            return f"{ticker}: ❌ Below MA200 (${price} vs ${round(ma200,2) if ma200 else 'N/A'})"
        if params.get('require_above_50') and (not ma50 or price < ma50*0.97):
            return f"{ticker}: ❌ Below MA50"
        rsi = _rsi(close, params.get('rsi_period',14))
        rsi_min, rsi_max = params.get('rsi_min',0), params.get('rsi_max',90)
        if rsi > rsi_max or rsi < rsi_min:
            return f"{ticker}: ❌ RSI={rsi} not in [{rsi_min}–{rsi_max}]"
        uptrend = _uptrend_52w(close)
        if params.get('require_uptrend_52w') and not uptrend:
            return f"{ticker}: ❌ Not in 52-week uptrend"
        trend = _trend_pct(close, 20)
        return (f"{ticker}: ✅ PASSES — Price=${price}, RSI={rsi}, "
                f"52W-Uptrend={'✓' if uptrend else '✗'}, Trend4W={trend}%")
    except Exception as e:
        return f"{ticker}: ❌ Exception: {e}"


# ──────────────────────────────────────────────────────────────
#  MAIN SCREENER
# ──────────────────────────────────────────────────────────────
_SPY_CACHE = {}   # module-level cache to avoid downloading SPY per stock


def _get_spy() -> pd.Series:
    global _SPY_CACHE
    now_key = datetime.today().strftime('%Y-%m-%d')
    if now_key in _SPY_CACHE:
        return _SPY_CACHE[now_key]
    spy_df = _get_ohlcv("SPY", period="1y")
    if spy_df.empty:
        return pd.Series(dtype=float)
    s = spy_df['Close']
    _SPY_CACHE = {now_key: s}
    return s


def calculate_indicators(ticker: str, params: dict):
    try:
        df = _get_ohlcv(ticker, period="2y")   # 2 years for 52w uptrend check
        if df.empty or len(df) < 60:
            return None

        close  = df['Close']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series(dtype=float)
        price  = round(float(close.iloc[-1]), 2)

        # ── Filters ──────────────────────────────────────────────────

        if price < params.get('min_price', 15):
            return None

        avg_vol    = float(volume.rolling(20).mean().iloc[-1]) if not volume.empty else 0
        avg_vol_50 = float(volume.rolling(50).mean().iloc[-1]) if not volume.empty else 0
        if np.isnan(avg_vol) or avg_vol < params.get('min_volume', 200_000):
            return None

        ma20  = round(float(close.rolling(20).mean().iloc[-1]),2)  if len(close)>=20  else None
        ma50  = round(float(close.rolling(50).mean().iloc[-1]),2)  if len(close)>=50  else None
        ma200 = round(float(close.rolling(200).mean().iloc[-1]),2) if len(close)>=200 else None

        def ok(v): return v is not None and not np.isnan(v)

        above_200 = ok(ma200) and price > ma200
        above_50  = ok(ma50)  and price > ma50
        above_20  = ok(ma20)  and price > ma20
        near_50   = ok(ma50)  and price >= ma50 * 0.97

        if params.get('require_above_200') and not above_200:
            return None
        if params.get('require_above_50') and not (above_50 or near_50):
            return None
        if params.get('require_above_20') and not above_20:
            return None

        rsi_period  = params.get('rsi_period', 14)
        rsi_max     = params.get('rsi_max', 90)
        rsi_min     = params.get('rsi_min', 0)
        current_rsi = _rsi(close, rsi_period)
        if current_rsi > rsi_max or current_rsi < rsi_min:
            return None

        # 52-week uptrend filter
        uptrend_52w = _uptrend_52w(close)
        if params.get('require_uptrend_52w', True) and not uptrend_52w:
            return None

        trend_4w = _trend_pct(close, 20)
        if trend_4w < -15.0:
            return None

        # ── Calculated Metrics (no filter) ───────────────────────────

        bb_pct, bb_upper_v, bb_lower_v = _bb(
            close, params.get('bb_period',20), params.get('bb_std',2.0))

        macd_line, macd_signal, macd_hist = _macd(close)
        macd_bullish = macd_hist > 0

        spy_close = _get_spy()
        beta = _beta(close, spy_close)

        min_beta = params.get('min_beta', 0.5)
        if min_beta > 0 and beta < min_beta:
            return None

        rs = _relative_strength(close, spy_close)
        vol_ratio, vol_spike = _volume_spike(volume)
        support, resistance, near_support = _support_resistance(df)
        fib = _fibonacci_levels(close)
        patterns = _chart_patterns(df)
        rr  = _risk_reward(price, support, resistance)

        # Institutional (only if requested)
        inst_pct = None
        min_inst = params.get('min_institutional', 0)
        if min_inst > 0:
            try:
                info = yf.Ticker(ticker).info
                raw  = info.get('heldPercentInstitutions')
                if raw is not None:
                    inst_pct = round(float(raw)*100, 1)
                    if inst_pct < min_inst:
                        return None
            except Exception:
                pass

        # Signal freshness
        signal_is_fresh = True
        try:
            g = close.diff().clip(lower=0).ewm(com=rsi_period-1, min_periods=rsi_period).mean()
            l = (-close.diff().clip(upper=0)).ewm(com=rsi_period-1, min_periods=rsi_period).mean()
            rsi_ser = 100 - (100/(1+g/l))
            if len(rsi_ser) > 5:
                prev = float(rsi_ser.iloc[-5])
                signal_is_fresh = (not np.isnan(prev)) and prev > rsi_max
        except Exception:
            signal_is_fresh = True

        # ── Score ─────────────────────────────────────────────────────
        score = 0.0

        # RSI
        if   current_rsi < 20: score += 4.0
        elif current_rsi < 25: score += 3.0
        elif current_rsi < 30: score += 2.5
        elif current_rsi < 35: score += 2.0
        elif current_rsi < 40: score += 1.5
        elif current_rsi < 50: score += 1.0
        else:                  score += 0.5

        # BB
        if   bb_pct < 0.05: score += 3.0
        elif bb_pct < 0.10: score += 2.5
        elif bb_pct < 0.20: score += 2.0
        elif bb_pct < 0.35: score += 1.5
        elif bb_pct < 0.50: score += 0.5

        # Trend
        if   trend_4w >  5: score += 1.5
        elif trend_4w >  0: score += 1.0
        elif trend_4w > -5: score += 0.3

        # MA
        if above_200:   score += 0.5
        if above_50:    score += 0.5
        if above_20:    score += 0.3
        if uptrend_52w: score += 1.0   # big bonus for true 52w uptrend

        # MACD
        if macd_bullish: score += 0.5

        # Volume spike
        if vol_spike:    score += 0.7
        elif vol_ratio > 1.5: score += 0.3

        # Relative strength
        if   rs > 1.5: score += 1.0
        elif rs > 1.0: score += 0.5

        # Near support
        if near_support: score += 0.5

        # Chart patterns
        if patterns:     score += 0.5

        # Good R/R ratio
        if rr.get('valid'): score += 0.5

        # Fresh signal
        if signal_is_fresh: score += 0.5

        # Institutional
        if inst_pct:
            if   inst_pct >= 60: score += 1.0
            elif inst_pct >= 40: score += 0.7
            elif inst_pct >= 30: score += 0.5

        score = round(min(10.0, score), 1)

        # ── Name ──────────────────────────────────────────────────────
        name = ticker
        try:
            fi   = yf.Ticker(ticker).fast_info
            name = getattr(fi, 'company_name', None) or ticker
        except Exception:
            pass

        # ── AI Summary ────────────────────────────────────────────────
        summary = _generate_summary(
            ticker, price, current_rsi, macd_bullish, trend_4w,
            above_200, above_50, uptrend_52w, near_support, rs,
            patterns, vol_spike, bb_pct, rr)

        return {
            "ticker":           ticker,
            "name":             name,
            "price":            price,
            "rsi":              current_rsi,
            "ma20":             ma20,
            "ma50":             ma50,
            "ma200":            ma200,
            "above_200":        above_200,
            "above_50":         above_50,
            "above_20":         above_20,
            "near_50":          near_50,
            "bb_pct":           bb_pct,
            "bb_upper":         bb_upper_v,
            "bb_lower":         bb_lower_v,
            "trend_4w":         trend_4w,
            "uptrend_52w":      uptrend_52w,
            "beta":             beta,
            "rs":               rs,
            "avg_volume":       round(avg_vol, 0),
            "volume_ratio":     round(vol_ratio, 2),
            "volume_spike":     vol_spike,
            "macd_line":        macd_line,
            "macd_signal":      macd_signal,
            "macd_hist":        macd_hist,
            "macd_bullish":     macd_bullish,
            "support":          support,
            "resistance":       resistance,
            "near_support":     near_support,
            "fib":              fib,
            "patterns":         patterns,
            "rr_ratio":         rr.get("ratio", 0),
            "rr_valid":         rr.get("valid", False),
            "rr_stop":          rr.get("stop"),
            "rr_target":        rr.get("target"),
            "institutional_pct":inst_pct,
            "signal_fresh":     signal_is_fresh,
            "signal_date":      datetime.today().strftime('%Y-%m-%d'),
            "summary":          summary,
            "score":            score,
            "passes_filter":    True,
        }

    except Exception:
        return None

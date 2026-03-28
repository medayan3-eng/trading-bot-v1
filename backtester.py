"""
Backtester — simulates Murphy-style swing trades on scanned stocks.

Buy signal  : RSI crosses below rsi_max AND price above MA200 AND price above MA50*0.97
Sell signal : RSI crosses above 60 OR price drops below MA50*0.95 OR BB%B > 0.85
Re-entry    : allowed after 2-bar cooldown
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed


# ── Indicators ────────────────────────────────────────────────
def _rsi(s: pd.Series, period: int = 14) -> pd.Series:
    delta    = s.diff()
    avg_gain = delta.clip(lower=0).ewm(com=period-1, min_periods=period).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(com=period-1, min_periods=period).mean()
    rs       = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def _bb_pct(s: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.Series:
    mid   = s.rolling(period).mean()
    sigma = s.rolling(period).std()
    upper = mid + std_dev * sigma
    lower = mid - std_dev * sigma
    return (s - lower) / (upper - lower)


def _get_data(ticker: str) -> pd.DataFrame:
    """Download 2 years of data using Ticker.history (reliable, no MultiIndex)."""
    try:
        t  = yf.Ticker(ticker)
        df = t.history(period="2y", interval="1d", auto_adjust=True, actions=False)
        if df is None or df.empty or 'Close' not in df.columns:
            return pd.DataFrame()
        return df[['Close','High','Low','Volume']].dropna(subset=['Close']).copy()
    except Exception:
        return pd.DataFrame()


# ── Single ticker backtest ────────────────────────────────────
def _backtest_one(ticker: str, params: dict) -> dict:
    try:
        df = _get_data(ticker)
        if df.empty or len(df) < 80:
            return {}

        close = df['Close']

        # Parameters — use what the user set, with sensible defaults
        rsi_period = params.get('rsi_period', 14)
        rsi_max    = params.get('rsi_max', 50)      # use user's RSI max
        rsi_min    = params.get('rsi_min', 0)
        bb_period  = params.get('bb_period', 20)
        bb_std     = params.get('bb_std', 2.0)

        rsi_s  = _rsi(close, rsi_period)
        bb_s   = _bb_pct(close, bb_period, bb_std)
        ma50   = close.rolling(50).mean()
        ma200  = close.rolling(200).mean()

        # ── Buy signal: RSI in oversold zone + above MAs ──────────
        # Relaxed: no BB requirement (it's informational)
        buy_sig = (
            (rsi_s < rsi_max) &
            (rsi_s > rsi_min) &
            (close > ma200 * 0.97) &    # within 3% of MA200
            (close > ma50  * 0.95)      # within 5% of MA50
        )

        # ── Sell signal: overbought OR breaks below MA ─────────────
        sell_sig = (
            (rsi_s > 65) |
            (close < ma50 * 0.93) |
            (bb_s  > 0.90)
        )

        # Only backtest last 12 months
        cutoff = pd.Timestamp(datetime.today() - timedelta(days=365))
        idx    = close.index[close.index >= cutoff].tolist()

        if len(idx) < 20:
            return {}

        # ── Simulate trades ───────────────────────────────────────
        trades        = []
        in_trade      = False
        buy_price     = None
        buy_date      = None
        cooldown      = 0

        for date in idx:
            if cooldown > 0:
                cooldown -= 1
                continue

            price    = float(close.loc[date])
            is_buy   = bool(buy_sig.loc[date])  if date in buy_sig.index  else False
            is_sell  = bool(sell_sig.loc[date]) if date in sell_sig.index else False

            if not in_trade:
                if is_buy:
                    in_trade  = True
                    buy_price = price
                    buy_date  = date
            else:
                if is_sell:
                    pct    = (price - buy_price) / buy_price * 100
                    hold_d = (date - buy_date).days
                    won    = pct > 0
                    trades.append({
                        "ticker":     ticker,
                        "buy_date":   buy_date.strftime('%Y-%m-%d'),
                        "sell_date":  date.strftime('%Y-%m-%d'),
                        "buy_price":  round(float(buy_price), 2),
                        "sell_price": round(float(price), 2),
                        "return_%":   round(pct, 2),
                        "hold_days":  hold_d,
                        "result":     "✅ Win" if won else "❌ Loss",
                        "rsi_at_buy": round(float(rsi_s.loc[buy_date]), 1)
                                      if buy_date in rsi_s.index else None,
                    })
                    in_trade  = False
                    buy_price = None
                    cooldown  = 2 if not won else 0   # short cooldown after loss

        # Open trade at end
        if in_trade and buy_price is not None:
            last_price = float(close.iloc[-1])
            pct        = (last_price - buy_price) / buy_price * 100
            trades.append({
                "ticker":     ticker,
                "buy_date":   buy_date.strftime('%Y-%m-%d'),
                "sell_date":  "OPEN",
                "buy_price":  round(float(buy_price), 2),
                "sell_price": round(float(last_price), 2),
                "return_%":   round(pct, 2),
                "hold_days":  (close.index[-1] - buy_date).days,
                "result":     "🔵 Open",
                "rsi_at_buy": None,
            })

        if not trades:
            return {}

        # ── Stats ─────────────────────────────────────────────────
        closed  = [t for t in trades if t['sell_date'] != "OPEN"]
        all_r   = [t['return_%'] for t in trades]
        wins    = [t for t in closed if t['return_%'] > 0]
        win_r   = len(wins) / len(closed) * 100 if closed else 0

        return {
            "ticker":       ticker,
            "trades":       trades,
            "total_trades": len(trades),
            "wins":         len(wins),
            "losses":       len(closed) - len(wins),
            "win_rate":     round(win_r, 1),
            "avg_return":   round(float(np.mean(all_r)), 2),
            "best_trade":   round(float(max(all_r)), 2),
            "worst_trade":  round(float(min(all_r)), 2),
            "avg_hold_days":round(float(np.mean([t['hold_days'] for t in trades])), 1),
        }

    except Exception:
        return {}


# ── Public entry point ────────────────────────────────────────
def run_backtest_on_screened(tickers: list, params: dict,
                              progress_bar=None, status_text=None) -> dict:
    """
    Run backtest on screened stocks.
    Returns {overall, per_stock, trade_log}
    """
    per_stock = {}
    trade_log = []
    done      = 0
    total     = len(tickers)

    # Sequential to avoid yfinance cache issues
    for ticker in tickers:
        done += 1
        if progress_bar:
            progress_bar.progress(done / total)
        if status_text:
            status_text.caption(f"Backtesting {ticker}… ({done}/{total})")

        res = _backtest_one(ticker, params)
        if res and res.get('total_trades', 0) > 0:
            per_stock[ticker] = {
                k: res[k] for k in
                ['total_trades','wins','losses','win_rate',
                 'avg_return','best_trade','worst_trade','avg_hold_days']
            }
            trade_log.extend(res.get('trades', []))

    if not trade_log:
        return {
            "overall":   {"total_trades":0,"wins":0,"losses":0,
                          "win_rate":0,"avg_return":0,"best_trade":0,"worst_trade":0},
            "per_stock": {},
            "trade_log": [],
            "note":      "No trades found. Try widening RSI range or unchecking MA filters."
        }

    all_r     = [t['return_%'] for t in trade_log]
    closed    = [t for t in trade_log if t['sell_date'] != "OPEN"]
    wins_all  = [t for t in closed if t['return_%'] > 0]
    wr_all    = len(wins_all) / len(closed) * 100 if closed else 0

    overall = {
        "total_trades":   len(trade_log),
        "wins":           len(wins_all),
        "losses":         len(closed) - len(wins_all),
        "win_rate":       round(wr_all, 1),
        "avg_return":     round(float(np.mean(all_r)), 2),
        "best_trade":     round(float(max(all_r)), 2),
        "worst_trade":    round(float(min(all_r)), 2),
        "tickers_tested": len(per_stock),
    }

    trade_log.sort(key=lambda x: x['buy_date'], reverse=True)

    return {
        "overall":   overall,
        "per_stock": per_stock,
        "trade_log": trade_log,
    }

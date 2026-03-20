"""
Backtester — runs ONLY on stocks that passed the live screener (Step 1).

Logic:
- Downloads 1 full year of daily data per ticker
- Simulates every possible buy/sell signal using the same Murphy criteria
- A new buy can trigger again after each completed sell (multiple round-trips)
- To maximise trade count we use a "re-entry allowed after cooldown" approach:
    * Buy  signal: RSI < rsi_max  AND  BB%B < 0.35  AND  price > MA200  AND  price > MA50*0.98
    * Sell signal: RSI > 60  OR  BB%B > 0.8  OR  price < MA50 * 0.97
- Per-stock stats: win_rate, avg_return, best/worst trade, avg hold days
- Overall aggregate across all scanned tickers
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed


# ─── indicator helpers ─────────────────────────────────────────────────────

def _rsi(s, period):
    d   = s.diff()
    g   = d.clip(lower=0).rolling(period).mean()
    l   = (-d.clip(upper=0)).rolling(period).mean()
    return 100 - 100 / (1 + g / l)


def _bb_pct(s, period, std_dev):
    mid   = s.rolling(period).mean()
    sigma = s.rolling(period).std()
    lower = mid - std_dev * sigma
    upper = mid + std_dev * sigma
    return (s - lower) / (upper - lower)


# ─── single ticker backtest ─────────────────────────────────────────────────

def _backtest_one(ticker: str, params: dict) -> dict:
    """
    Run a full year of simulated trades on one ticker.
    Returns per-stock stats + list of individual trade records.
    """
    try:
        end   = datetime.today()
        start = end - timedelta(days=400)  # extra buffer for warmup

        df = yf.download(ticker, start=start, end=end,
                         interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 60:
            return {}

        close  = df['Close'].squeeze()
        rsi_p  = params.get('rsi_period', 14)
        rsi_th = params.get('rsi_max', 40)
        bb_p   = params.get('bb_period', 20)
        bb_std = params.get('bb_std', 2.0)

        rsi    = _rsi(close, rsi_p)
        bb     = _bb_pct(close, bb_p, bb_std)
        ma50   = close.rolling(50).mean()
        ma200  = close.rolling(200).mean()

        # Build signal arrays (aligned)
        buy_sig  = (rsi < rsi_th) & (bb < 0.35) & (close > ma200) & (close > ma50 * 0.98)
        sell_sig = (rsi > 60) | (bb > 0.8) | (close < ma50 * 0.97)

        # Only trade within last 365 days
        cutoff  = pd.Timestamp(end - timedelta(days=365))
        close_r = close[close.index >= cutoff]
        buy_r   = buy_sig[buy_sig.index >= cutoff]
        sell_r  = sell_sig[sell_sig.index >= cutoff]

        # ── Simulate all trades ──────────────────────────────────────────
        trades        = []
        in_trade      = False
        buy_price     = None
        buy_date      = None
        buy_rsi       = None
        cooldown_left = 0          # bars to wait before re-entry after a loss

        idx = close_r.index.tolist()

        for i, date in enumerate(idx):
            if cooldown_left > 0:
                cooldown_left -= 1
                continue

            price     = float(close_r.loc[date])
            is_buy    = bool(buy_r.loc[date])  if date in buy_r.index  else False
            is_sell   = bool(sell_r.loc[date]) if date in sell_r.index else False

            if not in_trade:
                if is_buy:
                    in_trade   = True
                    buy_price  = price
                    buy_date   = date
                    buy_rsi    = float(rsi.loc[date]) if date in rsi.index else None

            else:  # in trade
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
                        "rsi_at_buy": round(float(buy_rsi), 1) if buy_rsi else None,
                    })

                    in_trade  = False
                    buy_price = None
                    # Short cooldown after a loss to avoid whipsaws
                    if not won:
                        cooldown_left = 3

        # If still open at year-end, mark as open trade
        if in_trade and buy_price is not None:
            last_price = float(close_r.iloc[-1])
            pct        = (last_price - buy_price) / buy_price * 100
            hold_d     = (close_r.index[-1] - buy_date).days
            trades.append({
                "ticker":     ticker,
                "buy_date":   buy_date.strftime('%Y-%m-%d'),
                "sell_date":  "OPEN",
                "buy_price":  round(float(buy_price), 2),
                "sell_price": round(float(last_price), 2),
                "return_%":   round(pct, 2),
                "hold_days":  hold_d,
                "result":     "🔵 Open",
                "rsi_at_buy": round(float(buy_rsi), 1) if buy_rsi else None,
            })

        if not trades:
            return {}

        # ── Per-stock stats ─────────────────────────────────────────────
        closed = [t for t in trades if t['sell_date'] != "OPEN"]
        all_r  = [t['return_%'] for t in trades]
        wins   = [t for t in closed if t['return_%'] > 0]
        losses = [t for t in closed if t['return_%'] <= 0]
        win_r  = len(wins) / len(closed) * 100 if closed else 0
        holds  = [t['hold_days'] for t in trades]

        return {
            "ticker":      ticker,
            "trades":      trades,
            "total_trades": len(trades),
            "wins":        len(wins),
            "losses":      len(losses),
            "win_rate":    round(win_r, 1),
            "avg_return":  round(float(np.mean(all_r)), 2),
            "best_trade":  round(float(max(all_r)), 2),
            "worst_trade": round(float(min(all_r)), 2),
            "avg_hold_days": round(float(np.mean(holds)), 1),
        }

    except Exception as e:
        return {}


# ─── public entry point ─────────────────────────────────────────────────────

def run_backtest_on_screened(tickers: list, params: dict,
                              progress_bar=None, status_text=None) -> dict:
    """
    Run backtest on every ticker in `tickers` (the Step-1 scan results).
    Returns a dict with:
      - overall:   aggregate stats
      - per_stock: dict ticker -> stats
      - trade_log: flat list of all trades
    """
    per_stock  = {}
    trade_log  = []
    done       = 0
    total      = len(tickers)

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_backtest_one, t, params): t for t in tickers}
        for fut in as_completed(futures):
            done += 1
            if progress_bar:
                progress_bar.progress(done / total)
            if status_text:
                status_text.caption(f"Backtesting {done}/{total}…")
            res = fut.result()
            if res and res.get('total_trades', 0) > 0:
                ticker = res['ticker']
                per_stock[ticker] = {
                    k: res[k] for k in
                    ['total_trades','wins','losses','win_rate',
                     'avg_return','best_trade','worst_trade','avg_hold_days']
                }
                trade_log.extend(res.get('trades', []))

    # ── Overall aggregate ────────────────────────────────────────────────
    if not trade_log:
        return {"overall": {}, "per_stock": {}, "trade_log": []}

    all_returns = [t['return_%'] for t in trade_log]
    closed      = [t for t in trade_log if t['sell_date'] != "OPEN"]
    wins_all    = [t for t in closed if t['return_%'] > 0]
    wr_all      = len(wins_all) / len(closed) * 100 if closed else 0

    overall = {
        "total_trades": len(trade_log),
        "wins":         len(wins_all),
        "losses":       len(closed) - len(wins_all),
        "win_rate":     round(wr_all, 1),
        "avg_return":   round(float(np.mean(all_returns)), 2),
        "best_trade":   round(float(max(all_returns)), 2),
        "worst_trade":  round(float(min(all_returns)), 2),
        "tickers_tested": len(per_stock),
    }

    # Sort trade log newest first
    trade_log.sort(key=lambda x: x['buy_date'], reverse=True)

    return {"overall": overall, "per_stock": per_stock, "trade_log": trade_log}

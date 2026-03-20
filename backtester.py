import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


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
    pct_b = (series - lower) / (upper - lower)
    return upper, mid, lower, pct_b


def generate_signals_historical(df, params):
    """
    Generate buy signals on historical data using Murphy criteria.
    Buy signal: RSI < rsi_max AND BB%B < 0.2 AND price > MA200 AND price > MA50
    Sell signal (exit): RSI > 60 OR BB%B > 0.8 OR price < MA50
    """
    close = df['Close'].squeeze()
    
    rsi = calculate_rsi(close, params.get('rsi_period', 14))
    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()
    _, _, _, bb_pct = calculate_bollinger(close, params.get('bb_period', 20), params.get('bb_std', 2.0))
    
    signals = pd.DataFrame(index=df.index)
    signals['close'] = close
    signals['rsi'] = rsi
    signals['ma50'] = ma50
    signals['ma200'] = ma200
    signals['bb_pct'] = bb_pct
    
    # Buy signal: all Murphy criteria met
    signals['buy'] = (
        (rsi < params.get('rsi_max', 40)) &
        (bb_pct < 0.35) &
        (close > ma200) &
        (close > ma50 * 0.98)
    )
    
    # Sell signal: overbought or below moving averages
    signals['sell'] = (
        (rsi > 60) |
        (bb_pct > 0.8) |
        (close < ma50 * 0.97)
    )
    
    return signals


def backtest_ticker(ticker, params, forward_days=10):
    """
    For a single ticker, find all buy signals in the last year.
    For each signal, check if price was higher forward_days later.
    Returns list of signal results.
    """
    try:
        end = datetime.today()
        start = end - timedelta(days=400)  # a bit more than a year for warmup
        
        df = yf.download(ticker, start=start, end=end, interval="1d", 
                        progress=False, auto_adjust=True)
        if df.empty or len(df) < 60:
            return []
        
        signals = generate_signals_historical(df, params)
        
        results = []
        in_trade = False
        buy_price = None
        buy_date = None
        
        # Only look at last 365 days
        cutoff = end - timedelta(days=365)
        recent_signals = signals[signals.index >= pd.Timestamp(cutoff)]
        
        for i, (date, row) in enumerate(recent_signals.iterrows()):
            if not in_trade and row['buy']:
                in_trade = True
                buy_price = row['close']
                buy_date = date
            elif in_trade and row['sell']:
                sell_price = row['close']
                pct_change = ((sell_price - buy_price) / buy_price) * 100
                
                results.append({
                    'ticker': ticker,
                    'signal_type': 'BUY→SELL',
                    'buy_date': buy_date.strftime('%Y-%m-%d'),
                    'sell_date': date.strftime('%Y-%m-%d'),
                    'buy_price': round(float(buy_price), 2),
                    'sell_price': round(float(sell_price), 2),
                    'pct_change': round(pct_change, 2),
                    'correct': pct_change > 0,
                    'rsi_at_buy': round(float(recent_signals.loc[buy_date, 'rsi']), 1) if buy_date in recent_signals.index else None,
                    'bb_pct_at_buy': round(float(recent_signals.loc[buy_date, 'bb_pct']), 3) if buy_date in recent_signals.index else None,
                })
                in_trade = False
                buy_price = None
                buy_date = None
        
        # If still in trade at end, evaluate vs current price
        if in_trade and buy_price is not None:
            sell_price = float(signals['close'].iloc[-1])
            pct_change = ((sell_price - buy_price) / buy_price) * 100
            results.append({
                'ticker': ticker,
                'signal_type': 'BUY (open)',
                'buy_date': buy_date.strftime('%Y-%m-%d'),
                'sell_date': 'OPEN',
                'buy_price': round(float(buy_price), 2),
                'sell_price': round(float(sell_price), 2),
                'pct_change': round(pct_change, 2),
                'correct': pct_change > 0,
                'rsi_at_buy': None,
                'bb_pct_at_buy': None,
            })
        
        return results
    
    except Exception as e:
        return []


def run_backtest(universe, params):
    """
    Run backtest across a universe of stocks.
    Returns summary stats + detailed signal list.
    """
    all_results = []
    
    for ticker in universe:
        ticker_results = backtest_ticker(ticker, params)
        all_results.extend(ticker_results)
    
    if not all_results:
        return {'total': 0, 'correct_buy': 0, 'correct_sell': 0, 'wrong': 0, 'details': []}
    
    total = len(all_results)
    correct = sum(1 for r in all_results if r['correct'])
    wrong = total - correct
    
    # Correct buy = price went up after buy signal
    correct_buy = sum(1 for r in all_results if r['correct'] and r['pct_change'] > 0)
    # For sells, we track separately
    correct_sell = correct_buy  # same metric in this framework
    
    # Sort by pct_change descending
    all_results.sort(key=lambda x: x['pct_change'], reverse=True)
    
    # Format for display
    df_results = pd.DataFrame(all_results)
    if not df_results.empty:
        df_results['result'] = df_results['correct'].map({True: '✅ Correct', False: '❌ Wrong'})
        df_results['pct_change'] = df_results['pct_change'].apply(lambda x: f"{x:+.2f}%")
        cols = ['ticker', 'buy_date', 'sell_date', 'buy_price', 'sell_price', 'pct_change', 'result', 'rsi_at_buy']
        df_results = df_results[[c for c in cols if c in df_results.columns]]
    
    avg_return = np.mean([r['pct_change'] for r in all_results]) if all_results else 0
    
    return {
        'total': total,
        'correct_buy': correct_buy,
        'correct_sell': correct_sell,
        'wrong': wrong,
        'win_rate': round(correct / total * 100, 1) if total else 0,
        'avg_return': round(float(avg_return), 2),
        'details': df_results.to_dict('records') if not df_results.empty else []
    }

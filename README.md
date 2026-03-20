# 📈 Murphy Stock Scanner

A Streamlit-based stock screener using John Murphy's technical analysis principles, focused on catching **oversold opportunities in uptrends**.

## Strategy Logic (Murphy Method)

| Criterion | Rule |
|-----------|------|
| **Price** | > $15, above MA200 + MA50 |
| **Volume** | Average volume > threshold |
| **Beta** | ≥ 1.0 (higher volatility = more opportunity) |
| **RSI(14)** | < 40 → looking for oversold in uptrend |
| **Bollinger Band %B** | < 0.35 → price near lower band |
| **4-Week Trend** | Positive → general uptrend confirmed |
| **MA Alignment** | Price > MA200 > MA50 ideal |

## Scoring (0–10)
- RSI depth (oversold level)
- BB position (near lower band)
- Trend strength (4-week)
- MA alignment
- Volume surge

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run app.py
```

## Deploying to Streamlit Cloud

1. Push this folder to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo → select `app.py`
4. Deploy!

## Backtest

The backtest module tests signal accuracy over the **last 12 months**:
- **Buy signal**: RSI < threshold + price near BB lower + in uptrend
- **Sell signal**: RSI > 60 OR price breaks below MA50
- Tracks: correct buys, correct sells, wrong calls, win rate

## Project Structure

```
stock_scanner/
├── app.py              # Main Streamlit app
├── screener.py         # Indicator calculations + filtering
├── backtester.py       # 1-year historical signal testing
├── news_fetcher.py     # News via yfinance
├── stock_universe.py   # ~500 stock universe
├── requirements.txt
└── README.md
```

## Notes
- Scans are multi-threaded (10 workers) for speed
- Beta is estimated vs SPY over 6 months
- News is pulled live from Yahoo Finance
- All data via yfinance (free, no API key needed)

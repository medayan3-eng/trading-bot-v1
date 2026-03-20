import yfinance as yf
from datetime import datetime


def fetch_news(ticker: str) -> list:
    """
    Fetch recent news for a ticker using yfinance.
    Returns list of news items with title, url, publisher, published.
    """
    try:
        t = yf.Ticker(ticker)
        news = t.news
        
        if not news:
            return []
        
        result = []
        for item in news[:10]:
            # Handle different yfinance news formats
            title = item.get('title', '') or item.get('content', {}).get('title', '')
            url = item.get('link', '') or item.get('url', '') or item.get('content', {}).get('url', '')
            publisher = item.get('publisher', '') or item.get('source', {}).get('displayName', '')
            
            # Convert timestamp
            pub_time = item.get('providerPublishTime') or item.get('pubDate', '')
            if isinstance(pub_time, int):
                try:
                    pub_str = datetime.fromtimestamp(pub_time).strftime('%b %d, %Y %H:%M')
                except:
                    pub_str = str(pub_time)
            else:
                pub_str = str(pub_time)[:16] if pub_time else ''
            
            if title:
                result.append({
                    'title': title,
                    'url': url,
                    'publisher': publisher,
                    'published': pub_str
                })
        
        return result
    
    except Exception as e:
        return []

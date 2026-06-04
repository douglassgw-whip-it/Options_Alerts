import pandas as pd
import yfinance as yf


def fetch_stock_data(ticker, period="1y"):
    """Fetches historical daily data for a given stock ticker."""
    try:
        stock = yf.Ticker(ticker)
        # Fetch data and ensure column headers are clean strings
        df = stock.history(period=period)
        if df.empty:
            return None
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None


def calculate_indicators(df):
    """Calculates 50-day MA, 200-day MA, and 14-day RSI."""
    # 1. Moving Averages
    df["MA50"] = df["Close"].rolling(window=50).mean()
    df["MA200"] = df["Close"].rolling(window=200).mean()

    # 2. Relative Strength Index (RSI)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)

    ema_gain = gain.ewm(com=13, adjust=False).mean()
    ema_loss = loss.ewm(com=13, adjust=False).mean()

    # Avoid division by zero
    rs = ema_gain / ema_loss.replace(0, 0.00001)
    df["RSI"] = 100 - (100 / (1 + rs))

    return df


def generate_signal(df):
    """Evaluates the most recent data point to generate a Buy, Sell, or Hold signal."""
    if len(df) < 200:
        return "Insufficient Data (Needs 200+ days)"

    # Get the latest row of data
    latest = df.iloc[-1]

    current_price = latest["Close"]
    ma50 = latest["MA50"]
    ma200 = latest["MA200"]
    rsi = latest["RSI"]

    # --- STRATEGY LOGIC ---
    # BUY: Price is above both MAs, 50MA is above 200MA (Uptrend), and RSI is not overbought (< 65)
    if current_price > ma50 and ma50 > ma200 and rsi < 65:
        return "BUY (Strong Uptrend)"

    # SELL: Price drops below the 50-day MA, or RSI shows extreme overbought conditions (> 80)
    elif current_price < ma50 or rsi > 80:
        return "SELL / TAKE PROFIT"

    else:
        return "HOLD / NEUTRAL"


def run_screener(ticker_list):
    """Scans all tickers in the list and prints out recommendations."""
    print("\n--- Running Stock Screener ---")
    results = []

    for ticker in ticker_list:
        print(f"Analyzing {ticker}...")
        df = fetch_stock_data(ticker)

        if df is not None:
            df = calculate_indicators(df)
            signal = generate_signal(df)

            # Pull the last known closing price
            last_price = df.iloc[-1]["Close"]
            last_rsi = df.iloc[-1]["RSI"]

            results.append(
                {
                    "Ticker": ticker,
                    "Price": round(last_price, 2),
                    "RSI": round(last_rsi, 1),
                    "Signal": signal,
                }
            )

    # Convert results into a clean table
    results_df = pd.DataFrame(results)
    print("\n=== FINAL SCREENER REPORT ===")
    print(results_df.to_string(index=False))


# --- RUN THE SCREENER ---
if __name__ == "__main__":
    # Add whatever stock tickers you want to scan here
    watchlist = ["AAPL", "MSFT", "NVDA", "AVGO", "AMZN", "TSLA"]
    run_screener(watchlist)

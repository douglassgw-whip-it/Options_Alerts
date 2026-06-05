import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import yfinance as yf

# Email Configuration
SENDER_EMAIL = "douglassgw@gmail.com"
RECIPIENT_EMAIL = "douglassgw@gmail.com"
APP_PASSWORD = os.environ.get("EMAIL_PASS")


def fetch_stock_data(ticker, period="1y"):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            return None
        return df
    except Exception:
        return None


def calculate_indicators(df):
    # 1. Moving Averages
    df["MA50"] = df["Close"].rolling(window=50).mean()
    df["MA200"] = df["Close"].rolling(window=200).mean()

    # 2. RSI Calculation
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    ema_gain = gain.ewm(com=13, adjust=False).mean()
    ema_loss = loss.ewm(com=13, adjust=False).mean()
    rs = ema_gain / ema_loss.replace(0, 0.00001)
    df["RSI"] = 100 - (100 / (1 + rs))

    # 3. Trailing Peak (Highest closing price of the last 20 trading days)
    df["Recent_Peak"] = df["Close"].rolling(window=20).max()

    return df


def generate_signal(df):
    if len(df) < 200:
        return "Insufficient Data", "#888888"

    latest = df.iloc[-1]
    current_price = latest["Close"]
    ma50 = latest["MA50"]
    ma200 = latest["MA200"]
    rsi = latest["RSI"]
    recent_peak = latest["Recent_Peak"]

    # Calculate how far the stock has dropped from its recent peak
    drop_from_peak = (recent_peak - current_price) / recent_peak

    # --- STRATEGY LOGIC WITH TRAILING STOP-LOSS ---

    # CRITICAL STOP-LOSS: Drop of 10% or more from the recent peak overrides everything
    if drop_from_peak >= 0.10:
        return "🔴 STOP-LOSS BREACHED (-10% from Peak)", "#D32F2F"

    # BUY: Price is above MAs, 50MA > 200MA (Uptrend), and RSI is not overbought
    elif current_price > ma50 and ma50 > ma200 and rsi < 65:
        return "🟢 BUY (Strong Uptrend)", "#2E7D32"

    # SELL: Standard technical exit (Price drops below 50MA or RSI is heavily overheated)
    elif current_price < ma50 or rsi > 80:
        return "🚨 SELL / TAKE PROFIT (Trend Weakening)", "#E65100"

    else:
        return "⚪ HOLD / NEUTRAL", "#4A4A4A"


def send_email(report_html):
    if not APP_PASSWORD:
        print("Error: EMAIL_PASS environment variable is not set.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "📊 Upgraded Daily Stock Alerts"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL

    part = MIMEText(report_html, "html")
    msg.attach(part)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print("Upgraded email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")


def run_screener():
    watchlist = ["AAPL", "MSFT", "NVDA", "AVGO", "AMZN", "TSLA"]
    table_rows = ""

    for ticker in watchlist:
        df = fetch_stock_data(ticker)
        if df is not None:
            df = calculate_indicators(df)
            signal_text, text_color = generate_signal(df)

            last_price = df.iloc[-1]["Close"]
            last_rsi = df.iloc[-1]["RSI"]

            # Build HTML rows dynamically with custom color styles
            table_rows += f"""
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">{ticker}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">${last_price:.2f}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{last_rsi:.1f}</td>
                <td style="padding: 10px; border: 1px solid #ddd; color: {text_color}; font-weight: bold;">{signal_text}</td>
            </tr>
            """

    # Beautifully styled HTML template
    email_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #333; }}
            table {{ border-collapse: collapse; width: 100%; max-width: 650px; border-radius: 4px; overflow: hidden; }}
            th {{ background-color: #1F2937; color: white; text-align: left; padding: 12px; font-weight: 600; }}
            tr:nth-child(even) {{ background-color: #F9FAFB; }}
        </style>
    </head>
    <body>
        <h2 style="color: #111827;">📊 Daily Buy/Sell Stock Alerts</h2>
        <p style="color: #4B5563;">Advanced trend analysis with a built-in 10% trailing stop-loss mechanism:</p>
        <table>
            <thead>
                <tr>
                    <th>Ticker</th>
                    <th>Price</th>
                    <th>RSI</th>
                    <th>Action Signal</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        <br>
        <p><small style="color: #9CA3AF;">Generated automatically via GitHub Actions.</small></p>
    </body>
    </html>
    """
    send_email(email_content)


if __name__ == "__main__":
    run_screener()

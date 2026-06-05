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


def get_full_market_watchlist():
    """Dynamically fetches S&P 500, NASDAQ-100, and Russell 2000 (Small/Mid Cap) tickers."""
    tickers = set()

    # 1. Fetch S&P 500
    try:
        sp500 = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]
        tickers.update(sp500["Symbol"].tolist())
    except Exception as e:
        print(f"Error fetching S&P 500 list: {e}")

    # 2. Fetch NASDAQ-100
    try:
        nasdaq100 = pd.read_html(
            "https://en.wikipedia.org/wiki/Nasdaq-100#Components"
        )[4]
        tickers.update(nasdaq100["Ticker"].tolist())
    except Exception as e:
        print(f"Error fetching NASDAQ-100 list: {e}")

    # 3. Fetch Russell 2000 (Small/Mid Caps via a reliable open-source source)
    try:
        r2000_url = "https://raw.githubusercontent.com/mrgnbrent/russell-2000-ticker-list/main/russell2000_tickers.csv"
        r2000 = pd.read_csv(r2000_url)
        tickers.update(r2000["Ticker"].tolist())
    except Exception as e:
        print(f"Error fetching Russell 2000 list: {e}")

    # Clean ticker formatting for yfinance compatibility (e.g., BRK.B -> BRK-B)
    clean_tickers = [
        str(t).strip().replace(".", "-").replace("/", "-") for t in tickers if t
    ]

    # Return sorted unique list
    return sorted(list(set(clean_tickers)))


def fetch_stock_data(ticker, period="1y"):
    try:
        # Using fast download defaults for individual ticker evaluation
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty or len(df) < 200:
            return None
        return df
    except Exception:
        return None


def calculate_indicators(df):
    df["MA50"] = df["Close"].rolling(window=50).mean()
    df["MA200"] = df["Close"].rolling(window=200).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    ema_gain = gain.ewm(com=13, adjust=False).mean()
    ema_loss = loss.ewm(com=13, adjust=False).mean()
    rs = ema_gain / ema_loss.replace(0, 0.00001)
    df["RSI"] = 100 - (100 / (1 + rs))

    df["Recent_Peak"] = df["Close"].rolling(window=20).max()
    return df


def generate_signal(df):
    latest = df.iloc[-1]
    current_price = latest["Close"]
    ma50 = latest["MA50"]
    ma200 = latest["MA200"]
    rsi = latest["RSI"]
    recent_peak = latest["Recent_Peak"]

    drop_from_peak = (recent_peak - current_price) / recent_peak

    if drop_from_peak >= 0.10:
        return "🔴 STOP-LOSS BREACHED (-10%)", "#D32F2F"
    elif current_price > ma50 and ma50 > ma200 and rsi < 65:
        return "🟢 BUY (Strong Uptrend)", "#2E7D32"
    elif current_price < ma50 or rsi > 80:
        return "🚨 TREND WEAKENING (Exit Setup)", "#E65100"
    else:
        return "⚪ HOLD", "#4A4A4A"


def send_email(report_html):
    if not APP_PASSWORD:
        print("Error: EMAIL_PASS environment variable is not set.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🚀 Broad Market Actionable Alerts"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL

    part = MIMEText(report_html, "html")
    msg.attach(part)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print("Broad Market email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")


def run_screener():
    print("Gathering comprehensive universe tickers...")
    watchlist = get_full_market_watchlist()
    print(f"Total market tickers loaded to scan: {len(watchlist)}")

    buy_rows = ""
    stop_rows = ""

    # Scanning loop
    for i, ticker in enumerate(watchlist):
        if i % 100 == 0 and i > 0:
            print(f"Scanned {i} / {len(watchlist)} stocks...")

        df = fetch_stock_data(ticker)
        if df is not None:
            df = calculate_indicators(df)
            signal_text, text_color = generate_signal(df)

            # FILTER: Completely ignore standard 'HOLD' or minor trend breaks to avoid inbox spam
            if "HOLD" in signal_text or "TREND WEAKENING" in signal_text:
                continue

            last_price = df.iloc[-1]["Close"]
            last_rsi = df.iloc[-1]["RSI"]

            row_html = f"""
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">{ticker}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">${last_price:.2f}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{last_rsi:.1f}</td>
                <td style="padding: 10px; border: 1px solid #ddd; color: {text_color}; font-weight: bold;">{signal_text}</td>
            </tr>
            """

            if "BUY" in signal_text:
                buy_rows += row_html
            elif "STOP-LOSS" in signal_text:
                stop_rows += row_html

    # Fallback placeholders if no alerts trigger on a specific day
    if not buy_rows:
        buy_rows = '<tr><td colspan="4" style="padding:10px; text-align:center; color:#777;">No new buy setups identified today.</td></tr>'
    if not stop_rows:
        stop_rows = '<tr><td colspan="4" style="padding:10px; text-align:center; color:#777;">No tracking positions triggered trailing stop-losses.</td></tr>'

    email_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #333; }}
            table {{ border-collapse: collapse; width: 100%; max-width: 700px; border-radius: 4px; overflow: hidden; margin-bottom: 25px; }}
            th {{ background-color: #1F2937; color: white; text-align: left; padding: 12px; font-weight: 600; }}
            tr:nth-child(even) {{ background-color: #F9FAFB; }}
            h3 {{ color: #111827; margin-top: 20px; border-bottom: 2px solid #E5E7EB; padding-bottom: 5px; max-width: 700px; }}
        </style>
    </head>
    <body>
        <h2>🚀 Broad Market Actionable Scanner</h2>
        <p>Scanning results compiled across S&P 500, NASDAQ-100, and Mid/Small Caps (Russell 2000):</p>
        
        <h3>🟢 Fresh Buy Signals</h3>
        <table>
            <thead>
                <tr><th>Ticker</th><th>Price</th><th>RSI</th><th>Action Signal</th></tr>
            </thead>
            <tbody>{buy_rows}</tbody>
        </table>

        <h3>🔴 Critical Stop-Loss Triggers</h3>
        <table>
            <thead>
                <tr><th>Ticker</th><th>Price</th><th>RSI</th><th>Action Signal</th></tr>
            </thead>
            <tbody>{stop_rows}</tbody>
        </table>
        
        <br>
        <p><small style="color: #9CA3AF;">Generated automatically via GitHub Actions.</small></p>
    </body>
    </html>
    """
    send_email(email_content)


if __name__ == "__main__":
    run_screener()

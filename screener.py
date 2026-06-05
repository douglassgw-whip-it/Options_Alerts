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

# 🎯 Your Explicit Core Watchlist (Will ALWAYS show at the top of the email)
CORE_WATCHLIST = [
    "AMZN",
    "GOOGL",
    "AAPL",
    "NVDA",
    "TSLA",
    "PLTR",
    "MSFT",
    "OKE",
    "VICI",
    "BA",
    "UBER",
    "RKLB",
    "MRK",
]


def get_broad_market_tickers():
    """Fetches broad market tickers from S&P 500, NASDAQ-100, and growth small/mid-caps."""
    tickers = set()

    # 1. Fetch S&P 500 from Wikipedia
    try:
        sp500 = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]
        tickers.update(sp500["Symbol"].tolist())
    except Exception as e:
        print(f"Error fetching S&P 500 list: {e}")

    # 2. Fetch NASDAQ-100 from Wikipedia
    try:
        nasdaq100 = pd.read_html(
            "https://en.wikipedia.org/wiki/Nasdaq-100#Components"
        )[4]
        tickers.update(nasdaq100["Ticker"].tolist())
    except Exception as e:
        print(f"Error fetching NASDAQ-100 list: {e}")

    # 3. Liquid Growth Small/Mid-Caps
    mid_small_caps = [
        "CELH",
        "WING",
        "ELF",
        "DUOL",
        "CROX",
        "SKX",
        "DKNG",
        "ROKU",
        "COIN",
        "HOOD",
        "SOFI",
        "AFRM",
        "U",
        "NET",
        "SNOW",
        "IOT",
        "PATH",
        "GTLB",
        "DDOG",
        "MDB",
        "FRSH",
        "TOST",
        "CHWY",
        "APP",
        "AAL",
        "DAL",
        "UAL",
        "CCL",
        "RCL",
        "NCLH",
        "PENN",
        "BYND",
        "OPEN",
        "RUN",
        "SPWR",
        "FSLR",
        "ENPH",
    ]
    tickers.update(mid_small_caps)

    # Clean formatting
    clean_tickers = [
        str(t).strip().replace(".", "-").replace("/", "-") for t in tickers if t
    ]
    return sorted(list(set(clean_tickers)))


def calculate_indicators(df):
    """Calculates 50MA, 200MA, RSI, and 20-day Trailing Highs."""
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
    """Evaluates trading rules based on moving averages, trailing stops, and RSI."""
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
    msg["Subject"] = "🚀 Broad Market & Core Watchlist Alerts"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL

    part = MIMEText(report_html, "html")
    msg.attach(part)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print("Hybrid market email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")


def run_screener():
    # Merge lists completely to download everything efficiently in one block
    broad_market = get_broad_market_tickers()
    master_download_list = sorted(list(set(CORE_WATCHLIST + broad_market)))

    print(f"Downloading master market data pool ({len(master_download_list)} tickers)...")
    try:
        data = yf.download(
            tickers=master_download_list,
            period="1y",
            group_by="ticker",
            threads=True,
        )
    except Exception as e:
        print(f"Bulk download failed: {e}")
        return

    core_rows = ""
    broad_buy_rows = ""
    broad_stop_rows = ""

    for ticker in master_download_list:
        try:
            # Handle multi-index data slice correctly
            if ticker not in data.columns.levels[0]:
                continue
            df = data[ticker].dropna(subset=["Close"])

            if len(df) < 200:
                continue

            df = df.copy()
            df = calculate_indicators(df)
            signal_text, text_color = generate_signal(df)

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

            # 1. Process Core Watchlist (Always display everything)
            if ticker in CORE_WATCHLIST:
                core_rows += row_html

            # 2. Process Broad Market Pool (Only record active signals)
            else:
                if "BUY" in signal_text:
                    broad_buy_rows += row_html
                elif "STOP-LOSS" in signal_text:
                    broad_stop_rows += row_html

        except Exception:
            continue

    # Fallbacks for broad market tables if no signals flash
    if not broad_buy_rows:
        broad_buy_rows = '<tr><td colspan="4" style="padding:10px; text-align:center; color:#777;">No new broad buy setups identified today.</td></tr>'
    if not broad_stop_rows:
        broad_stop_rows = '<tr><td colspan="4" style="padding:10px; text-align:center; color:#777;">No broad positions triggered trailing stops.</td></tr>'

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
        <h2>📊 Hybrid Market Portfolio Scanner</h2>
        
        <h3>⭐ Core Watchlist Status</h3>
        <p>Current snapshot of your primary target tickers:</p>
        <table>
            <thead>
                <tr><th>Ticker</th><th>Price</th><th>RSI</th><th>Action Signal</th></tr>
            </thead>
            <tbody>{core_rows}</tbody>
        </table>

        <hr style="border: 0; border-top: 1px dashed #D1D5DB; max-width: 700px; margin: 30px 0;">
        <h2>🔍 Broad Market Scanned Alerts</h2>
        <p>Dynamic hits scanned across S&P 500, NASDAQ-100, and Growth Mid/Small Caps:</p>

        <h3>🟢 Fresh Buy Signals</h3>
        <table>
            <thead>
                <tr><th>Ticker</th><th>Price</th><th>RSI</th><th>Action Signal</th></tr>
            </thead>
            <tbody>{broad_buy_rows}</tbody>
        </table>

        <h3>🔴 Critical Stop-Loss Triggers</h3>
        <table>
            <thead>
                <tr><th>Ticker</th><th>Price</th><th>RSI</th><th>Action Signal</th></tr>
            </thead>
            <tbody>{broad_stop_rows}</tbody>
        </table>
        
        <br>
        <p><small style="color: #9CA3AF;">Generated automatically via GitHub Actions.</small></p>
    </body>
    </html>
    """
    send_email(email_content)


if __name__ == "__main__":
    run_screener()

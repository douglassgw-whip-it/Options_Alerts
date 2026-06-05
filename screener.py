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
    """Dynamically fetches reliable S&P 500, NASDAQ-100, and mid/small cap tickers."""
    tickers = set()

    # 1. Fetch S&P 500 from Wikipedia
    try:
        sp500 = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )[0]
        tickers.update(sp500["Symbol"].tolist())
        print(f"Loaded {len(sp500)} tickers from S&P 500.")
    except Exception as e:
        print(f"Error fetching S&P 500 list: {e}")

    # 2. Fetch NASDAQ-100 from Wikipedia
    try:
        nasdaq100 = pd.read_html(
            "https://en.wikipedia.org/wiki/Nasdaq-100#Components"
        )[4]
        tickers.update(nasdaq100["Ticker"].tolist())
        print(f"Loaded components from NASDAQ-100.")
    except Exception as e:
        print(f"Error fetching NASDAQ-100 list: {e}")

    # 3. Use a highly liquid, static list of top Mid/Small Cap growth stars to prevent timeouts
    # This ensures a high-quality pool without the clutter of 2,000 dead/illiquid micro-caps
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
        "PLTR",
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

    # Clean ticker formatting for yfinance compatibility (e.g., BRK.B -> BRK-B)
    clean_tickers = [
        str(t).strip().replace(".", "-").replace("/", "-") for t in tickers if t
    ]
    return sorted(list(set(clean_tickers)))


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
    watchlist = get_full_market_watchlist()
    print(f"Requesting bulk historical data for {len(watchlist)} tickers...")

    # 🔥 CRITICAL BULK DOWNLOAD: Downloads EVERYTHING concurrently in one shot
    # This prevents Yahoo Finance blocks and executes in under 15 seconds
    try:
        data = yf.download(
            tickers=watchlist, period="1y", group_by="ticker", threads=True
        )
    except Exception as e:
        print(f"Bulk download failed: {e}")
        return

    buy_rows = ""
    stop_rows = ""

    print("Analyzing indicators across the market data pool...")
    for ticker in watchlist:
        try:
            # Safely extract individual ticker slice from the bulk data
            if ticker not in data.columns.levels[0]:
                continue
            df = data[ticker].dropna(subset=["Close"])

            if len(df) < 200:
                continue

            # 1. Technical calculations
            df = df.copy()
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

            # 2. Extract latest metrics
            latest = df.iloc[-1]
            current_price = latest["Close"]
            ma50 = latest["MA50"]
            ma200 = latest["MA200"]
            rsi = latest["RSI"]
            recent_peak = latest["Recent_Peak"]

            drop_from_peak = (recent_peak - current_price) / recent_peak

            # 3. Strategy Evaluation
            if drop_from_peak >= 0.10:
                signal_text, text_color = (
                    "🔴 STOP-LOSS BREACHED (-10%)",
                    "#D32F2F",
                )
            elif current_price > ma50 and ma50 > ma200 and rsi < 65:
                signal_text, text_color = "🟢 BUY (Strong Uptrend)", "#2E7D32"
            else:
                continue  # Silently drop neutral/hold/weak setups to prevent inbox clutter

            row_html = f"""
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">{ticker}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">${current_price:.2f}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{rsi:.1f}</td>
                <td style="padding: 10px; border: 1px solid #ddd; color: {text_color}; font-weight: bold;">{signal_text}</td>
            </tr>
            """

            if "BUY" in signal_text:
                buy_rows += row_html
            elif "STOP-LOSS" in signal_text:
                stop_rows += row_html

        except Exception:
            continue  # Avoid letting one weird stock break the whole run

    # Fallbacks if the market had a completely neutral day
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
        <p>Scanning results compiled across S&P 500, NASDAQ-100, and Small/Mid Cap growth leaders:</p>
        
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

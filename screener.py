import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import yfinance as yf

# ==========================================
# 1. DATA PREP
# ==========================================
def prep_data(ticker):
    """Fetches stock data and calculates MA50, MA200, RSI, and Recent Peak."""
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False, multi_level_index=False)
        if df.empty or len(df) < 200:
            return None

        df.columns = [str(col).strip() for col in df.columns]

        df['MA50'] = df['Close'].rolling(window=50).mean()
        df['MA200'] = df['Close'].rolling(window=200).mean()
        df['Recent_Peak'] = df['Close'].rolling(window=252, min_periods=1).max()

        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        clean_df = df.dropna()
        return clean_df if not clean_df.empty else None
    except Exception as e:
        print(f"⚠️ Data extraction failed for {ticker}: {e}")
        return None

# ==========================================
# 2. SIGNAL LOGIC
# ==========================================
def generate_signal(df):
    """Evaluates trading rules based on moving averages, trailing stops, RSI, and daily momentum."""
    if df is None or len(df) < 2:
        return "⚪ HOLD", "#4A4A4A"
        
    latest = df.iloc[-1]
    prior = df.iloc[-2]
    
    current_price = float(latest["Close"])
    prior_price = float(prior["Close"])
    ma50 = float(latest["MA50"])
    ma200 = float(latest["MA200"])
    rsi = float(latest["RSI"])
    recent_peak = float(latest["Recent_Peak"])

    daily_return = (current_price - prior_price) / prior_price if prior_price else 0
    drop_from_peak = (recent_peak - current_price) / recent_peak if recent_peak else 0

    if daily_return >= 0.03:
        if current_price > ma50 and ma50 > ma200:
            return "🚀 BULLISH BREAKOUT (Strong Momentum)", "#2E7D32"
        else:
            return "🔄 BULLISH REVERSAL (Volume Surge)", "#0288D1"
    elif drop_from_peak >= 0.10:
        return "🔴 STOP-LOSS BREACHED (-10%)", "#D32F2F"
    elif current_price > ma50 and ma50 > ma200 and rsi < 65:
        return "🟢 BUY (Strong Uptrend)", "#2E7D32"
    elif current_price < ma50 or rsi > 80:
        return "🚨 TREND WEAKENING (Exit Setup)", "#E65100"
    else:
        return "⚪ HOLD", "#4A4A4A"

# ==========================================
# 3. EMAIL DISPATCH (PORT 465 DIRECT SSL ENCRYPTION)
# ==========================================
def send_summary_email(alerts):
    smtp_user = os.environ.get("EMAIL_USER")
    smtp_pass = os.environ.get("EMAIL_PASSWORD")
    to_email = os.environ.get("TO_EMAIL")

    if not all([smtp_user, smtp_pass, to_email]):
        raise ValueError("❌ CRITICAL CONFIG: GitHub Environment secrets returned empty strings.")

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"📈 Market Screener Alert: {len(alerts)} Actions Triggered"
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Reply-To"] = smtp_user

    html_content = """
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>Screener Signal Summary</h2>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; border: 1px solid #ddd;">
          <tr style="background-color: #f2f2f2;">
            <th>Ticker</th>
            <th>Signal Status</th>
          </tr>
    """
    for ticker, (signal, color) in alerts.items():
        html_content += f"<tr><td><strong>{ticker}</strong></td><td style='color: {color}; font-weight: bold;'>{signal}</td></tr>"
        
    html_content += "</table></body></html>"
    msg.attach(MIMEText(html_content, "html"))

    # Direct port 465 secure socket connection bypasses cloud firewalls
    print("Initiating Direct implicit SSL tunnel via smtp.gmail.com:465...")
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)
    
    print("Authenticating credentials...")
    server.login(smtp_user, smtp_pass)
    
    print("Transmitting payload...")
    server.sendmail(smtp_user, to_email, msg.as_string())
    server.quit()
    print("✨ SUCCESS: Pipeline complete! Handed down directly to Gmail.")

# ==========================================
# 4. MAIN RUNNER
# ==========================================
def main():
    print("==================================================")
    print("🚀 STARTING SCREENER EVALUATION")
    print("==================================================")
    
    watchlist = ["RKLB", "PLTR", "BBAI", "VLN", "INFQ", "ACHR", "SPY"]
    active_alerts = {}

    for ticker in watchlist:
        print(f"Fetching data for {ticker}...")
        df = prep_data(ticker)
        
        if df is None:
            print(f"   ↳ ⚠️ Skipped: Insufficient data rows.")
            continue
            
        signal, color = generate_signal(df)
        print(f"   ↳ Result: {signal}")

        if "⚪ HOLD" not in signal:
            active_alerts[ticker] = (signal, color)

    print("\n==================================================")
    print(f"📊 SCREENER RUN COMPLETE. Actionable alerts: {len(active_alerts)}")
    
    if not active_alerts:
        print("💡 NOTICE: Injecting baseline run confirmation row...")
        active_alerts["Screener Verification"] = ("⚪ All watched elements evaluating as HOLD", "#4A4A4A")

    print("Initiating email dispatch...")
    send_summary_email(active_alerts)
    print("==================================================")

if __name__ == "__main__":
    main()

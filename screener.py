import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd

# ==========================================
# 1. ROBUST SIGNAL GENERATION LOGIC
# ==========================================
def generate_signal(df):
    """
    Evaluates trading rules based on moving averages, trailing stops, RSI, and daily momentum.
    Guarded against Missing Data (KeyErrors) and Zero Division.
    """
    if df is None or len(df) < 2:
        return "⚪ HOLD", "#4A4A4A"
        
    latest = df.iloc[-1]
    prior = df.iloc[-2]
    
    # Safe retrieval to prevent KeyErrors if columns are missing
    current_price = latest.get("Close")
    prior_price = prior.get("Close")
    ma50 = latest.get("MA50")
    ma200 = latest.get("MA200")
    rsi = latest.get("RSI")
    recent_peak = latest.get("Recent_Peak")

    # Guard: Ensure we have core price data before calculating returns
    if current_price is None or prior_price is None:
        return "⚪ HOLD (Missing Price Data)", "#4A4A4A"

    # Calculate today's performance safely
    daily_return = (current_price - prior_price) / prior_price if prior_price else 0
    
    # Guard against ZeroDivisionError for recent_peak
    if recent_peak and recent_peak > 0:
        drop_from_peak = (recent_peak - current_price) / recent_peak
    else:
        drop_from_peak = 0

    # Rule 1: 🔥 BULLISH OVERRIDE: Catch high-momentum breakout/reversal days
    if daily_return >= 0.03:
        if ma50 and ma200 and current_price > ma50 and ma50 > ma200:
            return "🚀 BULLISH BREAKOUT (Strong Momentum)", "#2E7D32"
        else:
            return "🔄 BULLISH REVERSAL (Volume Surge)", "#0288D1"

    # Rule 2: Trailing Stop-Loss Trigger
    elif drop_from_peak >= 0.10:
        return "🔴 STOP-LOSS BREACHED (-10%)", "#D32F2F"
        
    # Rule 3: Standard Trend Following Buy Setup
    elif ma50 and ma200 and rsi and current_price > ma50 and ma50 > ma200 and rsi < 65:
        return "🟢 BUY (Strong Uptrend)", "#2E7D32"
        
    # Rule 4: Moving Average / Overbought Breakdown
    elif (ma50 and current_price < ma50) or (rsi and rsi > 80):
        return "🚨 TREND WEAKENING (Exit Setup)", "#E65100"
        
    else:
        return "⚪ HOLD", "#4A4A4A"

# ==========================================
# 2. EMAIL DELIVERY WITH VERBOSE LOGGING
# ==========================================
def send_summary_email(alerts):
    """
    Compiles active alerts and dispatches an email.
    Includes explicit print statements to debug GitLab environment variable drop-offs.
    """
    # Fetch credentials from GitLab CI/CD Variables
    smtp_user = os.environ.get("EMAIL_USER")
    smtp_pass = os.environ.get("EMAIL_PASSWORD")
    to_email = os.environ.get("TO_EMAIL")

    # Debug: Check if variables are missing in the environment
    if not all([smtp_user, smtp_pass, to_email]):
        print("❌ CONFIG ERROR: Missing one or more environment variables!")
        print(f"-> EMAIL_USER: {'FOUND' if smtp_user else 'MISSING'}")
        print(f"-> EMAIL_PASSWORD: {'FOUND' if smtp_pass else 'MISSING'}")
        print(f"-> TO_EMAIL: {'FOUND' if to_email else 'MISSING'}")
        print("Hint: If running a non-main branch, verify your GitLab variables are NOT marked 'Protected'.")
        return

    # Build the HTML email body
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📈 Market Screener Alert: {len(alerts)} Actions Triggered"
    msg["From"] = smtp_user
    msg["To"] = to_email

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
        html_content += f"""
          <tr>
            <td><strong>{ticker}</strong></td>
            <td style="color: {color}; font-weight: bold;">{signal}</td>
          </tr>
        """
        
    html_content += "</table></body></html>"
    msg.attach(MIMEText(html_content, "html"))

    # Connect and send via SMTP with explicit safety try/except blocks
    try:
        print("Connecting to SMTP server (smtp.gmail.com:587)...")
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
        server.starttls()
        
        print("Attempting SMTP Login...")
        server.login(smtp_user, smtp_pass)
        
        print("Login verified. Transmitting email payload...")
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        print("✨ SUCCESS: Email successfully sent and accepted by relay server!")
        
    except smtplib.SMTPAuthenticationError:
        print("❌ SMTP AUTHENTICATION FAILED: Check your App Password.")
        print("Ensure you are using a 16-character Google App Password, not your standard master account password.")
    except Exception as e:
        print(f"❌ CRITICAL SMTP ERROR: Network or handshaking exception caught:\n{e}")

# ==========================================
# 3. CORE PROCESSING LOOP
# ==========================================
def main():
    # Mock Dictionary representing your data pipeline dataframes
    # Replace this block with your actual data fetching loop (e.g., yfinance or local CSV loads)
    ticker_data = {
        "RKLB": pd.DataFrame({"Close": [10.0, 11.5], "MA50": [9.0, 9.1], "MA200": [8.0, 8.1], "RSI": [55, 62], "Recent_Peak": [12.0, 12.0]}),
        "PLTR": pd.DataFrame({"Close": [40.0, 40.1], "MA50": [38.0, 38.2], "MA200": [35.0, 35.1], "RSI": [50, 52], "Recent_Peak": [45.0, 45.0]}),
        "BBAI": pd.DataFrame({"Close": [2.50, 2.48], "MA50": [2.80, 2.78], "MA200": [3.00, 2.98], "RSI": [41, 39], "Recent_Peak": [3.20, 3.20]})
    }

    active_alerts = {}

    print(f"Starting processing loop for {len(ticker_data)} symbols...")
    
    for ticker, df in ticker_data.items():
        signal, color = generate_signal(df)
        print(f"-> Logged: {ticker:5} | Output: {signal}")

        # Skip holds completely so we don't spam empty emails
        if "⚪ HOLD" in signal:
            continue
            
        active_alerts[ticker] = (signal, color)

    # Dispatch only if actionable data is present
    if active_alerts:
        print(f"\nActionable events found ({len(active_alerts)}). Handing off to mail handler...")
        send_summary_email(active_alerts)
    else:
        print("\nChecking finished: Everything evaluated to a 'HOLD'. Email routine bypassed.")

if __name__ == "__main__":
    main()

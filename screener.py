import os
import smtplib
import numpy as np
import pandas as pd
import yfinance as yf
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# 1. INSTITUTIONAL LIQUIDITY UNIVERSE MIRROR
# ==========================================
def fetch_options_universe():
    print("Initializing high-liquidity multi-index universe...")
    tickers = []
    
    # Extract S&P 500 components
    try:
        sp500_df = pd.read_csv("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv")
        tickers.extend([str(t).replace('.', '-') for t in sp500_df['Symbol'].tolist()])
    except Exception as e:
        print(f"⚠️ S&P 500 mirror bypassed: {e}. Fallback triggered.")
        
    # Extract NASDAQ-100 components
    try:
        nasdaq_df = pd.read_csv("https://raw.githubusercontent.com/Ate329/top-us-stock-tickers/main/tickers/top_100.csv")
        col = 'symbol' if 'symbol' in nasdaq_df.columns else 'Symbol'
        tickers.extend([str(t).replace('.', '-') for t in nasdaq_df[col].tolist()])
    except Exception as e:
        print(f"⚠️ NASDAQ-100 mirror bypassed: {e}")

    # Explicit core watchlists and macro trading drivers
    core_anchors = ["QQQ", "IWM", "DIA", "RKLB", "PLTR", "BBAI", "VLN", "ACHR", "JEPI", "JEPQ"]
    full_universe = list(set(core_anchors + tickers))
    print(f"🎯 Integration complete: {len(full_universe)} institutional targets queued.")
    return full_universe

# ==========================================
# 2. MARKDOWN RENDER PIPELINE
# ==========================================
def build_markdown_matrix(group_a, group_b, group_c):
    output = "## OPTIMIZED 30-45D OPTIONS SCORING MATRIX\n"
    output += "=======================================================================\n\n"
    
    output += "### 🚀 GROUP C: BREAKOUT SIGNALS (Volume/Momentum Confirmations)\n"
    output += "| Ticker | Price | RSI | Vol Relative |\n"
    output += "| :--- | :--- | :--- | :--- |\n"
    for t, m in group_c:
        output += f"| {t:<6} | {m['Price']:<9} | {m['RSI']:<5} | {m['VolumeRel']:<12} |\n"
    
    output += "\n" + "---" * 20 + "\n\n"
    
    output += "### 📈 GROUP A: DELTA MOMENTUM BREAKOUTS (Long Call / Debit Spread Targets)\n"
    output += "*Filter: Daily RSI >= 50 | Low-to-Mid IV Rank for Protection against Vol Crush*\n\n"
    output += "| Ticker | Price | Ann Alpha | Daily RSI | 30D IV Rank | Target Strike (+1 ATR) | Setup Score |\n"
    output += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for t, m in group_a:
        output += f"| {t:<6} | {m['Price']:<9} | {m['Alpha']:+9.1%} | {m['RSI']:<9} | {m['IVRank']:<10} | {m['TargetStrike']:<22} | {m['Score']:<11} |\n"
        
    output += "\n" + "---" * 20 + "\n\n"
    
    output += "### 💵 GROUP B: STRUCTURAL PULLBACKS (Premium Harvesting / Cash-Secured Puts)\n"
    output += "*Filter: Daily RSI < 50 | High IV Rank for Peak Premium Volatility Capture*\n\n"
    output += "| Ticker | Price | Ann Alpha | Daily RSI | 30D IV Rank | Suggested Margin Floor (-2 ATR) | Setup Score |\n"
    output += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for t, m in group_b:
        output += f"| {t:<6} | {m['Price']:<9} | {m['Alpha']:+9.1%} | {m['RSI']:<9} | {m['IVRank']:<10} | {m['StrikeFloor']:<31} | {m['Score']:<11} |\n"

    output += "\n=======================================================================\n"
    output += "🤖 *Automated Options Intelligence Pipeline Engine via GitHub Cloud Workspace Universe Engine*"
    return output

# ==========================================
# 3. SECURE REPO-SECRETS SMTP TUNNEL
# ==========================================
def send_matrix_email(matrix_text):
    smtp_user = os.environ.get("EMAIL_USER")
    smtp_pass = os.environ.get("EMAIL_PASSWORD")
    to_email = os.environ.get("TO_EMAIL")

    if not all([smtp_user, smtp_pass, to_email]):
        raise ValueError("❌ CRITICAL CONFIG: Missing core environment secrets.")

    msg = MIMEMultipart()
    msg["Subject"] = "📊 OPTIMIZED 30-45D OPTIONS SCORING MATRIX"
    msg["From"] = smtp_user
    msg["To"] = to_email
    
    body = f"Total-market multi-index macro options scan complete. Verified setups:\n\n{matrix_text}"
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())
    print("✨ SUCCESS: Options matrix delivered securely to your inbox.")

# ==========================================
# 4. DATA ENGINE & CORE SIGNAL LOGIC
# ==========================================
def main():
    print("🚀 DISPATCHING OPTIONS DATA SCREENING PIPELINE")
    
    spy_df = yf.download("SPY", period="1y", interval="1d", progress=False, auto_adjust=False)
    if isinstance(spy_df.columns, pd.MultiIndex):
        spy_df.columns = spy_df.columns.get_level_values(0)
    spy_close = spy_df['Adj Close'].dropna()
    spy_cum = (1 + spy_close.pct_change().dropna()).prod() - 1

    watchlist = fetch_options_universe()
    group_a_pool, group_b_pool, group_c_pool = [], [], []

    for ticker in watchlist:
        if ticker == "SPY": continue
        try:
            ticker_df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=False)
            if ticker_df.empty or len(ticker_df) < 60: continue
            if isinstance(ticker_df.columns, pd.MultiIndex):
                ticker_df.columns = ticker_df.columns.get_level_values(0)

            close_series = ticker_df['Adj Close']
            volume_series = ticker_df['Volume']
            high_series = ticker_df['High']
            low_series = ticker_df['Low']

            if volume_series.tail(20).mean() < 2500000: continue
            current_price = close_series.iloc[-1]

            # Indicators
            alpha = ((1 + close_series.pct_change().dropna()).prod() - 1) - spy_cum
            rolling_30d_vol = np.log(close_series / close_series.shift(1)).dropna().rolling(window=30).std() * np.sqrt(252)
            iv_rank_proxy = (rolling_30d_vol.dropna() < rolling_30d_vol.iloc[-1]).sum() / len(rolling_30d_vol.dropna()) if len(rolling_30d_vol.dropna()) > 0 else 0.5
            
            delta = close_series.diff()
            rsi_series = 100 - (100 / (1 + (delta.where(delta > 0, 0).rolling(14).mean() / (-delta.where(delta < 0, 0).rolling(14).mean()))))
            current_rsi = rsi_series.iloc[-1] if not np.isnan(rsi_series.iloc[-1]) else 50.0

            # Breakout Logic (Group C)
            sma_50 = close_series.rolling(50).mean().iloc[-1]
            high_20d = high_series.rolling(20).max().shift(1).iloc[-1]
            vol_avg_20 = volume_series.rolling(20).mean().iloc[-1]
            if current_price > high_20d and volume_series.iloc[-1] >= (1.5 * vol_avg_20) and 50 <= current_rsi <= 72 and current_price > sma_50:
                group_c_pool.append((ticker, {"Price": f"${current_price:,.2f}", "RSI": int(current_rsi), "VolumeRel": f"{volume_series.iloc[-1]/vol_avg_20:.1f}x"}))

            # Original Logic (Group A/B)
            atr_14 = pd.concat([high_series - low_series, (high_series - close_series.shift()).abs(), (low_series - close_series.shift()).abs()], axis=1).max(axis=1).rolling(14).mean().iloc[-1]
            if current_rsi >= 50:
                score_a = (1 if 55 < current_rsi < 70 else 0) + (1 if alpha > 0.05 else 0) + (1 if iv_rank_proxy < 0.45 else 0)
                group_a_pool.append((ticker, {"Price": f"${current_price:,.2f}", "Alpha": alpha, "RSI": int(current_rsi), "IVRank": f"{iv_rank_proxy * 100:.0f}%", "TargetStrike": f"${current_price + atr_14:,.2f}", "Score": f"{score_a} / 3", "RawIVRank": iv_rank_proxy}))
            else:
                score_b = (1 if current_rsi < 38 else 0) + (1 if iv_rank_proxy > 0.65 else 0) + (1 if alpha > -0.15 else 0)
                group_b_pool.append((ticker, {"Price": f"${current_price:,.2f}", "Alpha": alpha, "RSI": int(current_rsi), "IVRank": f"{iv_rank_proxy * 100:.0f}%", "StrikeFloor": f"${current_price - (2 * atr_14):,.2f}", "Score": f"{score_b} / 3", "RawIVRank": iv_rank_proxy}))
        except Exception: continue

    group_a_pool.sort(key=lambda x: x[1]["Alpha"], reverse=True)
    group_b_pool.sort(key=lambda x: x[1]["RawIVRank"], reverse=True)
    
    matrix_output = build_markdown_matrix(group_a_pool[:15], group_b_pool[:15], group_c_pool)
    print(matrix_output)
    send_matrix_email(matrix_output)

if __name__ == "__main__":
    main()

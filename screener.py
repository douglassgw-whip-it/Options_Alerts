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
def build_markdown_matrix(group_a, group_b):
    output = "## OPTIMIZED 30-45D OPTIONS SCORING MATRIX\n"
    output += "=======================================================================\n\n"
    
    output += "### 📈 GROUP A: DELTA MOMENTUM BREAKOUTS (Long Call / Debit Spread Targets)\n"
    output += "*Filter: Daily RSI >= 50 | Low-to-Mid IV Rank for Protection against Vol Crush*\n\n"
    output += "| Ticker | Price     | Ann Alpha | Daily RSI | 30D IV Rank | Target Strike (+1 ATR) | Setup Score |\n"
    output += "| :---   | :---      | :---      | :---      | :---        | :---                   | :---        |\n"
    for t, m in group_a:
        output += f"| {t:<6} | {m['Price']:<9} | {m['Alpha']:+9.1%} | {m['RSI']:<9} | {m['IVRank']:<10} | {m['TargetStrike']:<22} | {m['Score']:<11} |\n"
        
    output += "\n" + "---" * 20 + "\n\n"
    
    output += "### 💵 GROUP B: STRUCTURAL PULLBACKS (Premium Harvesting / Cash-Secured Puts)\n"
    output += "*Filter: Daily RSI < 50 | High IV Rank for Peak Premium Volatility Capture*\n\n"
    output += "| Ticker | Price     | Ann Alpha | Daily RSI | 30D IV Rank | Suggested Margin Floor (-2 ATR) | Setup Score |\n"
    output += "| :---   | :---      | :---      | :---      | :---        | :---                            | :---        |\n"
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
    
    # SPY Total Return Baseline Tracking
    spy_df = yf.download("SPY", period="1y", interval="1d", progress=False)
    if isinstance(spy_df.columns, pd.MultiIndex):
        spy_df.columns = spy_df.columns.get_level_values(0)
    spy_close = spy_df['Adj Close'].dropna()
    spy_cum = (1 + spy_close.pct_change().dropna()).prod() - 1

    watchlist = fetch_options_universe()
    group_a_pool = [] # Calls / Debits
    group_b_pool = [] # Puts / Credits

    for ticker in watchlist:
        if ticker == "SPY":
            continue
        try:
            ticker_df = yf.download(ticker, period="1y", interval="1d", progress=False)
            if ticker_df.empty or len(ticker_df) < 60:
                continue
                
            if isinstance(ticker_df.columns, pd.MultiIndex):
                ticker_df.columns = ticker_df.columns.get_level_values(0)

            # --- FIXED TO ADJ CLOSE TO FACTOR IN ALL HIGH-YIELD DISTRIBUTIONS/DIVIDENDS ---
            close_series = ticker_df['Adj Close']
            volume_series = ticker_df['Volume']
            high_series = ticker_df['High']
            low_series = ticker_df['Low']

            # --- LIQUIDITY GATE: Filter out tickers with illiquid options chain markers ---
            avg_volume_20d = volume_series.tail(20).mean()
            if avg_volume_20d < 2500000:
                continue

            current_price = close_series.iloc[-1]

            # --- TRUE ADJUSTED TOTAL RETURN ALPHA ---
            stock_returns = close_series.pct_change().dropna()
            stock_cum = (1 + stock_returns).prod() - 1
            alpha = stock_cum - spy_cum

            # --- OPTIONS EXPIRE IN 30-45 DAYS: TRACK TRADING WINDOW IMPLIED VOLATILITY (IV) PROXY ---
            # Calculates daily log returns and rolls a 30-day trading window to match the option duration
            daily_log_returns = np.log(close_series / close_series.shift(1)).dropna()
            rolling_30d_vol = daily_log_returns.rolling(window=30).std() * np.sqrt(252)
            current_30d_iv_proxy = rolling_30d_vol.iloc[-1]
            
            valid_vols = rolling_30d_vol.dropna()
            iv_rank_proxy = (valid_vols < current_30d_iv_proxy).sum() / len(valid_vols) if len(valid_vols) > 0 else 0.5

            # --- COHERENT TECHNICAL MOMENTUM (RSI-14) ---
            delta = close_series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_series = 100 - (100 / (1 + (gain / loss)))
            current_rsi = rsi_series.iloc[-1]
            if np.isnan(current_rsi): current_rsi = 50.0

            # --- EXPIRATION VOLATILITY BUFFER (ATR-14) ---
            high_low = high_series - low_series
            high_close = (high_series - close_series.shift()).abs()
            low_close = (low_series - close_series.shift()).abs()
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr_14 = true_range.rolling(14).mean().iloc[-1]

            # Strategy Math for Expiration Strikes
            strike_floor = current_price - (2 * atr_14) # 2 ATR buffer down for Put Sales
            target_strike = current_price + (1 * atr_14) # 1 ATR target up for Long Calls

            # ==========================================
            # STRATEGY RISK SCORING MECHANISM
            # ==========================================
            # Group A: Call Option Setups (RSI over 50, wants lower IV Rank to protect from severe premium crush)
            if current_rsi >= 50:
                score_a = 0
                if current_rsi > 55 and current_rsi < 70: score_a += 1  # In the breakout sweet spot, not overextended
                if alpha > 0.05: score_a += 1                         # Outperforming benchmark
                if iv_rank_proxy < 0.45: score_a += 1                 # Premium is cheap, safe to buy directional exposure
                
                metrics = {
                    "Price": f"${current_price:,.2f}", "Alpha": alpha, "RSI": int(current_rsi),
                    "IVRank": f"{iv_rank_proxy * 100:.0f}%", "TargetStrike": f"${target_strike:,.2f}",
                    "Score": f"{score_a} / 3", "RawIVRank": iv_rank_proxy
                }
                group_a_pool.append((ticker, metrics))

            # Group B: Put Selling Income Setups (RSI under 50, wants bloated IV Rank to extract maximum premium)
            else:
                score_b = 0
                if current_rsi < 38: score_b += 1                     # Underlyings are technically oversold
                if iv_rank_proxy > 0.65: score_b += 1                 # Implied Premium is highly jacked; edge to the option seller
                if alpha > -0.15: score_b += 1                        # Not trapped in an unbacked terminal death spiral
                
                metrics = {
                    "Price": f"${current_price:,.2f}", "Alpha": alpha, "RSI": int(current_rsi),
                    "IVRank": f"{iv_rank_proxy * 100:.0f}%", "StrikeFloor": f"${strike_floor:,.2f}",
                    "Score": f"{score_b} / 3", "RawIVRank": iv_rank_proxy
                }
                group_b_pool.append((ticker, metrics))

        except Exception:
            continue

    # Sort structures logically by edge parameters
    group_a_pool.sort(key=lambda x: x[1]["Alpha"], reverse=True)    # Highest relative alpha runners first
    group_b_pool.sort(key=lambda x: x[1]["RawIVRank"], reverse=True) # Juiciest premium opportunities ranked at the top

    matrix_output = build_markdown_matrix(group_a_pool[:15], group_b_pool[:15])
    print(matrix_output)
    
    send_matrix_email(matrix_output)

if __name__ == "__main__":
    main()

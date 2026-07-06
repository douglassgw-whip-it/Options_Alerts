import os
import time
import smtplib
import numpy as np
import pandas as pd
import yfinance as yf
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# 1. EXPANDED DYNAMIC MULTI-INDEX UNIVERSE
# ==========================================
def fetch_broad_market_universe():
    """Dynamically scrapes S&P 500 and Nasdaq-100 rosters simultaneously."""
    print("Executing broad extraction of institutional indices...")
    tickers = []
    
    # Track 1: S&P 500
    try:
        sp500_table = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        sp500_list = sp500_table[0]['Symbol'].tolist()
        tickers.extend([t.replace('.', '-') for t in sp500_list])
        print(f"✅ Extracted S&P 500 catalog rows.")
    except Exception as e:
        print(f"⚠️ S&P 500 scrape bypassed: {e}")

    # Track 2: NASDAQ-100 Tech/Growth Index
    try:
        nasdaq_table = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
        # Finds the main component layout table dynamically
        for table in nasdaq_table:
            if 'Ticker' in table.columns or 'Symbol' in table.columns:
                col = 'Ticker' if 'Ticker' in table.columns else 'Symbol'
                nasdaq_list = table[col].dropna().tolist()
                tickers.extend([t.replace('.', '-') for t in nasdaq_list])
                print(f"✅ Extracted NASDAQ-100 catalog rows.")
                break
    except Exception as e:
        print(f"⚠️ NASDAQ-100 scrape bypassed: {e}")

    # Index Benchmarks & Watchlist fallbacks
    macro_anchors = ["QQQ", "IWM", "DIA", "RKLB", "PLTR", "BBAI", "VLN", "ACHR"]
    full_universe = list(set(macro_anchors + tickers))
    print(f"📊 Broad Engine Complete. Total components in live routing matrix: {len(full_universe)}")
    return full_universe

# ==========================================
# 2. OPTION QUANT ANALYSIS ENGINE
# ==========================================
def calculate_matrix_metrics(ticker, spy_df):
    """Calculates alpha, liquidity, RSI, IV Rank, and ATR options parameters."""
    try:
        # Download historical footprint for the current stock
        df = yf.download(ticker, period="1y", interval="1d", progress=False, multi_level_index=False)
        if df.empty or len(df) < 50:
            return None

        df.columns = [str(col).strip() for col in df.columns]
        
        # STAGE A: LIQUIDITY CHECK (Ensures tight options spreads)
        avg_volume_10d = df['Volume'].tail(10).mean()
        if avg_volume_10d < 1000000:  
            return None

        # STAGE B: BENCHMARK MATRIX ALIGNMENT
        combined = pd.concat([df['Close'].rename('Stock'), spy_df['Close'].rename('SPY')], axis=1).dropna()
        if len(combined) < 30:
            return None

        # Annualized Alpha (Benchmark Relative alpha sizing)
        stock_returns = combined['Stock'].pct_change().dropna()
        spy_returns = combined['SPY'].pct_change().dropna()
        alpha = ((1 + stock_returns).prod() - 1) - ((1 + spy_returns).prod() - 1)

        # 20-Day Relative Historical Volatility
        stock_vol_20d = stock_returns.tail(20).std() * np.sqrt(252)
        spy_vol_20d = spy_returns.tail(20).std() * np.sqrt(252)
        relative_vol = stock_vol_20d / spy_vol_20d if spy_vol_20d > 0 else 1.0

        # Implied Historical Volatility Percentile (HV Rank Range)
        rolling_20d_vol = stock_returns.rolling(20).std() * np.sqrt(252)
        hv_min = rolling_20d_vol.min()
        hv_max = rolling_20d_vol.max()
        hv_rank = ((stock_vol_20d - hv_min) / (hv_max - hv_min)) if (hv_max - hv_min) > 0 else 0.5

        # Daily Momentum (14-Day RSI Vector)
        delta = combined['Stock'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi_series = 100 - (100 / (1 + (gain / loss)))
        
        latest_price = combined['Stock'].iloc[-1]
        latest_rsi = rsi_series.iloc[-1] if not np.isnan(rsi_series.iloc[-1]) else 50.0

        # Structural Risk Margin (ATR 2.0x Safety Floor for Put writers)
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(14).mean().iloc[-1]
        suggested_strike_margin = latest_price - (2 * atr)

        # Tactical Scoring Configuration Rules
        score_a = 0  # Call Buying
        if latest_rsi > 55: score_a += 1
        if alpha > 0.05: score_a += 1
        if hv_rank < 0.40: score_a += 1  

        score_b = 0  # Put Selling
        if latest_rsi < 35: score_b += 1
        if alpha < 0: score_b += 1
        if hv_rank > 0.60: score_b += 1  

        return {
            "Price": f"${latest_price:,.2f}",
            "Alpha": alpha,
            "Vol": f"{relative_vol:.2f}x",
            "HVRank": f"{hv_rank * 100:.0f}%",
            "RSI": int(latest_rsi),
            "StrikeFloor": f"${suggested_strike_margin:,.2f}",
            "ScoreA": f"{score_a} / 3",
            "ScoreB": f"{score_b} / 3",
            "RawHVRank": hv_rank
        }
    except Exception:
        return None  

# ==========================================
# 3. REPORT FORMATTING PIPELINE
# ==========================================
def build_markdown_matrix(group_a, group_b):
    output = "=== SYSTEMATIC BROAD INDEX SCORING MATRIX ===\n\n"
    
    output += " GROUP A: ALPHA MOMENTUM BREAKOUTS (Call Targets) -- [Filter: High Liquid + Low IV Setup]\n"
    output += "| Ticker | Price   | Ann Alpha | 20D Vol | Daily RSI | IV Rank | Tactical Score |\n"
    output += "| -------- | ------- | --------- | ------- | --------- | ------- | -------------- |\n"
    for t, m in group_a:
        output += f"| {t:<6} | {m['Price']:<7} | {m['Alpha']:+7.1%} | {m['Vol']:<7} | {m['RSI']:<9} | {m['HVRank']:<7} | {m['ScoreA']:<14} |\n"
        
    output += "\n GROUP B: STRUCTURAL PULLBACKS (Put Selling Income) -- [Filter: High Vol Premium + Margin Floor]\n"
    output += "| Ticker | Price   | Ann Alpha | Daily RSI | 20D Vol | IV Rank | Suggested Strike Floor | Put selling Score |\n"
    output += "| -------- | ------- | --------- | --------- | ------- | ------- | ---------------------- | ----------------- |\n"
    for t, m in group_b:
        output += f"| {t:<6} | {m['Price']:<7} | {m['Alpha']:+7.1%} | {m['RSI']:<9} | {m['Vol']:<7} | {m['HVRank']:<7} | {m['StrikeFloor']:<22} | {m['ScoreB']:<17} |\n"

    output += "\nAutomated Data Pipeline Engine via GitHub Cloud Workspace Universe Engine"
    return output

# ==========================================
# 4. PORT 465 SSL DISPATCH PIPELINE
# ==========================================
def send_matrix_email(matrix_text):
    smtp_user = "douglassgw@gmail.com"     # <-- Change to your sender address
    to_email = "douglassgw@gmail.com"   # <-- Change to your receiver address
    smtp_pass = os.environ.get("EMAIL_PASSWORD"

    if not smtp_pass:
        raise ValueError("❌ CRITICAL CONFIG: EMAIL_PASSWORD environment variable is missing.")

    msg = MIMEMultipart()
    msg["Subject"] = "📊 UNLOCKED SYSTEMATIC TOTAL-MARKET OPTIONS MATRIX"
    msg["From"] = smtp_user
    msg["To"] = to_email
    
    body = f"Total-market multi-index macro scan complete. Optimized options setups:\n\n{matrix_text}"
    msg.attach(MIMEText(body, "plain"))

    print("Opening secure SSL pipeline tunnel to smtp.gmail.com:465...")
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)
    server.login(smtp_user, smtp_pass)
    server.sendmail(smtp_user, to_email, msg.as_string())
    server.quit()
    print("✨ SUCCESS: Macro Matrix data package emailed successfully!")

# ==========================================
# 5. EXECUTION DISPATCH MATRIX
# ==========================================
def main():
    print("🚀 BOOTING BROAD NETWORK INDEX EXTRACTION PROCESSING ENGINE")
    
    spy_df = yf.download("SPY", period="1y", interval="1d", progress=False, multi_level_index=False)
    spy_df.columns = [str(col).strip() for col in spy_df.columns]

    # Dynamically extract comprehensive multi-index rosters
    watchlist = fetch_broad_market_universe()

    group_a_pool = []
    group_b_pool = []

    print("Spinning up parallel worker threads for macro computation loop...")
    # Throttled slightly to 12 workers to prevent API connection refusal across 600+ components
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(calculate_matrix_metrics, ticker, spy_df): ticker for ticker in watchlist}
        for future in as_completed(futures):
            ticker = futures[future]
            metrics = future.result()
            if metrics is not None:
                if metrics["RSI"] >= 45:
                    group_a_pool.append((ticker, metrics))
                else:
                    group_b_pool.append((ticker, metrics))

    # Perform multi-layered sorting matrices
    group_a_pool.sort(key=lambda x: x[1]["Alpha"], reverse=True)
    group_b_pool.sort(key=lambda x: x[1]["RawHVRank"], reverse=True)

    # Compile report using the best 20 positions found across the combined universe
    matrix_output = build_markdown_matrix(group_a_pool[:20], group_b_pool[:20])
    print("\n" + matrix_output + "\n")
    
    send_matrix_email(matrix_output)

if __name__ == "__main__":
    main()

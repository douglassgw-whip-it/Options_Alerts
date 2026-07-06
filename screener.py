import os
import smtplib
import numpy as np
import pandas as pd
import yfinance as yf
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# 1. DYNAMIC MULTI-INDEX UNIVERSE SCRAPER
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
    except Exception as e:
        print(f"⚠️ S&P 500 scrape bypassed: {e}")

    # Track 2: NASDAQ-100
    try:
        nasdaq_table = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
        for table in nasdaq_table:
            if 'Ticker' in table.columns or 'Symbol' in table.columns:
                col = 'Ticker' if 'Ticker' in table.columns else 'Symbol'
                nasdaq_list = table[col].dropna().tolist()
                tickers.extend([t.replace('.', '-') for t in nasdaq_list])
                break
    except Exception as e:
        print(f"⚠️ NASDAQ-100 scrape bypassed: {e}")

    # Index Benchmarks & Watchlist fallbacks
    macro_anchors = ["QQQ", "IWM", "DIA", "RKLB", "PLTR", "BBAI", "VLN", "ACHR"]
    full_universe = list(set(macro_anchors + tickers))
    print(f"📊 Broad Engine Complete. Total components to batch download: {len(full_universe)}")
    return full_universe

# ==========================================
# 2. REPORT FORMATTING PIPELINE
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
# 3. PORT 465 SSL DISPATCH PIPELINE
# ==========================================
def send_matrix_email(matrix_text):
    smtp_user = "douglassgw@gmail.com"  
    to_email = "douglassgw@gmail.com"   
    smtp_pass = os.environ.get("EMAIL_PASSWORD")

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
# 4. EXECUTION DISPATCH MATRIX (BATCH DRIVEN)
# ==========================================
def main():
    print("🚀 BOOTING BROAD NETWORK INDEX EXTRACTION PROCESSING ENGINE")
    
    watchlist = fetch_broad_market_universe()
    
    print("Executing single massive batch download to prevent cloud rate-limiting...")
    all_data = yf.download(watchlist + ["SPY"], period="1y", interval="1d", progress=False)
    
    try:
        spy_close = all_data['Close']['SPY'].dropna()
        spy_returns = spy_close.pct_change().dropna()
        spy_cum = (1 + spy_returns).prod() - 1
        spy_vol_20d = spy_returns.tail(20).std() * np.sqrt(252)
    except Exception as e:
        print(f"❌ Failed to parse SPY benchmark data: {e}")
        return

    group_a_pool = []
    group_b_pool = []

    print("Processing metrics from batch footprint...")
    for ticker in watchlist:
        if ticker == "SPY":
            continue
        try:
            close_series = all_data['Close'][ticker].dropna()
            volume_series = all_data['Volume'][ticker].dropna()
            high_series = all_data['High'][ticker].dropna()
            low_series = all_data['Low'][ticker].dropna()
            
            if len(close_series) < 50:
                continue

            # 1. LIQUIDITY FILTER
            avg_volume_10d = volume_series.tail(10).mean()
            if avg_volume_10d < 1000000:
                continue

            # Align vectors with SPY
            combined_stock_spy = pd.concat([close_series.rename('Stock'), spy_close.rename('SPY')], axis=1).dropna()
            stock_returns = combined_stock_spy['Stock'].pct_change().dropna()
            
            # 2. ANNUALIZED ALPHA
            stock_cum = (1 + stock_returns).prod() - 1
            alpha = stock_cum - spy_cum

            # 3. 20-DAY RELATIVE VOLATILITY
            stock_vol_20d = stock_returns.tail(20).std() * np.sqrt(252)
            relative_vol = stock_vol_20d / spy_vol_20d if spy_vol_20d > 0 else 1.0

            # 4. HISTORICAL VOLATILITY (HV) RANK
            rolling_20d_vol = stock_returns.rolling(20).std() * np.sqrt(252)
            hv_min, hv_max = rolling_20d_vol.min(), rolling_20d_vol.max()
            hv_rank = ((stock_vol_20d - hv_min) / (hv_max - hv_min)) if (hv_max - hv_min) > 0 else 0.5

            # 5. 14-DAY RSI
            delta = combined_stock_spy['Stock'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_series = 100 - (100 / (1 + (gain / loss)))
            latest_price = combined_stock_spy['Stock'].iloc[-1]
            latest_rsi = rsi_series.iloc[-1] if not np.isnan(rsi_series.iloc[-1]) else 50.0

            # 6. ATR & SAFETY MARGIN
            high_low = high_series - low_series
            high_close = (high_series - close_series.shift()).abs()
            low_close = (low_series - close_series.shift()).abs()
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(14).mean().iloc[-1]
            suggested_strike_margin = latest_price - (2 * atr)

            # 7. METRIC MATCH SCORING
            score_a = 0
            if latest_rsi > 55: score_a += 1
            if alpha > 0.05: score_a += 1
            if hv_rank < 0.40: score_a += 1

            score_b = 0
            if latest_rsi < 35: score_b += 1
            if alpha < 0: score_b += 1
            if hv_rank > 0.60: score_b += 1

            metrics = {
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

            if latest_rsi >= 45:
                group_a_pool.append((ticker, metrics))
            else:
                group_b_pool.append((ticker, metrics))
        except Exception:
            continue

    group_a_pool.sort(key=lambda x: x[1]["Alpha"], reverse=True)
    group_b_pool.sort(key=lambda x: x[1]["RawHVRank"], reverse=True)

    matrix_output = build_markdown_matrix(group_a_pool[:20], group_b_pool[:20])
    print("\n" + matrix_output + "\n")
    
    send_matrix_email(matrix_output)

if __name__ == "__main__":
    main()

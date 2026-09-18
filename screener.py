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
    try:
        sp500_df = pd.read_csv("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv")
        tickers.extend([str(t).replace('.', '-') for t in sp500_df['Symbol'].tolist()])
    except Exception as e:
        print(f"⚠️ S&P 500 mirror bypassed: {e}.")
    try:
        nasdaq_df = pd.read_csv("https://raw.githubusercontent.com/Ate329/top-us-stock-tickers/main/tickers/top_100.csv")
        col = 'symbol' if 'symbol' in nasdaq_df.columns else 'Symbol'
        tickers.extend([str(t).replace('.', '-') for t in nasdaq_df[col].tolist()])
    except Exception as e:
        print(f"⚠️ NASDAQ-100 mirror bypassed: {e}")

    core_anchors = ["QQQ", "IWM", "DIA", "RKLB", "PLTR", "BBAI", "VLN", "ACHR", "JEPI", "JEPQ"]
    return list(set(core_anchors + tickers))

# ==========================================
# 2. MARKDOWN RENDER PIPELINE
# ==========================================
def build_markdown_matrix(group_a, group_b, group_c):
    output = "## OPTIMIZED 30-45D OPTIONS SCORING MATRIX\n"
    output += "=======================================================================\n\n"
    
    output += "### 🚀 GROUP C: BREAKOUT SIGNALS (Volume/Momentum/Compression)\n"
    output += "| Ticker | Price | RSI | Vol Relative | Strength vs SPY |\n"
    output += "| :--- | :--- | :--- | :--- | :--- |\n"
    for t, m in group_c:
        output += f"| {t:<6} | {m['Price']:<9} | {m['RSI']:<5} | {m['VolumeRel']:<12} | {m['RelStrength']:<15} |\n"
    
    output += "\n" + "---" * 20 + "\n\n"
    
    output += "### 📈 GROUP A: DELTA MOMENTUM BREAKOUTS\n"
    output += "| Ticker | Price | Ann Alpha | Daily RSI | 30D IV Rank | Target Strike (+1 ATR) | Score |\n"
    output += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for t, m in group_a:
        output += f"| {t:<6} | {m['Price']:<9} | {m['Alpha']:+9.1%} | {m['RSI']:<9} | {m['IVRank']:<10} | {m['TargetStrike']:<22} | {m['Score']:<11} |\n"
        
    output += "\n" + "---" * 20 + "\n\n"
    
    output += "### 💵 GROUP B: STRUCTURAL PULLBACKS\n"
    output += "| Ticker | Price | Ann Alpha | Daily RSI | 30D IV Rank | Margin Floor (-2 ATR) | Score |\n"
    output += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for t, m in group_b:
        output += f"| {t:<6} | {m['Price']:<9} | {m['Alpha']:+9.1%} | {m['RSI']:<9} | {m['IVRank']:<10} | {m['StrikeFloor']:<31} | {m['Score']:<11} |\n"

    return output

# ==========================================
# 3. SECURE REPO-SECRETS SMTP TUNNEL
# ==========================================
def send_matrix_email(matrix_text):
    smtp_user = os.environ.get("EMAIL_USER")
    smtp_pass = os.environ.get("EMAIL_PASSWORD")
    to_email = os.environ.get("TO_EMAIL")
    if not all([smtp_user, smtp_pass, to_email]): 
        raise ValueError("Missing environment secrets.")
    msg = MIMEMultipart()
    msg["Subject"] = "📊 OPTIMIZED 30-45D OPTIONS SCORING MATRIX"
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(matrix_text, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, to_email, msg.as_string())

# ==========================================
# 4. DATA ENGINE & CORE SIGNAL LOGIC
# ==========================================
def main():
    spy_df = yf.download("SPY", period="1y", interval="1d", progress=False, auto_adjust=False)
    if isinstance(spy_df.columns, pd.MultiIndex): 
        spy_df.columns = spy_df.columns.get_level_values(0)
    
    # Clean SPY reference series
    spy_df['Price_Clean'] = spy_df['Close'].fillna(spy_df['Adj Close']).ffill()
    spy_close = spy_df['Price_Clean'].dropna()
    spy_cum = (1 + spy_close.pct_change().dropna()).prod() - 1
    spy_20d_ret = (spy_close.iloc[-1] / spy_close.iloc[-21]) - 1

    watchlist = fetch_options_universe()
    group_a_pool, group_b_pool, group_c_pool = [], [], []

    for ticker in watchlist:
        if ticker == "SPY": 
            continue
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=False)
            if df.empty or len(df) < 60: 
                continue
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            # --- ROBUST PRICE & ATR CLEANUP PATCH ---
            df['Price_Clean'] = df['Close'].fillna(df['Adj Close']).ffill()
            df = df.dropna(subset=['Price_Clean', 'High', 'Low', 'Volume'])
            if len(df) < 60:
                continue

            close = df['Price_Clean']
            vol = df['Volume']
            high = df['High']
            low = df['Low']

            if vol.tail(20).mean() < 2500000: 
                continue
            
            curr_p = float(close.iloc[-1])
            if np.isnan(curr_p) or curr_p <= 0:
                continue

            # --- CALCULATE INDICATORS ---
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            curr_rsi = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50.0

            # --- ATR CALCULATION PATCH ---
            tr1 = high - low
            tr2 = (high - close.shift()).abs()
            tr3 = (low - close.shift()).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_series = tr.rolling(14).mean().dropna()
            
            if atr_series.empty or np.isnan(atr_series.iloc[-1]):
                continue
            
            atr_14 = float(atr_series.iloc[-1])

            # --- GROUP C: BREAKOUT LOGIC ---
            sma_50 = close.rolling(50).mean().iloc[-1]
            high_20d = high.rolling(20).max().shift(1).iloc[-1]
            vol_avg_20 = vol.rolling(20).mean().iloc[-1]
            std_20 = close.rolling(20).std()
            bandwidth = (std_20 * 2) / close.rolling(20).mean()
            is_tight = bandwidth.iloc[-1] < bandwidth.rolling(20).mean().iloc[-1]
            rel_strength = (curr_p / close.iloc[-21]) - 1

            if curr_p > high_20d and vol.iloc[-1] >= (1.5 * vol_avg_20) and 50 <= curr_rsi <= 72 and curr_p > sma_50 and is_tight and rel_strength > spy_20d_ret:
                group_c_pool.append((ticker, {
                    "Price": f"${curr_p:,.2f}", 
                    "RSI": int(curr_rsi), 
                    "VolumeRel": f"{vol.iloc[-1]/vol_avg_20:.1f}x", 
                    "RelStrength": f"{rel_strength:.1%}"
                }))

            # --- GROUP A/B: SCORING LOGIC ---
            alpha = ((1 + close.pct_change().dropna()).prod() - 1) - spy_cum
            log_ret = np.log(close / close.shift(1)).dropna()
            rolling_std = log_ret.rolling(30).std().dropna()
            
            if len(rolling_std) == 0:
                continue
                
            iv_rank_proxy = (rolling_std * np.sqrt(252) < (rolling_std.iloc[-1] * np.sqrt(252))).sum() / len(rolling_std)

            if curr_rsi >= 50:
                score_a = (1 if 55 < curr_rsi < 70 else 0) + (1 if alpha > 0.05 else 0) + (1 if iv_rank_proxy < 0.45 else 0)
                group_a_pool.append((ticker, {
                    "Price": f"${curr_p:,.2f}", 
                    "Alpha": alpha, 
                    "RSI": int(curr_rsi), 
                    "IVRank": f"{iv_rank_proxy * 100:.0f}%", 
                    "TargetStrike": f"${curr_p + atr_14:,.2f}", 
                    "Score": f"{score_a} / 3", 
                    "RawIVRank": iv_rank_proxy
                }))
            else:
                score_b = (1 if curr_rsi < 38 else 0) + (1 if iv_rank_proxy > 0.65 else 0) + (1 if alpha > -0.15 else 0)
                group_b_pool.append((ticker, {
                    "Price": f"${curr_p:,.2f}", 
                    "Alpha": alpha, 
                    "RSI": int(curr_rsi), 
                    "IVRank": f"{iv_rank_proxy * 100:.0f}%", 
                    "StrikeFloor": f"${curr_p - (2 * atr_14):,.2f}", 
                    "Score": f"{score_b} / 3", 
                    "RawIVRank": iv_rank_proxy
                }))
        except Exception:
            continue

    group_a_pool.sort(key=lambda x: x[1]["Alpha"], reverse=True)
    group_b_pool.sort(key=lambda x: x[1]["RawIVRank"], reverse=True)
    
    matrix_output = build_markdown_matrix(group_a_pool[:15], group_b_pool[:15], group_c_pool)
    print(matrix_output)
    send_matrix_email(matrix_output)

if __name__ == "__main__":
    main()

import os
import sys
import pandas as pd

# ========================================================
# 1. YOUR ORIGINAL SIGNAL LOGIC (WITH GRACEFUL DATA GUARDS)
# ========================================================
def generate_signal(df):
    """Evaluates trading rules based on moving averages, trailing stops, RSI, and daily momentum."""
    # Safety Check: Ensure the DataFrame exists and has at least 2 days of data
    if df is None or len(df) < 2:
        return "⚪ HOLD (Insufficient Data Rows)", "#4A4A4A"
        
    latest = df.iloc[-1]
    prior = df.iloc[-2]
    
    # Safe data extraction using .get() to prevent silent KeyErrors
    current_price = latest.get("Close")
    prior_price = prior.get("Close")
    ma50 = latest.get("MA50")
    ma200 = latest.get("MA200")
    rsi = latest.get("RSI")
    recent_peak = latest.get("Recent_Peak")

    # Ensure crucial price data points exist before math operations
    if current_price is None or prior_price is None:
        return "⚪ HOLD (Missing Core Price Columns)", "#4A4A4A"

    # Calculate today's performance to detect sharp intraday turnarounds
    daily_return = (current_price - prior_price) / prior_price if prior_price else 0
    
    # Safely handle drop calculation to avoid ZeroDivisionErrors
    if recent_peak and recent_peak > 0:
        drop_from_peak = (recent_peak - current_price) / recent_peak
    else:
        drop_from_peak = 0

    # 1. 🔥 BULLISH OVERRIDE: Catch high-momentum breakout/reversal days
    if daily_return >= 0.03:
        if ma50 and ma200 and current_price > ma50 and ma50 > ma200:
            return "🚀 BULLISH BREAKOUT (Strong Momentum)", "#2E7D32"
        else:
            return "🔄 BULLISH REVERSAL (Volume Surge)", "#0288D1"

    # 2. Trailing Stop-Loss Trigger (Only fires if the stock didn't bounce sharply today)
    elif drop_from_peak >= 0.10:
        return "🔴 STOP-LOSS BREACHED (-10%)", "#D32F2F"
        
    # 3. Standard Trend Following Buy Setup
    elif ma50 and ma200 and rsi and current_price > ma50 and ma50 > ma200 and rsi < 65:
        return "🟢 BUY (Strong Uptrend)", "#2E7D32"
        
    # 4. Moving Average / Overbought Breakdown
    elif (ma50 and current_price < ma50) or (rsi and rsi > 80):
        return "🚨 TREND WEAKENING (Exit Setup)", "#E65100"
        
    else:
        return "⚪ HOLD", "#4A4A4A"

# ========================================================
# 2. CORE EXECUTION & GITHUB LOG DEBUGGER
# ========================================================
def run_screener(market_data_dict):
    """
    Processes your data dictionary and prints detailed logs 
    directly to GitHub Actions so you can see why emails aren't sending.
    """
    print("==================================================")
    print("🚀 STARTING SCREENER EVALUATION")
    print(f"Total items found in dataset: {len(market_data_dict)}")
    print("==================================================")

    actionable_signals_found = 0

    for key, df in market_data_dict.items():
        # Log the structural state of the incoming data frame
        row_count = len(df) if df is not None else 0
        print(f"\n🔍 Evaluating: {key} | Total historical data rows: {row_count}")

        # Run your logic
        signal, color = generate_signal(df)
        print(f"   ↳ Result: {signal}")

        # Track if anything actually triggered an alert status
        if "⚪ HOLD" not in signal:
            actionable_signals_found += 1
            print(f"   🔥 ALERT TRIGGERED for {key}! Preparing email payload...")
            # Your original email dispatch code or list appending goes here
            
    print("\n==================================================")
    print("📊 SCREENER RUN COMPLETE")
    print(f"Total actionable alerts built: {actionable_signals_found}")
    if actionable_signals_found == 0:
        print("💡 NOTICE: Zero emails were sent because 100% of the tickers evaluated to a 'HOLD'.")
    print("==================================================")

# This wrapper links into whatever structure handles your main execution
if __name__ == "__main__":
    # Ensure a data dictionary variable exists from your data fetcher block
    if 'your_market_data' in locals() or 'your_market_data' in globals():
        run_screener(your_market_data)
    else:
        print("⚠️ Script structure note: Pass your main market DataFrame dictionary into run_screener().")

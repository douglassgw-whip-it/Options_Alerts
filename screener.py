def generate_signal(df):
    """Evaluates trading rules based on moving averages, trailing stops, RSI, and daily momentum."""
    if len(df) < 2:
        return "⚪ HOLD", "#4A4A4A"
        
    latest = df.iloc[-1]
    prior = df.iloc[-2]
    
    current_price = latest["Close"]
    prior_price = prior["Close"]
    ma50 = latest["MA50"]
    ma200 = latest["MA200"]
    rsi = latest["RSI"]
    recent_peak = latest["Recent_Peak"]

    # Calculate today's performance to detect sharp intraday turnarounds
    daily_return = (current_price - prior_price) / prior_price
    drop_from_peak = (recent_peak - current_price) / recent_peak

    # 1. 🔥 BULLISH OVERRIDE: Catch high-momentum breakout/reversal days (e.g., RKLB up 15%)
    if daily_return >= 0.03:
        # Check if it's an absolute breakout or a structural trend recovery
        if current_price > ma50 and ma50 > ma200:
            return "🚀 BULLISH BREAKOUT (Strong Momentum)", "#2E7D32"
        else:
            return "🔄 BULLISH REVERSAL (Volume Surge)", "#0288D1"

    # 2. Trailing Stop-Loss Trigger (Only fires if the stock didn't bounce sharply today)
    elif drop_from_peak >= 0.10:
        return "🔴 STOP-LOSS BREACHED (-10%)", "#D32F2F"
        
    # 3. Standard Trend Following Buy Setup
    elif current_price > ma50 and ma50 > ma200 and rsi < 65:
        return "🟢 BUY (Strong Uptrend)", "#2E7D32"
        
    # 4. Moving Average / Overbought Breakdown
    elif current_price < ma50 or rsi > 80:
        return "🚨 TREND WEAKENING (Exit Setup)", "#E65100"
        
    else:
        return "⚪ HOLD", "#4A4A4A"

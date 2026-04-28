"""
Decision Engine — price fetching, technical indicators, and exit recommendation.
"""
import requests
import numpy as np
import pandas as pd
from datetime import datetime


# ─── Price History ─────────────────────────────────────────────────────────────

def _fetch_price_history(ticker: str) -> pd.Series:
    """Return a pd.Series of daily closes for the last 1 year."""
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="1y")
        if not hist.empty:
            return hist["Close"]
    except Exception:
        pass

    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?range=1y&interval=1d&includePrePost=false"
    )
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    result = data["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    idx = pd.to_datetime(timestamps, unit="s")
    return pd.Series(closes, index=idx, name="Close").dropna()


# ─── Technical Indicators ──────────────────────────────────────────────────────

def compute_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1)


def compute_macd(series: pd.Series) -> tuple[float, float, float]:
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1])


def compute_momentum(series: pd.Series, period: int = 20) -> float:
    if len(series) < period + 1:
        return 0.0
    return round(float((series.iloc[-1] / series.iloc[-period - 1] - 1) * 100), 2)


# ─── Exit Analysis ─────────────────────────────────────────────────────────────

def run_exit_analysis(
    ticker: str,
    buy_price: float,
    buy_date: str,
    shares: float,
    risk_tolerance: str,
    account_type: str,
) -> dict:
    ticker = ticker.upper().strip()
    close = _fetch_price_history(ticker)

    if close is None or len(close) == 0:
        return {"error": f"No data found for ticker '{ticker}'."}

    current_price = float(close.iloc[-1])
    buy_dt = datetime.strptime(buy_date, "%Y-%m-%d")
    hold_days = (datetime.now() - buy_dt).days
    hold_years = hold_days / 365.25
    gain_pct = (current_price - buy_price) / buy_price * 100
    position_value = current_price * shares
    unrealized_pnl = position_value - buy_price * shares
    short_term_tax = (account_type == "Taxable") and (hold_years < 1)

    rsi = compute_rsi(close)
    macd_val, macd_sig, macd_hist = compute_macd(close)
    momentum_20 = compute_momentum(close, 20)
    sma50 = float(close.rolling(50).mean().iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1])

    sell_pressure = 0
    signals = []

    # P&L signal
    if gain_pct > 50:
        sell_pressure += 25
        signals.append(f"Position up {gain_pct:.1f}% — significant profit, consider taking gains")
    elif gain_pct > 25:
        sell_pressure += 15
        signals.append(f"Position up {gain_pct:.1f}% — healthy gain achieved")
    elif gain_pct > 10:
        sell_pressure += 5
        signals.append(f"Position up {gain_pct:.1f}%")
    elif gain_pct < -10:
        sell_pressure -= 10
        signals.append(f"Position down {abs(gain_pct):.1f}% — review stop-loss strategy")
    else:
        signals.append(f"Position {gain_pct:+.1f}% — near breakeven")

    # RSI signal
    if rsi > 75:
        sell_pressure += 20
        signals.append(f"RSI {rsi} — severely overbought")
    elif rsi > 65:
        sell_pressure += 12
        signals.append(f"RSI {rsi} — overbought territory")
    elif rsi < 35:
        sell_pressure -= 15
        signals.append(f"RSI {rsi} — oversold, possible bounce")
    else:
        signals.append(f"RSI {rsi} — neutral momentum")

    # MACD signal
    if macd_hist < 0 and macd_val < macd_sig:
        sell_pressure += 15
        signals.append("MACD histogram negative — bearish momentum divergence")
    elif macd_hist > 0 and macd_val > macd_sig:
        sell_pressure -= 10
        signals.append("MACD histogram positive — bullish momentum")
    else:
        signals.append("MACD signal mixed / neutral")

    # Momentum signal
    if momentum_20 < -5:
        sell_pressure += 10
        signals.append(f"20-day momentum {momentum_20:+.1f}% — negative trend")
    elif momentum_20 > 10:
        sell_pressure -= 5
        signals.append(f"20-day momentum {momentum_20:+.1f}% — strong uptrend")
    else:
        signals.append(f"20-day momentum {momentum_20:+.1f}%")

    # SMA signals
    if current_price < sma50:
        sell_pressure += 10
        signals.append("Price below 50-day SMA — short-term downtrend")
    if current_price < sma200:
        sell_pressure += 10
        signals.append("Price below 200-day SMA — long-term downtrend")
    if current_price > sma50 > sma200:
        sell_pressure -= 5
        signals.append("Price above both SMAs — uptrend intact")

    # Tax signal
    if short_term_tax and gain_pct > 10:
        sell_pressure -= 8
        signals.append(f"Short-term hold ({hold_days}d) — selling triggers ordinary income rates")

    # Risk tolerance adjustment
    sell_pressure += {"Low": 10, "Medium": 0, "High": -10}.get(risk_tolerance, 0)
    if risk_tolerance == "Low":
        signals.append("Low risk tolerance — bias toward protecting gains")
    elif risk_tolerance == "High":
        signals.append("High risk tolerance — comfortable riding volatility")

    sell_pressure = max(0, min(100, sell_pressure))

    if sell_pressure >= 60:
        action, color = "Full Sell", "#f04438"
        confidence = min(95, 50 + sell_pressure // 2)
    elif sell_pressure >= 40:
        action, color = "Sell 50%", "#FFB482"
        confidence = min(90, 45 + sell_pressure // 2)
    elif sell_pressure >= 20:
        action, color = "Sell 25%", "#ffd400"
        confidence = min(85, 40 + sell_pressure // 2)
    else:
        action, color = "Hold", "#17b26a"
        confidence = min(90, 70 - sell_pressure)

    price_hist_df = close.reset_index()
    price_hist_df.columns = ["date", "price"]
    price_hist_df["date"] = pd.to_datetime(price_hist_df["date"]).dt.strftime("%Y-%m-%d")

    return {
        "ticker": ticker,
        "action": action,
        "confidence": int(confidence),
        "color": color,
        "sell_pressure_score": int(sell_pressure),
        "signals": signals,
        "metrics": {
            "current_price": round(current_price, 2),
            "buy_price": round(buy_price, 2),
            "gain_pct": round(gain_pct, 2),
            "position_value": round(position_value, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "hold_days": hold_days,
            "rsi": rsi,
            "macd": round(macd_val, 3),
            "macd_signal": round(macd_sig, 3),
            "macd_histogram": round(macd_hist, 3),
            "momentum_20d": momentum_20,
            "sma50": round(sma50, 2),
            "sma200": round(sma200, 2),
            "short_term_tax": short_term_tax,
        },
        "price_history": price_hist_df.to_dict(orient="records"),
    }
